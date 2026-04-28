# modules/menu/report_generator.py
"""report_generator is the thin UI-facing adapter. 
   report_menu.py calls it, and it forwards the request to the reports_repo.py.
"""
from typing import Dict, Any

from modules.db_operation import reports_repo


def get_detailed_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return detailed report data."""
    return reports_repo.detailed_report(params)


def get_summary_report(params: Dict[str, Any]) -> Dict[str, Any]:
   """Return summary report data."""
   return reports_repo.summary_report(params)


def get_inactivity_report(params: Dict[str, Any]) -> Dict[str, Any]:
   """Return inactivity report data."""
   return reports_repo.inactivity_report(params)
