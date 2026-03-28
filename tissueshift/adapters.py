"""Foundation model adapters for parameter-efficient fine-tuning.

Modern histopathology foundation models (UNI, CONCH, Virchow, PLIP,
CTransPath) have hundreds of millions of parameters.  Full fine-tuning
is prohibitively expensive and risks overfitting on the relatively
small breast cancer cohorts used by TissueShift.

This module provides **parameter-efficient fine-tuning (PEFT)**
strategies that update < 1-5% of parameters while achieving
comparable performance:

1. **LoRA (Low-Rank Adaptation)** — injects trainable rank-r
   decompositions into attention projection matrices.
2. **LoRA+** — decoupled learning rates for A and B matrices.
3. **AdaLoRA** — adaptive rank allocation that grows/prunes rank
   per layer based on importance.
4. **Prefix Tuning** — prepends learnable soft tokens to keys/values.
5. **BitFit** — only trains bias terms.
6. **Adapter Layers** — bottleneck layers inserted after attention/FFN.

References
----------
Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models", ICLR 2022.
Zhang et al., "AdaLoRA: Adaptive Budget Allocation", ICLR 2023.
Li & Liang, "Prefix-Tuning", ACL 2021.
Houlsby et al., "Parameter-Efficient Transfer Learning", ICML 2019.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class PEFTConfig:
    """Configuration for parameter-efficient fine-tuning."""

    method: str = "lora"  # lora | adalora | prefix | bitfit | adapter
    # LoRA params
    lora_rank: int = 8
    lora_alpha: float = 16.0
    lora_dropout: float = 0.05
    lora_target_modules: Tuple[str, ...] = (
        "q_proj", "v_proj", "k_proj", "out_proj",
        "query", "value", "key",  # alternate naming
    )
    lora_plus_lr_ratio: float = 16.0  # B matrix LR multiplier for LoRA+
    # AdaLoRA
    adalora_init_rank: int = 12
    adalora_target_rank: int = 4
    adalora_warmup_steps: int = 500
    # Prefix tuning
    prefix_length: int = 20
    prefix_hidden_dim: int = 512
    # Adapter
    adapter_bottleneck_dim: int = 64
    adapter_dropout: float = 0.1
    # General
    freeze_base: bool = True


# ===================================================================
# 1. LoRA — Low-Rank Adaptation
# ===================================================================

class LoRALinear(nn.Module):
    """Drop-in replacement for nn.Linear with LoRA decomposition.

    W_new = W_frozen + (B @ A) * (α / r)

    Only A and B are trainable.  A is initialised with Kaiming; B is
    initialised to zero so the initial output equals the frozen model.
    """

    def __init__(
        self,
        original: nn.Linear,
        rank: int = 8,
        alpha: float = 16.0,
        dropout: float = 0.05,
    ):
        super().__init__()
        self.in_features = original.in_features
        self.out_features = original.out_features
        self.rank = rank
        self.scaling = alpha / rank

        # Frozen weights
        self.weight = original.weight
        self.weight.requires_grad_(False)
        self.bias = original.bias
        if self.bias is not None:
            self.bias.requires_grad_(False)

        # LoRA matrices
        self.lora_A = nn.Parameter(torch.empty(rank, self.in_features))
        self.lora_B = nn.Parameter(torch.zeros(self.out_features, rank))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))

        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        base = F.linear(x, self.weight, self.bias)
        lora = self.dropout(x) @ self.lora_A.T @ self.lora_B.T * self.scaling
        return base + lora

    def merge(self) -> nn.Linear:
        """Merge LoRA weights into a single Linear for inference."""
        merged = nn.Linear(self.in_features, self.out_features, bias=self.bias is not None)
        merged.weight.data = self.weight.data + (self.lora_B @ self.lora_A) * self.scaling
        if self.bias is not None:
            merged.bias.data = self.bias.data
        return merged

    @property
    def trainable_params(self) -> int:
        return self.lora_A.numel() + self.lora_B.numel()


# ===================================================================
# 2. AdaLoRA — Adaptive Rank Allocation
# ===================================================================

class AdaLoRALinear(nn.Module):
    """LoRA with SVD-based adaptive rank allocation.

    Decomposes the update as W_Δ = P Λ Q where Λ is a diagonal of
    *importance scores*.  During training, low-importance singular
    values are pruned.
    """

    def __init__(
        self,
        original: nn.Linear,
        init_rank: int = 12,
        alpha: float = 16.0,
        dropout: float = 0.05,
    ):
        super().__init__()
        self.in_features = original.in_features
        self.out_features = original.out_features
        self.rank = init_rank
        self.scaling = alpha / init_rank

        self.weight = original.weight
        self.weight.requires_grad_(False)
        self.bias = original.bias
        if self.bias is not None:
            self.bias.requires_grad_(False)

        # SVD decomposition: P (out, r), Λ (r,), Q (r, in)
        self.lora_P = nn.Parameter(torch.randn(self.out_features, init_rank) * 0.01)
        self.lora_Lambda = nn.Parameter(torch.ones(init_rank))
        self.lora_Q = nn.Parameter(torch.randn(init_rank, self.in_features) * 0.01)

        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        self._importance = torch.zeros(init_rank)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        base = F.linear(x, self.weight, self.bias)
        delta = (self.lora_P * self.lora_Lambda.unsqueeze(0)) @ self.lora_Q
        lora_out = self.dropout(x) @ delta.T * self.scaling
        return base + lora_out

    def update_importance(self) -> None:
        """Update importance scores based on |Λ| * ||P_i|| * ||Q_i||."""
        with torch.no_grad():
            p_norm = self.lora_P.norm(dim=0)
            q_norm = self.lora_Q.norm(dim=1)
            self._importance = (self.lora_Lambda.abs() * p_norm * q_norm).detach()

    def prune_to_rank(self, target_rank: int) -> None:
        """Remove least-important singular values."""
        if target_rank >= self.rank:
            return
        self.update_importance()
        keep = self._importance.topk(target_rank).indices.sort().values
        self.lora_P.data = self.lora_P.data[:, keep]
        self.lora_Lambda.data = self.lora_Lambda.data[keep]
        self.lora_Q.data = self.lora_Q.data[keep, :]
        self.rank = target_rank


# ===================================================================
# 3. Prefix Tuning
# ===================================================================

class PrefixEncoder(nn.Module):
    """Generate prefix key-value pairs for transformer attention.

    Instead of modifying weights, prefix tuning prepends *learnable
    soft tokens* to the key and value sequences in every attention
    layer.  This effectively steers the attention without changing
    model parameters.
    """

    def __init__(
        self,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        prefix_length: int = 20,
        hidden_dim: int = 512,
    ):
        super().__init__()
        self.num_layers = num_layers
        self.prefix_length = prefix_length
        embed_dim = num_heads * head_dim

        # Learnable prefix embeddings (reparameterised through MLP)
        self.prefix_tokens = nn.Embedding(prefix_length, hidden_dim)
        self.prefix_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 2 * num_layers * embed_dim),
        )

    def forward(self, batch_size: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """Generate prefix keys and values for all layers.

        Returns
        -------
        prefix_keys : (num_layers, B, prefix_length, embed_dim)
        prefix_values : (num_layers, B, prefix_length, embed_dim)
        """
        idx = torch.arange(self.prefix_length, device=self.prefix_tokens.weight.device)
        emb = self.prefix_tokens(idx)  # (L, hidden)
        projected = self.prefix_proj(emb)  # (L, 2*layers*embed)

        # Reshape: (L, 2, layers, embed)
        projected = projected.view(self.prefix_length, 2, self.num_layers, -1)
        # Expand batch: (2, layers, B, L, embed)
        projected = projected.permute(1, 2, 0, 3).unsqueeze(2).expand(-1, -1, batch_size, -1, -1)

        prefix_keys = projected[0]    # (layers, B, L, embed)
        prefix_values = projected[1]  # (layers, B, L, embed)
        return prefix_keys, prefix_values


# ===================================================================
# 4. Adapter Layers
# ===================================================================

class BottleneckAdapter(nn.Module):
    """Bottleneck adapter inserted after a transformer sub-layer.

    h → LayerNorm → down_proj → act → up_proj → scale + residual

    The bottleneck dimension is typically 32-128, adding minimal
    parameters while providing substantial capacity.
    """

    def __init__(
        self,
        input_dim: int,
        bottleneck_dim: int = 64,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.norm = nn.LayerNorm(input_dim)
        self.down = nn.Linear(input_dim, bottleneck_dim)
        self.act = nn.GELU()
        self.up = nn.Linear(bottleneck_dim, input_dim)
        self.dropout = nn.Dropout(dropout)
        self.scale = nn.Parameter(torch.tensor(0.1))

        # Initialize near-identity
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        h = self.norm(x)
        h = self.down(h)
        h = self.act(h)
        h = self.dropout(h)
        h = self.up(h)
        return residual + h * self.scale


# ===================================================================
# Injection utilities
# ===================================================================

def _find_linear_modules(
    model: nn.Module,
    target_names: Tuple[str, ...],
) -> Dict[str, Tuple[nn.Module, str, nn.Linear]]:
    """Find all nn.Linear modules whose name matches one of *target_names*."""
    matches: Dict[str, Tuple[nn.Module, str, nn.Linear]] = {}
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            short = name.split(".")[-1]
            if short in target_names:
                # Get parent
                parts = name.rsplit(".", 1)
                if len(parts) == 2:
                    parent_name, attr = parts
                    parent = dict(model.named_modules())[parent_name]
                else:
                    parent = model
                    attr = name
                matches[name] = (parent, attr, module)
    return matches


def inject_lora(
    model: nn.Module,
    cfg: PEFTConfig,
) -> nn.Module:
    """Inject LoRA layers into a model in-place.

    Returns the model with LoRA layers replacing matching Linear modules.
    """
    targets = _find_linear_modules(model, cfg.lora_target_modules)
    n_injected = 0

    for full_name, (parent, attr, linear) in targets.items():
        lora_linear = LoRALinear(
            linear,
            rank=cfg.lora_rank,
            alpha=cfg.lora_alpha,
            dropout=cfg.lora_dropout,
        )
        setattr(parent, attr, lora_linear)
        n_injected += 1

    logger.info(
        "Injected LoRA (rank=%d) into %d layers; trainable params: %s",
        cfg.lora_rank,
        n_injected,
        _count_trainable(model),
    )

    if cfg.freeze_base:
        freeze_non_lora(model)

    return model


def inject_adapters(
    model: nn.Module,
    cfg: PEFTConfig,
    after_pattern: str = r"self_attn|mlp|ffn",
) -> nn.Module:
    """Inject bottleneck adapter layers after matched sub-modules."""
    n_injected = 0
    for name, module in list(model.named_modules()):
        if re.search(after_pattern, name) and hasattr(module, "out_proj"):
            dim = module.out_proj.out_features if hasattr(module.out_proj, "out_features") else 256
            adapter = BottleneckAdapter(dim, cfg.adapter_bottleneck_dim, cfg.adapter_dropout)
            # Wrap the module's forward
            original_forward = module.forward

            def make_wrapped(orig, adp):
                def wrapped(*args, **kwargs):
                    out = orig(*args, **kwargs)
                    if isinstance(out, torch.Tensor):
                        return adp(out)
                    return out
                return wrapped

            module.forward = make_wrapped(original_forward, adapter)
            n_injected += 1

    logger.info("Injected %d adapter layers", n_injected)
    if cfg.freeze_base:
        _freeze_except_adapters(model)
    return model


def freeze_non_lora(model: nn.Module) -> None:
    """Freeze all parameters except LoRA/adapter parameters."""
    for name, param in model.named_parameters():
        if "lora_" not in name and "adapter" not in name and "prefix" not in name:
            param.requires_grad_(False)


def _freeze_except_adapters(model: nn.Module) -> None:
    """Freeze all except adapter + bias parameters."""
    for name, param in model.named_parameters():
        trainable = (
            "adapter" in name
            or "prefix" in name
            or "lora_" in name
            or "bias" in name
        )
        param.requires_grad_(trainable)


def enable_bitfit(model: nn.Module) -> None:
    """BitFit: only train bias terms."""
    for name, param in model.named_parameters():
        param.requires_grad_("bias" in name)
    logger.info("BitFit enabled: %s trainable params", _count_trainable(model))


def _count_trainable(model: nn.Module) -> str:
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    pct = 100 * trainable / max(total, 1)
    return f"{trainable:,} / {total:,} ({pct:.2f}%)"


# ===================================================================
# LoRA+ optimiser helper
# ===================================================================

def lora_plus_param_groups(
    model: nn.Module,
    base_lr: float = 1e-4,
    lr_ratio: float = 16.0,
    weight_decay: float = 0.01,
) -> List[Dict[str, Any]]:
    """Create parameter groups for LoRA+ (separate LR for A and B).

    B matrices and biases get base_lr × lr_ratio.
    """
    group_a: list[nn.Parameter] = []
    group_b: list[nn.Parameter] = []
    group_other: list[nn.Parameter] = []

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if "lora_A" in name:
            group_a.append(param)
        elif "lora_B" in name:
            group_b.append(param)
        else:
            group_other.append(param)

    return [
        {"params": group_a, "lr": base_lr, "weight_decay": weight_decay},
        {"params": group_b, "lr": base_lr * lr_ratio, "weight_decay": weight_decay},
        {"params": group_other, "lr": base_lr, "weight_decay": weight_decay},
    ]


# ===================================================================
# Merge / export utilities
# ===================================================================

def merge_lora_weights(model: nn.Module) -> nn.Module:
    """Merge all LoRA layers back into their base Linear modules.

    After merging, the model has no LoRA overhead and can be exported
    as a standard checkpoint.
    """
    for name, module in list(model.named_modules()):
        if isinstance(module, LoRALinear):
            parts = name.rsplit(".", 1)
            if len(parts) == 2:
                parent = dict(model.named_modules())[parts[0]]
                attr = parts[1]
            else:
                parent = model
                attr = name
            setattr(parent, attr, module.merge())
    logger.info("Merged all LoRA weights into base model.")
    return model


def peft_summary(model: nn.Module) -> Dict[str, Any]:
    """Return a summary of PEFT modules in the model."""
    lora_count = 0
    adapter_count = 0
    total_lora_params = 0

    for name, module in model.named_modules():
        if isinstance(module, LoRALinear):
            lora_count += 1
            total_lora_params += module.trainable_params
        if isinstance(module, (AdaLoRALinear,)):
            lora_count += 1
        if isinstance(module, BottleneckAdapter):
            adapter_count += 1

    return {
        "lora_layers": lora_count,
        "adapter_layers": adapter_count,
        "lora_params": total_lora_params,
        "trainable": _count_trainable(model),
    }
