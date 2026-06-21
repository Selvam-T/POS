# Runtime Filesystem Helpers

## Files

- `modules/runtime/data.py`
- `modules/runtime/paths.py`
- `modules/runtime/__init__.py`

## Runtime Data

`modules.runtime.data` manages writable application directories.

- `ensure_appdata_dir(path=None)` creates and returns the configured application data directory.
- `ensure_ads_dir(path=None)` creates and returns the configured Screen 2 advertisements directory.
- Default locations come from `config.APPDATA_DIR` and `config.ADS_DIR`.
- An explicit path can be supplied by tests or callers that need an alternate destination.

These helpers are used by settings persistence, Screen 2 advertisement management, and the customer display.

## Runtime Resource Paths

`modules.runtime.paths` resolves read-only application resources in source and packaged execution.

- `ui_path(filename)` resolves files under `config.UI_DIR`.
- `asset_path(*parts)` resolves files under `config.ASSETS_DIR`.
- `stylesheet_path(filename)` resolves files under `config.QSS_DIR`.
- `load_stylesheet(path)` reads a stylesheet and resolves its relative asset URLs.
- `resolve_stylesheet_urls(text, assets_dir=None)` converts `url(assets/...)` references to runtime absolute paths.

These helpers are used by the main window, dialogs, sales panel, login, customer display, and menu controllers.

## Package Exports

`modules.runtime` re-exports the public data-directory and resource-path helpers. Callers may import from the package or from the specific `data` and `paths` modules.

## Tests

`tests/test_runtime_assets_data.py` verifies directory creation, path resolution, and stylesheet URL rewriting.
