# Git: Why ignore `__pycache__/` and `*.pyc`, and how to untrack them safely

**File purpose:** Quick reference for ignoring Python bytecode files, cleaning them from Git *tracking*, and understanding what `git rm --cached` actually does.

---

## Why you need `.gitignore` entries for `__pycache__/` and `*.pyc`

When you run Python (e.g., `python main.py`), Python can generate **bytecode cache files**:

- `__pycache__/` folders
- `*.pyc` files (compiled bytecode, e.g., `greeting_menu.cpython-312.pyc`)

These files are:
- **auto-generated**
- **machine/version specific** (Python version, platform)
- **not source of truth**
- likely to cause noise + conflicts in Git

### What happened in your repo

Git blocked your checkout because `.pyc` files were modified locally and Git was trying to switch commits:

```text
error: Your local changes to the following files would be overwritten by checkout:
        Project/modules/menu/__pycache__/greeting_menu.cpython-312.pyc
        Project/modules/menu/__pycache__/logout_menu.cpython-312.pyc
Please commit your changes or stash them before you switch branches.
Aborting
```

That is exactly why these should be ignored: Python regenerates them, but Git treats them like important tracked files if they were ever committed.

---

## How to ignore them properly in `.gitignore`

Add these lines in a `.gitignore` that is at or above the folders you want to ignore (repo root is simplest):

```gitignore
__pycache__/
*.pyc
```

### Ignoring `/db/` (your special case)

Because your `/db` folder is **outside** the `Project/` folder, you must ignore it **from the repo root** (one level above `Project/`), not from inside `Project/`.

Repo-root `.gitignore` example:

```gitignore
/db/
__pycache__/
*.pyc
```

Your commit message confirms this intention:

```text
commit bfdf3d051e4e317794d6961150c503ea65fc0972 (HEAD -> main)
...
    Ignore db directory at repo root
```

---

## If you already committed & pushed `__pycache__/` or `*.pyc`

Important rule:

> **`.gitignore` does NOT automatically remove files that are already tracked.**

If `.pyc` files were committed before, Git will keep tracking them until you explicitly remove them **from the index** (tracking), while keeping them on disk.

### Correct fix (safe): remove from tracking only

1) Make sure `.gitignore` contains:
```gitignore
__pycache__/
*.pyc
```

2) Remove tracked bytecode from the index (tracking):
```bash
git rm -r --cached __pycache__
git rm --cached '*.pyc'
```

3) Commit and push:
```bash
git commit -m "Stop tracking Python bytecode"
git push
```

After that:
- Your working directory can still generate `.pyc` files locally
- Git will stop seeing them
- Checkout/switch commits will not be blocked by them anymore

---

## What `git rm --cached` removes (and what it does NOT)

### What gets removed
- The files are removed from **Git tracking** (the **index**).
- They will appear in Git as “deleted” in the next commit **only in the repository**, not on your disk.

### What does *not* get removed
- The files are **NOT deleted from your filesystem** when `--cached` is used.

This is why you should not panic about losing `.py`, `.ui`, `.svg`, etc. when the command includes `--cached`.

---

## Why it looked like everything got removed

You ran a PowerShell command intended to remove only `__pycache__` folders, but the expanded arguments caused Git to untrack a lot more than expected.

This was the console output (your real output):

```text
git rm -r --cached (Get-ChildItem -Recurse -Directory __pycache__)
rm 'Project/AppData/vegetables.json'
rm 'Project/Documentation/DIALOG_AUDIT_REPORT.md'
rm 'Project/Documentation/admin_settings.md'
rm 'Project/Documentation/barcode_manager.md'
rm 'Project/Documentation/cancel_all_functionality.md'
rm 'Project/Documentation/dialog_wrapper.md'
rm 'Project/Documentation/logout_and_titlebar.md'
rm 'Project/Documentation/main_py_overview.md'
rm 'Project/Documentation/manual_entry.md'
rm 'Project/Documentation/overlay_manager.md'
rm 'Project/Documentation/product_menu.md'
rm 'Project/Documentation/sales_frame_setup.md'
rm 'Project/Documentation/scanner_input_infocus.md'
rm 'Project/Documentation/tableOperation.md'
rm 'Project/Documentation/vegetable_entry_dialog_and_selection.md'
rm 'Project/Documentation/vegetable_menu.md'
rm 'Project/Project_Journal.md'
rm 'Project/README.md'
rm 'Project/__pycache__/config.cpython-312.pyc'
rm 'Project/__pycache__/config.cpython-313.pyc'
rm 'Project/__pycache__/greeting_menu.cpython-312.pyc'
rm 'Project/__pycache__/main.cpython-313.pyc'
rm 'Project/assets/icons/admin.svg'
rm 'Project/assets/icons/combo_arrow_down.svg'
rm 'Project/assets/icons/delete.svg'
rm 'Project/assets/icons/device.svg'
rm 'Project/assets/icons/down_arrow.svg'
rm 'Project/assets/icons/greeting.svg'
rm 'Project/assets/icons/logout.svg'
rm 'Project/assets/icons/main_background.svg'
rm 'Project/assets/icons/product.svg'
rm 'Project/assets/icons/reports.svg'
rm 'Project/assets/icons/vegetable.svg'
rm 'Project/assets/main.qss'
rm 'Project/assets/menu.qss'
rm 'Project/assets/sales.qss'
rm 'Project/config.py'
rm 'Project/main.py'
...
rm 'Project/ui/admin_menu.ui'
rm 'Project/ui/cancel_sale.ui'
rm 'Project/ui/devices_menu.ui'
rm 'Project/ui/greeting_menu.ui'
rm 'Project/ui/logout_menu.ui'
rm 'Project/ui/main_window.ui'
rm 'Project/ui/manual_entry.ui'
rm 'Project/ui/menu_frame.ui'
rm 'Project/ui/on_hold.ui'
rm 'Project/ui/payment_frame.ui'
rm 'Project/ui/product_menu.ui'
rm 'Project/ui/reports_menu.ui'
rm 'Project/ui/sales_frame.ui'
rm 'Project/ui/vegetable_entry.ui'
rm 'Project/ui/vegetable_menu.ui'
rm 'Project/ui/view_hold.ui'
```

### What you were worried was happening
It *looked like* Git was **deleting your real project files** (`.py`, `.ui`, docs, icons).

### Why you shouldn’t be worried
Because of the key detail:

- you used `--cached`
- that means **Git index-only removal**
- your actual files were still on disk

The “rm …” lines are Git telling you:
> “I’m removing these from tracking.”

Not:
> “I’m deleting them from your computer.”

---

## How to undo a mistaken `git rm --cached` before committing

If you ever run a too-broad `git rm --cached ...` and you **have not committed yet**, you can restore staging:

```bash
git restore --staged .
```

That re-stages everything back to tracked state (undoes the “deleted from index” effect).

If you want to discard working-tree changes too (dangerous if you have real edits):
```bash
git reset --hard HEAD
```

---

## Summary: do this and you’re done

1) Put in repo-root `.gitignore`:
```gitignore
/db/
__pycache__/
*.pyc
```

2) If `__pycache__/` and `*.pyc` were previously committed:
```bash
git rm -r --cached __pycache__
git rm --cached '*.pyc'
git commit -m "Stop tracking Python bytecode"
git push
```

That prevents:
- checkout blocks
- accidental `.pyc` commits
- noisy diffs

---

**End of note.**
