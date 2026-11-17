"""Filesystem export for POS diagnostic reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping

from modules.menu.diagnostics.report_formatter import format_diagnostic_report


DIAGNOSTIC_EXPORT_ROOT = Path.home() / "POS_Exports" / "Diagnostic"


def export_diagnostic_report(
    diagnostic_results: Mapping[str, Mapping],
    *,
    output_dir: str | Path | None = None,
    generated_at: datetime | None = None,
) -> Path:
    """Write a timestamped UTF-8 diagnostic report and return its path."""
    generated = generated_at or datetime.now().astimezone()
    folder = Path(output_dir) if output_dir is not None else DIAGNOSTIC_EXPORT_ROOT
    folder.mkdir(parents=True, exist_ok=True)

    timestamp = generated.strftime("%d%b%Y_%H-%M-%S").lower()
    candidate = folder / f"diagnostic_report_{timestamp}.txt"
    suffix = 2
    while candidate.exists():
        candidate = folder / f"diagnostic_report_{timestamp}_{suffix}.txt"
        suffix += 1

    report = format_diagnostic_report(
        diagnostic_results,
        generated_at=generated,
    )
    candidate.write_text(report, encoding="utf-8", newline="\n")
    return candidate
