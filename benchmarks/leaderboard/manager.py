"""Leaderboard management: ingest results, rank, serve."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from benchmarks.metrics import PRIMARY_METRICS

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    team: str
    model: str
    score: float
    track: str
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    metrics: dict[str, float] = field(default_factory=dict)
    rank: int = 0


class Leaderboard:
    """Manages leaderboard state for all tracks."""

    def __init__(self, storage_dir: str = "data/leaderboard"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.entries: dict[str, list[LeaderboardEntry]] = {}
        self._load()

    def _load(self):
        """Load all leaderboard data from disk."""
        for track in PRIMARY_METRICS:
            path = self.storage_dir / f"{track}.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                self.entries[track] = [
                    LeaderboardEntry(**entry) for entry in data
                ]
            else:
                self.entries[track] = []

    def _save(self, track: str):
        """Persist leaderboard for a track."""
        path = self.storage_dir / f"{track}.json"
        with open(path, "w") as f:
            json.dump([asdict(e) for e in self.entries[track]], f, indent=2)

    def submit(
        self,
        track: str,
        team: str,
        model: str,
        score: float,
        metrics: dict[str, float] | None = None,
    ) -> LeaderboardEntry:
        """Add or update a leaderboard entry."""
        if track not in PRIMARY_METRICS:
            raise ValueError(f"Unknown track: {track}")

        # Check for existing entry by same team
        existing = [
            e for e in self.entries[track] if e.team == team and e.model == model
        ]

        entry = LeaderboardEntry(
            team=team,
            model=model,
            score=score,
            track=track,
            metrics=metrics or {},
        )

        if existing:
            # Update if score improved
            if score > existing[0].score:
                self.entries[track].remove(existing[0])
                self.entries[track].append(entry)
                logger.info(f"Updated {team}/{model} on {track}: {score:.4f}")
            else:
                logger.info(f"Score not improved for {team}/{model} on {track}")
                return existing[0]
        else:
            self.entries[track].append(entry)
            logger.info(f"New entry {team}/{model} on {track}: {score:.4f}")

        # Re-rank
        self.entries[track].sort(key=lambda e: e.score, reverse=True)
        for i, e in enumerate(self.entries[track]):
            e.rank = i + 1

        self._save(track)
        return entry

    def get_track(self, track: str) -> list[LeaderboardEntry]:
        """Get ranked leaderboard for a track."""
        return self.entries.get(track, [])

    def get_all(self) -> dict[str, list[LeaderboardEntry]]:
        """Get all leaderboard data."""
        return self.entries

    def format_markdown(self, track: str) -> str:
        """Format leaderboard as markdown table."""
        entries = self.get_track(track)
        primary = PRIMARY_METRICS[track]

        lines = [
            f"## {track} Leaderboard",
            "",
            f"| Rank | Team | Model | {primary} | Date |",
            "|------|------|-------|--------|------|",
        ]

        for e in entries:
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(e.rank, str(e.rank))
            lines.append(
                f"| {medal} | {e.team} | {e.model} | {e.score:.4f} | {e.date} |"
            )

        return "\n".join(lines)
