"""Error/failure policy helpers (opt-in).

This module is additive and does not affect existing dialogs unless imported.
It provides a centralized place to decide what to log and how to surface
messages to users.
"""

from __future__ import annotations

import traceback
from typing import Callable, Optional, TypeVar

from modules.ui_utils.error_logger import log_error
from modules.ui_utils import ui_feedback

T = TypeVar('T')


def should_log(exc: Exception, *, category: str = 'unexpected') -> bool:
    """Decide whether an exception should be logged.

    Suggested categories: 'validation', 'expected', 'unexpected', 'db', 'ui'.
    """
    cat = (category or 'unexpected').strip().lower()

    # Validation and expected-user-flow errors generally shouldn't spam logs.
    if cat in ('validation', 'expected'):
        return False

    # KeyboardInterrupt/SystemExit shouldn't be logged as application errors.
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return False

    return True


def safe_call(
    where: str,
    fn: Callable[[], T],
    *,
    host_window=None,
    user_message: Optional[str] = None,
    duration: int = 5000,
    category: str = 'unexpected',
    log: bool = True,
    fallback: Optional[T] = None,
) -> Optional[T]:
    """Run fn() and apply standardized error handling on failure.

    - Optional logging to error.log (traceback included)
    - Optional user-facing MainWindow status bar message
    - Returns fallback on exception

    This is opt-in; dialogs can choose to use it incrementally.
    """
    try:
        return fn()
    except Exception as exc:
        if log and should_log(exc, category=category):
            try:
                tb = traceback.format_exc()
            except Exception:
                tb = ''
            try:
                msg = f"{(where or 'Error').strip()}: {exc!r}"
                if tb and 'Traceback' in tb:
                    msg = msg + "\n" + tb
                log_error(msg)
            except Exception:
                pass

        if host_window is not None and user_message:
            try:
                ui_feedback.show_main_status(host_window, str(user_message), is_error=True, duration=int(duration))
            except Exception:
                pass

        return fallback
