#!/usr/bin/env python3
"""Utility for reporting the latest VAULT TV release metadata.

This lightweight helper inspects a JSON feed that contains an array of
VAULT TV release entries. Each entry must at minimum provide an ISO 8601
``date`` field as well as a descriptive ``title``. The tool surfaces the most
recent entry so that operators can quickly verify which drop is live inside the
Mind-Vault-AI shop experience. If no explicit feed is supplied, the checker will
look for ``data/vault_tv_feed.json`` and fall back to the distributed sample
file so first-time operators can run the command without additional setup.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

DEFAULT_FEED_CANDIDATES: Sequence[Path] = (
    Path("data/vault_tv_feed.json"),
    Path("data/vault_tv_feed.sample.json"),
)


@dataclass(frozen=True)
class VaultTvEntry:
    """Represents a validated VAULT TV feed entry."""

    title: str
    published_at: datetime
    raw_date: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "VaultTvEntry":
        if "date" not in data or "title" not in data:
            raise ValueError("Entry is missing required 'date' or 'title' fields.")

        raw_date = str(data["date"])
        parsed_date = _parse_date(raw_date)

        metadata = {
            key: value
            for key, value in data.items()
            if key not in {"title", "date"}
        }

        return cls(
            title=str(data["title"]),
            published_at=parsed_date,
            raw_date=raw_date,
            metadata=dict(metadata),
        )


def _resolve_default_feed() -> Path:
    """Return the first available default feed path.

    Raises
    ------
    FileNotFoundError
        If none of the known feed candidates are present.
    """

    for candidate in DEFAULT_FEED_CANDIDATES:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No VAULT TV feed found. Create data/vault_tv_feed.json using the "
        "sample template in data/vault_tv_feed.sample.json."
    )


def _parse_date(raw: str) -> datetime:
    """Parse an ISO 8601 timestamp into a :class:`datetime` instance.

    ``datetime.fromisoformat`` does not accept ``Z`` as a timezone suffix, so we
    normalise it to ``+00:00`` to keep the workflow forgiving.
    """

    normalised = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalised)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Invalid ISO 8601 date: {raw!r}") from exc


def _load_entries(feed_path: Path) -> List[VaultTvEntry]:
    """Load and validate entries from the feed file."""

    try:
        raw_content = feed_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Feed not found at {feed_path}. Provide a JSON file using the sample "
            "template in data/vault_tv_feed.sample.json."
        )

    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Feed file {feed_path} is not valid JSON: {exc.msg}"
        ) from exc

    if not isinstance(payload, list):
        raise ValueError(
            f"Feed file {feed_path} must contain a JSON array of entries."
        )

    validated: List[VaultTvEntry] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(
                f"Feed entry #{idx + 1} in {feed_path} is not a JSON object."
            )

        try:
            entry = VaultTvEntry.from_mapping(item)
        except ValueError as exc:
            raise ValueError(
                f"Feed entry #{idx + 1} in {feed_path} is invalid: {exc}"
            ) from exc

        validated.append(entry)

    if not validated:
        raise ValueError(
            f"Feed file {feed_path} does not contain any VAULT TV entries."
        )

    return validated


def _format_metadata(entry: VaultTvEntry) -> Iterable[str]:
    for key, value in entry.metadata.items():
        yield f"  {key}: {value}"


def report_latest(feed_path: Path, *, stale_after: Optional[int] = None) -> str:
    """Generate a human-readable report of the latest VAULT TV entry."""

    entries = _load_entries(feed_path)
    latest_entry = max(entries, key=lambda item: item.published_at)

    lines = [
        "Latest VAULT TV release detected:",
        f"  Title: {latest_entry.title}",
        f"  Date:  {latest_entry.published_at.isoformat()}",
    ]

    metadata_lines = list(_format_metadata(latest_entry))
    if metadata_lines:
        lines.append("  Additional metadata:")
        lines.extend(metadata_lines)

    lines.append(f"Total releases in feed: {len(entries)}")

    if stale_after is not None:
        now = datetime.now(timezone.utc)
        age = now - latest_entry.published_at
        threshold = timedelta(days=stale_after)
        if age > threshold:
            lines.append(
                "⚠️  Latest release is older than the configured staleness window "
                f"({age.days} days > {stale_after} days)."
            )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feed",
        type=Path,
        help=(
            "Path to the VAULT TV feed JSON file. If omitted the checker searches "
            "for data/vault_tv_feed.json and falls back to the sample template."
        ),
    )
    parser.add_argument(
        "--stale-after",
        type=int,
        default=None,
        metavar="DAYS",
        help=(
            "Warn if the newest VAULT TV release is older than the given number "
            "of days."
        ),
    )
    args = parser.parse_args()

    try:
        feed_path = args.feed if args.feed is not None else _resolve_default_feed()
        report = report_latest(feed_path, stale_after=args.stale_after)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
