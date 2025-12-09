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

_RELATIVE_FEED_TARGETS: Sequence[str] = (
    "data/vault_tv_feed.json",
    "data/vault_tv_feed.sample.json",
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


@dataclass(frozen=True)
class ReportResult:
    """Represents the outcome of summarising the feed."""

    message: str
    is_stale: bool
    entry_count: int
    latest_entry: VaultTvEntry
    generated_at: datetime
    age: timedelta

    def to_payload(self) -> Dict[str, Any]:
        """Return a JSON-serialisable payload describing the report."""

        return {
            "generated_at": self.generated_at.isoformat(),
            "entry_count": self.entry_count,
            "is_stale": self.is_stale,
            "latest_release": {
                "title": self.latest_entry.title,
                "date": self.latest_entry.published_at.isoformat(),
                "age_seconds": int(self.age.total_seconds()),
                "age_human": _format_timedelta(self.age),
                "metadata": dict(self.latest_entry.metadata),
            },
            "message": self.message,
        }


def _resolve_default_feed() -> Path:
    """Return the first available default feed path.

    The resolver checks both the current working directory and the repository
    root (relative to this script) so the command works even when invoked from
    automation pipelines.

    Raises
    ------
    FileNotFoundError
        If none of the known feed candidates are present.
    """

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    candidates: List[Path] = []
    seen: set[Path] = set()
    for relative_target in _RELATIVE_FEED_TARGETS:
        for base in (Path.cwd(), repo_root):
            candidate = (base / relative_target).resolve()
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)

    for candidate in candidates:
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
        parsed = datetime.fromisoformat(normalised)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Invalid ISO 8601 date: {raw!r}") from exc

    if parsed.tzinfo is None:
        # Assume UTC for feeds that omit an explicit timezone. This keeps the
        # workflow forgiving while avoiding naive datetimes in later math.
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _load_entries(feed_path: Path) -> List[VaultTvEntry]:
    """Load and validate entries from the feed file."""

    try:
        latest_entry = max(entries, key=lambda item: (item.published_at, item.title))
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

            if age > threshold:
                # Round up to the nearest whole day for a more intuitive message.
                age_in_days = int((age.total_seconds() + 86399) // 86400)
                lines.append(
                    "⚠️  Latest release is older than the configured staleness window "
                    f"({age_in_days} days > {stale_after} days)."
                )
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
        yield f"    {key}: {value}"


def _format_timedelta(delta: timedelta) -> str:
    """Return a compact human readable representation of a time delta."""

    total_seconds = int(delta.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)

    days, remainder = divmod(total_seconds, 24 * 3600)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    segments = []
    if days:
        segments.append(f"{days}d")
    if hours:
        segments.append(f"{hours}h")
    if minutes or not segments:
        segments.append(f"{minutes}m")

    return sign + " ".join(segments)


def report_latest(
    feed_path: Path, *, stale_after: Optional[int] = None
) -> ReportResult:
    """Generate a human-readable report of the latest VAULT TV entry."""

    entries = _load_entries(feed_path)
    latest_entry = max(entries, key=lambda item: item.published_at)
    now = datetime.now(timezone.utc)
    age = now - latest_entry.published_at

    lines = [
        "Latest VAULT TV release detected:",
        f"  Title: {latest_entry.title}",
        f"  Date:  {latest_entry.published_at.isoformat()}",
        f"  Age:   {_format_timedelta(age)} (as of {now.isoformat()})",
    ]

    metadata_lines = list(_format_metadata(latest_entry))
    if metadata_lines:
        lines.append("  Additional metadata:")
        lines.extend(metadata_lines)

    lines.append(f"Total releases in feed: {len(entries)}")

    is_stale = False
    if stale_after is not None:
        threshold = timedelta(days=stale_after)
        if age > threshold:
            is_stale = True
            lines.append(
                "⚠️  Latest release is older than the configured staleness window "
                f"({age.days} days > {stale_after} days)."
            )

    return ReportResult(
        "\n".join(lines),
        is_stale=is_stale,
        entry_count=len(entries),
        latest_entry=latest_entry,
        generated_at=now,
        age=age,
    )


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
    parser.add_argument(
        "--fail-on-stale",
        action="store_true",
        help=(
            "Exit with a non-zero status code when the latest release exceeds the "
            "--stale-after window."
        ),
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help=(
            "Choose between human-readable text (default) or JSON formatted "
            "output for automation."
        ),
    )
    args = parser.parse_args()

    if args.stale_after is not None and args.stale_after <= 0:
        parser.error("--stale-after must be a positive integer")

    try:
        feed_path = args.feed if args.feed is not None else _resolve_default_feed()
        report = report_latest(feed_path, stale_after=args.stale_after)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    if args.output == "json":
        print(json.dumps(report.to_payload(), indent=2))
    else:
        print(report.message)

    if report.is_stale and args.fail_on_stale:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
