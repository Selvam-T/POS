# Trial Build Expiry

Trial behavior is controlled from `config.py`:

```python
TRIAL_BUILD_ENABLED = False
TRIAL_EXPIRY_DATE = date(2026, 6, 30)
TRIAL_EXPIRED_MESSAGE = 'Testing period expired. Please contact SelvamPOS support.'
```

When `TRIAL_BUILD_ENABLED` is `True`, `modules/runtime/trial.py` blocks login when either condition is true:

- Current UTC date is after `TRIAL_EXPIRY_DATE`.
- Current UTC time is earlier than the embedded build timestamp, which indicates possible system clock rollback.

`TRIAL_EXPIRY_DATE` is inclusive. For example, `date(2026, 6, 30)` allows login through `2026-06-30` UTC and blocks from `2026-07-01` UTC.

## Build Timestamp

The embedded UTC build timestamp lives in:

```text
modules/runtime/trial_build.py
```

The checked-in timestamp is only a safe placeholder. Trial builds should refresh
it immediately before packaging.

Before creating a trial executable, run from the `Project` directory:

```powershell
python dev_tools\maintenance\write_trial_build_timestamp.py
```

Then build the executable. Because `trial_build.py` is a normal imported Python module, PyInstaller includes it automatically.

## Login Behavior

- Normal login: expired trial builds keep the login dialog open and show `TRIAL_EXPIRED_MESSAGE` in `loginStatusLabel`.
- `LOGIN_ON = False` development bypass: expired trial builds are still blocked before auto-login is created.
