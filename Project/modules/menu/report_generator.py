# modules/menu/report_generator.py
"""Thin adapter between UI (`report_menu.py`) and report data layer.

Currently implements a minimal `get_detailed_report` function that calls
`modules.db_operation.reports_repo.detailed_report` and returns the
structured result. This keeps UI code decoupled from SQL/aggregation logic.
"""
from typing import Dict, Any

from modules.db_operation import reports_repo


def get_detailed_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return structured detailed report data for the given params.

    Args:
        params: dictionary containing params such as `from`, `to`, `user_id`.

    Returns:
        A dict with keys matching the detailed report structure. If no data
        is available, implementations may return an empty but well-formed
        dict.
    """
    return reports_repo.detailed_report(params)
