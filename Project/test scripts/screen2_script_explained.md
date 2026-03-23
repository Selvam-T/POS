# Screen 2 Ads Demo Script (screen2_ads_demo.py)

## Purpose
This script is a standalone demo for the Screen 2 Ads tab in the admin menu UI. It loads the existing admin menu UI, focuses the Screen 2 Ads tab, and implements file-based add/remove/reorder/preview logic for ad images stored in the local assets/ads folder.

It is intended for local testing and design validation before integrating the same behavior into the main POS app.

## How It Works
- Loads [ui/admin_menu.ui](../ui/admin_menu.ui) using `uic.loadUi()`.
- Uses Project/assets/ads as the "source of truth" for active ads.
- Displays thumbnails in the list via in-memory scaling (no thumbnail files written).
- Persists order by renaming files with numeric prefixes (1_, 2_, 3_, ...).

## Storage Model
- Folder: Project/assets/ads
- Any supported image file placed in this folder is considered part of the active rotation.
- Order is determined by numeric prefix (example: 1_image.jpg, 2_image.jpg).
- Reorder operations rename files to re-apply prefixes in list order.

## Acceptance Criteria (Rejection Rules)
Images are accepted only if all criteria pass:
- Format: .jpg, .jpeg, .png
- Resolution: exactly 1280x800
- Aspect ratio: 16:10
- Quantity limit: max 6 images

If any rule fails, the image is rejected and not copied into assets/ads.

## Error / Status Messages
Status messages are shown in the screen2StatusLabel.

Common messages:
- "Max 6 images reached."
- "Images added." (or a version that includes a rejection reason)
- "File rejected - <reason>."
- "Select an image to remove."
- "Failed to remove image."
- "Image removed."

Rejection reasons (short labels):
- Invalid format
- Unreadable image
- Wrong resolution
- Wrong aspect ratio

## Function Reference

### `Screen2AdsDemo.__init__`
- Loads the UI, ensures ads folder exists, wires signals, refreshes list, focuses Screen 2 tab.

### `_ensure_ads_dir()`
- Creates assets/ads if missing.

### `_wire()`
- Connects button handlers and list selection changes to their respective slots.

### `_focus_screen2_tab()`
- Sets the current tab to the Screen 2 Ads tab if available.

### `_status(message)`
- Writes a message to screen2StatusLabel.

### `_count_label(count)`
- Updates the "X / 6 images" count label.

### `_list_ad_files()`
- Returns absolute paths for all allowed ads in assets/ads, sorted by numeric prefix.

### `_sort_key(filename)`
- Sorting helper; primary sort is numeric prefix, fallback to alpha.

### `_strip_prefix(filename)`
- Removes any leading numeric prefix and underscore from a filename.

### `_refresh_list(select_index=-1)`
- Rebuilds the list widget from disk and updates preview/labels.

### `_make_item(path)`
- Creates a list item with thumbnail icon and stores file path in `Qt.UserRole`.

### `_on_selection_changed()`
- Loads selected image into preview label.

### `_set_preview(path)`
- Scales selected image into the preview label using KeepAspectRatio.

### `_add_images()`
- Opens file picker, validates selection, copies accepted files into assets/ads, and renames with prefix.

### `_validate_image(path)`
- Checks file extension, readability, resolution, and aspect ratio.

### `_build_add_status(added, rejected, remaining)`
- Returns a concise status string after an add attempt.

### `_unique_base(base)`
- Ensures destination filename uniqueness if a conflict exists.

### `_remove_selected()`
- Deletes the selected image and renumbers remaining files.

### `_move_selected_up()` / `_move_selected_down()`
- Moves the selected list item and persists ordering by renaming files.

### `_swap_rows(row_a, row_b)`
- Swaps two list items and saves the new order.

### `_persist_order_from_list()`
- Collects list order and renumbers files to match.

### `_renumber_files(ordered_paths=None)`
- Renames files to sequential numeric prefixes (safe temp renames first).

### `main()`
- Launches the dialog in a standalone QApplication.

## How To Run
From the project root:

python "test scripts/screen2_ads_demo.py"

## Notes
- Thumbnails and previews are generated in memory using QPixmap scaling.
- The list is IconMode and suited for visual browsing.
- This script is independent of the POS runtime; no database is used.
