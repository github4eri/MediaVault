# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**MediaVault** — an AI-powered photo/video management web app. Users upload media, Google Gemini auto-generates tags, and assets are browsable/searchable by name, tag, or category. Two roles: **admin** (full CRUD) and **guest** (read-only).

Live deployment: Render ([https://my-media-vault-yhpp.onrender.com](https://my-media-vault-yhpp.onrender.com))

## Dev Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dev server
uvicorn main:app --reload

# Seed users from .env (run once after wiping the DB)
python seed_all.py

# Create admin manually
python create_admin.py

# Reset admin password (edit update_password.py line 9 first)
python update_password.py
```

## Environment Setup

Create a `.env` file with:
```
GEMINI_API_KEY=...
ADMIN_USERNAME=admin
ADMIN_PASSWORD=...
GUEST_USERNAME=guest
GUEST_PASSWORD=...
```

The SQLite database (`media_vault_v2.db`) and default categories ("Photography", "AI Art") are created automatically on first startup.

## Architecture

**Request flow for uploads:**
`POST /upload/` → `media_service.handle_upload_process()` → saves file to `static/uploads/` → (if `.heic`: convert to JPG or MP4, keep original) → `vision.analyze_media()` (Gemini) → `database_ops.create_asset()` (SQLite)

**Auth flow:**
Login sets two cookies: `username` (httponly) and `is_logged_in`. `security.get_current_user()` reads the `username` cookie to look up the `User` row. Role gating is done by checking `user.username != 'guest'` in both templates and route handlers — there is no `role` column, just the username string.

**Module responsibilities:**
- `main.py` — all FastAPI routes
- `models.py` — SQLAlchemy models (`Category`, `DBMediaAsset`, `User`)
- `database.py` — engine/session setup (SQLite)
- `database_ops.py` — reusable DB helpers (`create_asset`, `get_or_create_category`, `get_asset_by_id`)
- `media_service.py` — orchestrates upload → AI → DB pipeline; handles HEIC conversion (still→JPG via `pillow-heif`, video/multi-frame→MP4 via `ffmpeg`)
- `vision.py` — Gemini API wrapper; auto-detects image vs. video mime type; falls back to `"Vault, Media, Uncategorized"` on error
- `security.py` — bcrypt hashing (`verify_password`, `get_password_hash`) and `get_current_user` dependency

**Templates** are in `templates/` with reusable partials under `templates/components/` (`checkbox.html`, `tags.html`, `actions.html`, `meta.html`, `preview.html`, `upload_modal.html`, `admin_tools.html`). The dashboard conditionally includes admin-only components using `{% if user.username != 'guest' %}`.

## Supported File Types

- **Images:** `png`, `jpg`, `jpeg`, `webp`, `gif`, `heic`
- **Videos:** `mp4`, `mov`
- HEIC uploads are auto-converted on the server; the original HEIC is kept in `static/uploads/` and downloadable via `/download-original/{id}` (admin only). The `DBMediaAsset.original_file_path` column stores the original filename when set.
- `ffmpeg` must be on PATH for HEIC video conversion. `pillow-heif` handles HEIC still images.

## Known Quirks

- `templates.env.cache = None` in `main.py` is a required workaround for a Python 3.14 Jinja2 hashability bug — do not remove it.
- The admin user is seeded in two separate places: `main.py` startup hook (hardcoded `admin/admin123`) and `seed_all.py` (env-driven). On Render, `seed_all.py` is the authoritative seeder.
