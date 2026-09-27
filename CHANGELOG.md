# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-09-26

### Added

- Initial release. Adds an N-way content-mode toggle (e.g. Beginner/Advanced) to the header that
  shows or hides content marked with `data-fcm-hide` per mode, without reloading the page. The
  active mode persists across pages via `localStorage`.
- Content marking via `attr_list` attributes (a marked heading hides its whole section), `<div>` /
  `<span>` wrappers, or CSS rules on the `data-fcm-mode` attribute set on `<html>`.
- Per-mode `label`, `default`, `icon`, `description` (tooltip), and `announcement` (toast text).
- Links to content hidden in the current mode switch to the nearest mode that shows it.
- `query_param` option to set the mode from a URL, e.g. `?mode=advanced`.
- `collapse_labels` option to show icons only below a 45em viewport width. Without it, a toggle
  that doesn't fit in Material's header moves to its own row.
- `hide_toc_entries`, `wrapper_class`, `insert_selector`, `attribute`, `storage_key`,
  `aria_label`, and `show_toast` options.
- `--fcm-*` custom properties for theming the toggle.
- `fcm:modechange` event on `document` for analytics.
