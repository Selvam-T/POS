"""Refresh the UTC build timestamp used by trial executables.

Run this from the Project directory immediately before creating a trial build:

    python dev_tools/maintenance/write_trial_build_timestamp.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET = PROJECT_ROOT / 'modules' / 'runtime' / 'trial_build.py'


def main() -> int:
    now = datetime.now(timezone.utc)
    content = (
        '"""Generated trial-build metadata.\n\n'
        'Refresh this file immediately before creating a trial executable.\n'
        '"""\n\n'
        'from datetime import datetime, timezone\n\n\n'
        'BUILD_TIMESTAMP_UTC = datetime(\n'
        f'    {now.year}, {now.month}, {now.day}, '
        f'{now.hour}, {now.minute}, {now.second}, '
        f'{now.microsecond}, tzinfo=timezone.utc\n'
        ')\n'
    )
    TARGET.write_text(content, encoding='utf-8')
    print(f'Updated {TARGET} to {now.isoformat()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
