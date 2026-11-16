# Docbase backend (Flask + MySQL, REST)

Implements `backend.md` (phases B0 to B6, minus backup/restore). Base path: `/api/v1`.

## Run it

```bash
# 1. Quick local run, no database (in-memory: everything is lost on restart)
pip install -r requirements.txt
SEED_DEMO=1 flask --app wsgi:app run     # login admin@example.com / admin1234, demo tree included
# then open http://127.0.0.1:5000/api/v1/health

# 2. With MySQL (Docker)
cp .env.example .env             # edit the secrets
docker compose up -d --build
docker compose exec api flask init-db       # or: alembic revision --autogenerate -m init && alembic upgrade head
docker compose exec api flask seed --password 'a-strong-password'
```

Switching storage: `STORAGE=memory|sql` (defaults to `sql` when `DATABASE_URL` is set).
Other commands: `flask create-user EMAIL --role editor`, `flask purge-trash` (cron, daily).

## Tests

```bash
python -m unittest discover -s tests -t .          # 83 tests on the in-memory repo (11 SQL contract tests are skipped without SQLAlchemy)
TEST_REPO=sql python -m unittest discover -s tests -t .   # same suite on SQLAlchemy/SQLite
```

## Layout

```
app/
  api/            HTTP only: auth_routes, node_routes (tree, nodes, trash), misc_routes (templates, assets, search, export, health)
  services/       tree (all tree rules), content (TipTap JSON validation), search, assets, export, ordering
  repos/          base (contract), memory, sql (SQLAlchemy models + queries)
  auth.py  errors.py  config.py  seed.py  cli.py
migrations/       Alembic (env.py reads DATABASE_URL)
tests/            unit, API (full flows), repository contract
```

## API summary

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/login`, `/auth/refresh`, `/auth/logout` | access token in body, refresh token in HttpOnly cookie |
| GET | `/auth/me` | |
| GET | `/tree` | flat list, no content |
| POST | `/nodes` | `type`, `name`, `parent_id`, `template_id`, `props`, `content`, `icon`, `id`, `link` |
| GET / PATCH / DELETE | `/nodes/{id}` | PATCH needs `If-Match: <version>` (428 if missing, 409 on conflict) |
| POST | `/nodes/{id}/move` | `parent_id` (null = root), optional `before_id` or `after_id` |
| GET | `/nodes/{id}/breadcrumb`, `/nodes/{id}/stats` | |
| GET / DELETE | `/trash` | list roots / empty |
| POST / DELETE | `/trash/{id}/restore`, `/trash/{id}` | restore / purge |
| GET | `/templates` | |
| POST / GET | `/assets`, `/assets/{id}` | multipart `file`; GET needs no auth header (see below) |
| GET | `/search?q&scope=all|title|content&folder_id&template_id&status&limit&offset` | |
| GET | `/export/{id}?format=md|html|txt|zip` | folders are exported recursively |
| GET | `/health` | |

Errors are `application/problem+json` with a stable `code` (`invalid_parent`, `cycle`, `max_depth`, `version_conflict`, `invalid_content`, ...).

## Behaviours worth knowing

- **Sub-pages:** a page whose parent is a page always has a `pageLink` in the parent's content. The server adds it on create/move/restore and removes it on delete/move out. Pass `link: false` on create when the editor will insert the link itself at the cursor; the next PATCH never duplicates it. Removing a `pageLink` in a PATCH deletes the sub-page (move it to the trash).
- **Moves/deletes that touch another page** (the parent's content changes) list that page in `affected_ids`; the client should refetch it.
- **Content** is validated against a strict whitelist (paragraph, heading 1-2, lists, image, pageLink, bold, italic, link). Unknown nodes, `javascript:` links and foreign image URLs are rejected with 422.
- **Assets** are served by capability URL (unguessable UUID, no auth) because `<img>` tags cannot send a Bearer header. If that is not acceptable, switch to cookie auth or signed URLs.
- **Search** is accent/case-insensitive. On MySQL it uses `LIKE` on the `utf8mb4_0900_ai_ci` collation; a FULLTEXT index exists for a future `MATCH()` path or Meilisearch.
- Login rate limiting is in-process; use Flask-Limiter + Redis with several workers.

## Differences from backend.md

The sandbox this was built in had no package index, so only Flask, PyJWT and Pillow were available. To keep everything testable:
- Plain Flask blueprints + small validators instead of Flask-Smorest/marshmallow (no auto-generated OpenAPI yet).
- PyJWT directly instead of Flask-JWT-Extended; Werkzeug (scrypt) instead of Argon2.
- A repository layer (`Repo`) with an in-memory implementation for tests and a SQLAlchemy implementation for MySQL.
- Alembic is configured but no migration is committed: generate the first one against your MySQL.

## Not done yet

Backup/restore endpoints, custom template CRUD, orphan-asset cleanup command, FULLTEXT search path, OpenAPI document, refresh-token revocation.
