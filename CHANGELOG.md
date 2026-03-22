# Changelog

All notable changes to this project will be documented in this file.

## 2026-03-22

### Added
- Added `requirements.txt` with pinned runtime dependencies.
- Added `CHANGELOG.md`.

### Changed
- Updated README dependency installation to use `pip install -r requirements.txt`.
- Reworked search results backend to use `yt-dlp` helpers instead of `py_yt`.
- Implemented audio quality filtering based on available ABR data.

### Fixed
- Enforced private-chat-only checks across command handlers.
- Added session TTL and bounded pending-session cleanup for download/search/info/thumb workflows.
- Improved temporary file cleanup to remove full temp directories recursively.
- Added additional cleanup for token-specific temp folders on success and failure paths.
