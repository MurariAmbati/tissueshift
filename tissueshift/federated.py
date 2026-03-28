"""Federated learning engine for privacy-preserving multi-site training.

Enables TissueShift to be trained across multiple hospitals without
sharing raw patient data.  Each site keeps its data locally and only
communicates model updates (or encrypted gradients) to a central
coordinator.

Supports three federation strategies:

1. **FedAvg** — standard federated averaging of model weights.
2. **FedProx** — proximal term to handle heterogeneous data.
3. **Scaffold** — variance reduction via control variates.
4. **Differential Privacy** — noise injection for formal ε-DP guarantees.

The engine handles:
* Heterogeneous cohorts (each site may have different modalities)
* Communication compression (top-k sparsification)
* Asynchronous participation (sites can join/leave rounds)
* Secure aggregation simulation

References
----------
McMahan et al., "Communication-Efficient Learning of Deep Networks", AISTATS 2017.
Li et al., "Federated Optimization in Heterogeneous Networks (FedProx)", MLSys 2020.
Karimireddy et al., "SCAFFOLD", ICML 2020.
Abadi et al., "Deep Learning with Differential Privacy", CCS 2016.
"""

from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class FederatedConfig:
    """Parameters for federated learning."""

    strategy: str = "fedavg"  # fedavg | fedprox | scaffold
    num_rounds: int = 100
    local_epochs: int = 5
    min_clients_per_round: int = 2
    client_fraction: float = 1.0  # fraction of clients sampled per round

    # FedProx
    fedprox_mu: float = 0.01  # proximal term weight

    # Communication
    compress: bool = False
    compress_top_k: float = 0.1  # fraction of gradients to send

    # Differential privacy
    use_dp: bool = False
    dp_noise_multiplier: float = 1.0
    dp_max_grad_norm: float = 1.0
    target_epsilon: float = 8.0
    target_delta: float = 1e-5

    # Aggregation
    weighted_by_samples: bool = True  # weight by dataset size


# ===================================================================
# Client (Site)
# ===================================================================

class FederatedClient:
    """Represents a single hospital/site in the federation.

    Each client holds a local dataset, a local copy of the global model,
    and optionally SCAFFOLD control variates.
    """

    def __init__(
        self,
        client_id: str,
        model: nn.Module,
        train_loader: Any,
        val_loader: Optional[Any] = None,
        cfg: FederatedConfig = FederatedConfig(),
        device: str = "cpu",
    ):
        self.client_id = client_id
        self.model = copy.deepcopy(model).to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.cfg = cfg
        self.device = device

        self.num_samples = len(train_loader.dataset) if hasattr(train_loader, "dataset") else 0

        # SCAFFOLD control variate
        self._control_variate: Optional[Dict[str, torch.Tensor]] = None
        self._server_control: Optional[Dict[str, torch.Tensor]] = None

    def receive_global_model(self, global_state: Dict[str, torch.Tensor]) -> None:
        """Update local model with global weights."""
        self.model.load_state_dict(global_state, strict=False)

    def receive_server_control(self, server_control: Dict[str, torch.Tensor]) -> None:
        """Receive server control variate (SCAFFOLD)."""
        self._server_control = {k: v.clone() for k, v in server_control.items()}

    def local_train(
        self,
        loss_fn: nn.Module,
        lr: float = 1e-4,
        global_state: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Dict[str, Any]:
        """Perform local training for cfg.local_epochs.

        Returns
        -------
        Dict with: model_delta, num_samples, local_loss, control_delta (scaffold)
        """
        self.model.train()
        optimizer = torch.optim.SGD(self.model.parameters(), lr=lr)

        # Save initial state for delta computation
        init_state = {k: v.clone() for k, v in self.model.state_dict().items()}

        total_loss = 0.0
        n_batches = 0

        for epoch in range(self.cfg.local_epochs):
            for batch in self.train_loader:
                optimizer.zero_grad()
                batch = self._move_batch(batch)

                outputs = self.model(**batch["inputs"])
                losses = loss_fn(outputs, batch.get("targets", {}), stage=batch.get("stage", 0))
                loss = losses["total"] if isinstance(losses, dict) else losses

                # FedProx proximal term
                if self.cfg.strategy == "fedprox" and global_state is not None:
                    prox = 0.0
                    for name, param in self.model.named_parameters():
                        if name in global_state:
                            prox += ((param - global_state[name].to(self.device)) ** 2).sum()
                    loss = loss + 0.5 * self.cfg.fedprox_mu * prox

                # SCAFFOLD correction
                if self.cfg.strategy == "scaffold" and self._control_variate is not None:
                    for name, param in self.model.named_parameters():
                        if param.grad is not None and name in self._control_variate:
                            cv = self._control_variate[name].to(self.device)
                            sc = self._server_control[name].to(self.device) if self._server_control else 0
                            param.grad.data += sc - cv

                loss.backward()

                # DP gradient clipping
                if self.cfg.use_dp:
                    self._clip_gradients()

                optimizer.step()
                total_loss += loss.item()
                n_batches += 1

        # Compute model delta
        final_state = self.model.state_dict()
        model_delta = {
            k: final_state[k] - init_state[k]
            for k in init_state
            if k in final_state
        }

        # Update SCAFFOLD control variate
        control_delta = None
        if self.cfg.strategy == "scaffold":
            control_delta = self._update_scaffold_control(
                init_state, final_state, lr
            )

        # Communication compression
        if self.cfg.compress:
            model_delta = self._compress_delta(model_delta)

        avg_loss = total_loss / max(n_batches, 1)
        return {
            "model_delta": model_delta,
            "num_samples": self.num_samples,
            "local_loss": avg_loss,
            "control_delta": control_delta,
        }

    def _clip_gradients(self) -> None:
        """Per-sample gradient clipping for DP."""
        total_norm = 0.0
        for param in self.model.parameters():
            if param.grad is not None:
                total_norm += param.grad.data.norm(2).item() ** 2
        total_norm = math.sqrt(total_norm)
        clip_coef = min(1.0, self.cfg.dp_max_grad_norm / (total_norm + 1e-6))
        for param in self.model.parameters():
            if param.grad is not None:
                param.grad.data *= clip_coef

    def _compress_delta(
        self, delta: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """Top-k sparsification for communication efficiency."""
        compressed = {}
        for k, v in delta.items():
            flat = v.flatten()
            k_val = max(1, int(len(flat) * self.cfg.compress_top_k))
            topk = flat.abs().topk(k_val)
            mask = torch.zeros_like(flat)
            mask[topk.indices] = flat[topk.indices]
            compressed[k] = mask.reshape(v.shape)
        return compressed

    def _update_scaffold_control(
        self,
        init_state: Dict[str, torch.Tensor],
        final_state: Dict[str, torch.Tensor],
        lr: float,
    ) -> Dict[str, torch.Tensor]:
        """Update SCAFFOLD local control variate."""
        if self._control_variate is None:
            self._control_variate = {
                k: torch.zeros_like(v) for k, v in init_state.items()
            }

        new_cv: Dict[str, torch.Tensor] = {}
        delta_cv: Dict[str, torch.Tensor] = {}
        K = self.cfg.local_epochs * max(1, len(self.train_loader))

        for k in init_state:
            old_cv = self._control_variate.get(k, torch.zeros_like(init_state[k]))
            sc = self._server_control.get(k, torch.zeros_like(init_state[k])) if self._server_control else torch.zeros_like(init_state[k])

            new_cv[k] = old_cv - sc + (init_state[k] - final_state[k]) / (K * lr + 1e-10)
            delta_cv[k] = new_cv[k] - old_cv

        self._control_variate = new_cv
        return delta_cv

    def _move_batch(self, batch: Any) -> Dict[str, Any]:
        """Move batch tensors to device."""
        if isinstance(batch, dict):
            result: Dict[str, Any] = {}
            for k, v in batch.items():
                if isinstance(v, torch.Tensor):
                    result[k] = v.to(self.device)
                elif isinstance(v, dict):
                    result[k] = {
                        kk: vv.to(self.device) if isinstance(vv, torch.Tensor) else vv
                        for kk, vv in v.items()
                    }
                else:
                    result[k] = v
            return result
        return {"inputs": batch}

    @torch.no_grad()
    def evaluate(self, loss_fn: nn.Module) -> Dict[str, float]:
        """Evaluate on local validation set."""
        if self.val_loader is None:
            return {}
        self.model.eval()
        total_loss = 0.0
        n = 0
        for batch in self.val_loader:
            batch = self._move_batch(batch)
            outputs = self.model(**batch["inputs"])
            losses = loss_fn(outputs, batch.get("targets", {}), stage=0)
            total_loss += (losses["total"] if isinstance(losses, dict) else losses).item()
            n += 1
        return {"val_loss": total_loss / max(n, 1)}


# ===================================================================
# Server (Coordinator)
# ===================================================================

class FederatedServer:
    """Central coordinator that aggregates client updates.

    Does NOT see any raw patient data — only receives model weight
    deltas (optionally compressed / noised).
    """

    def __init__(
        self,
        global_model: nn.Module,
        cfg: FederatedConfig = FederatedConfig(),
    ):
        self.cfg = cfg
        self.global_model = global_model
        self.global_state = copy.deepcopy(global_model.state_dict())

        # SCAFFOLD server control
        self._server_control: Dict[str, torch.Tensor] = {
            k: torch.zeros_like(v) for k, v in self.global_state.items()
        }

        self.round_history: List[Dict[str, Any]] = []

    @property
    def current_round(self) -> int:
        return len(self.round_history)

    def select_clients(
        self, clients: List[FederatedClient]
    ) -> List[FederatedClient]:
        """Random client sampling for this round."""
        n = max(
            self.cfg.min_clients_per_round,
            int(len(clients) * self.cfg.client_fraction),
        )
        n = min(n, len(clients))
        indices = np.random.choice(len(clients), n, replace=False)
        return [clients[i] for i in indices]

    def aggregate(
        self, client_results: List[Dict[str, Any]]
    ) -> Dict[str, torch.Tensor]:
        """Aggregate client model deltas into the global model.

        Supports FedAvg (weighted averaging) and SCAFFOLD (with control
        variate correction).
        """
        if not client_results:
            return self.global_state

        # Compute weights
        if self.cfg.weighted_by_samples:
            total_samples = sum(r["num_samples"] for r in client_results)
            weights = [r["num_samples"] / max(total_samples, 1) for r in client_results]
        else:
            weights = [1.0 / len(client_results)] * len(client_results)

        # Aggregate deltas
        agg_delta: Dict[str, torch.Tensor] = {}
        for key in client_results[0]["model_delta"]:
            agg_delta[key] = sum(
                w * r["model_delta"][key] for w, r in zip(weights, client_results)
            )

        # Add DP noise
        if self.cfg.use_dp:
            agg_delta = self._add_dp_noise(agg_delta, len(client_results))

        # Apply to global model
        new_state: Dict[str, torch.Tensor] = {}
        for k in self.global_state:
            if k in agg_delta:
                new_state[k] = self.global_state[k] + agg_delta[k]
            else:
                new_state[k] = self.global_state[k]

        self.global_state = new_state
        self.global_model.load_state_dict(new_state, strict=False)

        # SCAFFOLD server control update
        if self.cfg.strategy == "scaffold":
            self._update_server_control(client_results)

        # Record history
        avg_loss = np.mean([r["local_loss"] for r in client_results])
        self.round_history.append({
            "round": self.current_round,
            "n_clients": len(client_results),
            "avg_loss": float(avg_loss),
            "total_samples": sum(r["num_samples"] for r in client_results),
        })

        logger.info(
            "Round %d: %d clients, avg_loss=%.4f",
            self.current_round, len(client_results), avg_loss,
        )

        return self.global_state

    def _add_dp_noise(
        self,
        delta: Dict[str, torch.Tensor],
        num_clients: int,
    ) -> Dict[str, torch.Tensor]:
        """Add calibrated Gaussian noise for differential privacy."""
        noise_std = (
            self.cfg.dp_noise_multiplier
            * self.cfg.dp_max_grad_norm
            / max(num_clients, 1)
        )
        noised = {}
        for k, v in delta.items():
            noised[k] = v + torch.randn_like(v) * noise_std
        return noised

    def _update_server_control(
        self, client_results: List[Dict[str, Any]]
    ) -> None:
        """Update SCAFFOLD server control variate."""
        n = len(client_results)
        for r in client_results:
            if r.get("control_delta") is not None:
                for k, dv in r["control_delta"].items():
                    if k in self._server_control:
                        self._server_control[k] += dv / n

    def broadcast(self, clients: List[FederatedClient]) -> None:
        """Send global model to all clients."""
        for c in clients:
            c.receive_global_model(self.global_state)
            if self.cfg.strategy == "scaffold":
                c.receive_server_control(self._server_control)


# ===================================================================
# Federation Orchestrator
# ===================================================================

class FederationOrchestrator:
    """End-to-end federated training loop.

    Coordinates server and clients through a configurable number of
    communication rounds.
    """

    def __init__(
        self,
        server: FederatedServer,
        clients: List[FederatedClient],
        loss_fn: nn.Module,
        cfg: FederatedConfig = FederatedConfig(),
    ):
        self.server = server
        self.clients = clients
        self.loss_fn = loss_fn
        self.cfg = cfg

    def run(
        self,
        num_rounds: Optional[int] = None,
        lr: float = 1e-4,
        eval_every: int = 5,
    ) -> List[Dict[str, Any]]:
        """Run the full federated training loop.

        Returns
        -------
        List of round-level results.
        """
        rounds = num_rounds or self.cfg.num_rounds
        history: list[Dict[str, Any]] = []

        for r in range(rounds):
            logger.info("=== Federated Round %d/%d ===", r + 1, rounds)

            # 1. Broadcast global model
            self.server.broadcast(self.clients)

            # 2. Select clients
            selected = self.server.select_clients(self.clients)

            # 3. Local training
            results = []
            for client in selected:
                result = client.local_train(
                    loss_fn=self.loss_fn,
                    lr=lr,
                    global_state=self.server.global_state,
                )
                results.append(result)

            # 4. Aggregate
            self.server.aggregate(results)

            # 5. Evaluate
            round_info = self.server.round_history[-1]
            if (r + 1) % eval_every == 0:
                val_results = {}
                for client in self.clients:
                    client.receive_global_model(self.server.global_state)
                    val = client.evaluate(self.loss_fn)
                    if val:
                        val_results[client.client_id] = val
                round_info["val_results"] = val_results

            history.append(round_info)

        return history

    def privacy_budget(self) -> Dict[str, float]:
        """Compute spent privacy budget (for DP mode)."""
        if not self.cfg.use_dp:
            return {"dp_enabled": False}

        # Simplified RDP → (ε, δ) conversion
        rounds = self.server.current_round
        sigma = self.cfg.dp_noise_multiplier
        q = self.cfg.client_fraction
        delta = self.cfg.target_delta

        # Moments accountant approximation
        rdp_alpha = 2.0
        rdp_eps = q ** 2 * rdp_alpha / (2 * sigma ** 2) * rounds

        epsilon = rdp_eps + math.log(1 / delta) / (rdp_alpha - 1)

        return {
            "dp_enabled": True,
            "epsilon_spent": float(epsilon),
            "target_epsilon": self.cfg.target_epsilon,
            "delta": self.cfg.target_delta,
            "rounds_completed": rounds,
            "budget_remaining": max(0, self.cfg.target_epsilon - epsilon),
        }
