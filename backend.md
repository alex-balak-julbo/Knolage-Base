# Backend Plan: Flask + MySQL + REST API

| | |
|---|---|
| **Document** | backend.md |
| **Version** | 1.0 (draft) |
| **Date** | November 13, 2026 |
| **Related** | `specification_documentation.md`, `frontend.md` |

---

## 1. Goals

Provide the API behind the documentation base: a recursive tree of **folders** and **pages**, rich page content, templates with properties, full-text search, file/image storage and export (Markdown, HTML, text, ZIP).

---

## 2. Key Decisions

### 2.1 REST vs GraphQL → **REST (recommended)**

| Criterion | REST | GraphQL |
|---|---|---|
| Fit with the domain | Resource-oriented (nodes, templates, assets): natural fit | Useful for deeply nested, variable queries; our tree is loaded flat in one call |
| File upload / download (images, ZIP export) | Native (multipart, streaming) | Awkward (needs side endpoints anyway) |
| Caching | HTTP caching, ETag, simple | Needs extra tooling |
| Tooling in Flask | Mature (Flask-Smorest, OpenAPI, Swagger UI) | Possible (Strawberry/Ariadne) but extra layer |
| Typed front-end client | Generate TypeScript types from OpenAPI | Codegen from schema |
| Learning/maintenance cost | Low | Higher |

**Decision:** REST with an **OpenAPI 3** contract (auto-generated). Reconsider GraphQL only if the UI later needs many different cross-entity views.

### 2.2 Stack

| Concern | Choice |
|---|---|
| Language / runtime | Python 3.12 |
| Web framework | Flask 3 (application factory + blueprints) |
| API layer | **Flask-Smorest** (blueprints, marshmallow schemas, OpenAPI, pagination) |
| ORM / migrations | SQLAlchemy 2.x + **Flask-Migrate** (Alembic) |
| Database | **MySQL 8.0+** (InnoDB, `utf8mb4`, recursive CTEs, JSON type, FULLTEXT) |
| DB driver | PyMySQL (pure Python) or mysqlclient |
| Auth | Flask-JWT-Extended (access token + refresh token) |
| Sanitization / validation | marshmallow + a custom content validator (see 4.3) |
| Images | Pillow (resize/compress) |
| Rate limiting | Flask-Limiter |
| CORS | Flask-CORS (dev only; same-origin behind Nginx in prod) |
| Tests | pytest, pytest-flask, factory-boy |
| Lint / typing | Ruff, Black, mypy |
| Server | Gunicorn behind Nginx; Docker Compose |
| Jobs | Flask CLI commands + cron (trash purge); APScheduler optional |

### 2.3 Page content format (update to the spec)

The editor on the front end is **TipTap (ProseMirror)**. The page body is therefore stored as the **TipTap/ProseMirror JSON document** in a `JSON` column. This supersedes the `blocks[]` array described in the specification (§4.1): each former block is now a top-level node of the document (`paragraph`, `heading` level 1-2, `bulletList`, `orderedList`, `pageLink`, `image`).

The backend must therefore be able to:
1. **Validate** the JSON against an allowed-nodes/marks whitelist;
2. **Extract plain text** (`search_text`) for search;
3. **Render** the JSON to Markdown, HTML and plain text for export.

---

## 3. Architecture

```
Client (Vue) ──HTTPS──> Nginx ──> Gunicorn ──> Flask app
                                                 │
                       ┌──────────────┬──────────┴─────────┬─────────────┐
                       ▼              ▼                    ▼             ▼
                  API blueprints   Services            Models         Storage
                  (HTTP, schemas)  (business rules)   (SQLAlchemy)    (MySQL + files)
```

Layering rules:
- **Blueprints** only parse input, call a service, return a schema. No business logic.
- **Services** hold the rules (tree integrity, moves, search, export, content validation).
- **Models** map tables only.
- Every write is inside a transaction managed by the service.

### 3.1 Project structure

```
backend/
├── app/
│   ├── __init__.py            # create_app()
│   ├── config.py              # Dev / Test / Prod settings from env
│   ├── extensions.py          # db, migrate, jwt, limiter, api (smorest)
│   ├── errors.py              # error handlers (problem+json)
│   ├── models/
│   │   ├── user.py
│   │   ├── node.py            # folders + pages (single table)
│   │   ├── template.py
│   │   └── asset.py
│   ├── schemas/               # marshmallow: request/response
│   ├── api/                   # blueprints (v1)
│   │   ├── auth.py
│   │   ├── tree.py
│   │   ├── nodes.py
│   │   ├── templates.py
│   │   ├── assets.py
│   │   ├── search.py
│   │   ├── export.py
│   │   └── trash.py
│   ├── services/
│   │   ├── tree_service.py    # create, move, delete, restore, breadcrumbs
│   │   ├── content_service.py # validate JSON, extract text
│   │   ├── search_service.py
│   │   ├── export_service.py  # JSON -> md/html/txt, zip
│   │   ├── asset_service.py   # upload, resize, serve
│   │   └── template_service.py
│   └── cli.py                 # flask seed, flask purge-trash, flask reindex
├── migrations/
├── tests/
├── wsgi.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml         # api + mysql + nginx
```

---

## 4. Data Model (MySQL)

### 4.1 Tables

All tables: `ENGINE=InnoDB`, `utf8mb4`, collation **`utf8mb4_0900_ai_ci`** (case- and accent-insensitive, so `procedure` matches `Procédure`).

**`users`**

| Column | Type | Notes |
|---|---|---|
| `id` | CHAR(36) PK | UUID |
| `email` | VARCHAR(255) UNIQUE | |
| `password_hash` | VARCHAR(255) | Argon2/bcrypt |
| `display_name` | VARCHAR(120) | |
| `role` | ENUM('admin','editor','reader') | Used in V2 |
| `created_at` | DATETIME | |

> Open question Q5 (single vs multi-user) is not blocking: the schema includes `users` and `owner_id` from day one; a single seeded user is enough at first.

**`nodes`** (folders and pages in one table)

| Column | Type | Notes |
|---|---|---|
| `id` | CHAR(36) PK | UUID (can be generated by the client) |
| `type` | ENUM('folder','page') | |
| `parent_id` | CHAR(36) NULL FK → nodes.id | NULL = root |
| `name` | VARCHAR(255) | Folder name or page title |
| `icon` | VARCHAR(16) NULL | Emoji |
| `position` | BIGINT | Order among siblings |
| `template_id` | VARCHAR(64) NULL FK → templates.id | Pages only |
| `props` | JSON NULL | Template property values |
| `content` | JSON NULL | TipTap document (pages only) |
| `search_text` | MEDIUMTEXT | Plain text extracted from `content` + props |
| `version` | INT | Optimistic locking, +1 per update |
| `owner_id` | CHAR(36) FK → users.id | |
| `created_at`, `updated_at` | DATETIME | |
| `deleted_at` | DATETIME NULL | Soft delete (trash) |

Indexes:
- `INDEX (parent_id, position)` — list children in order
- `INDEX (deleted_at)`
- `INDEX (owner_id, type)`
- `FULLTEXT (name, search_text)` — full-text search (see 6)

**`templates`**

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(64) PK | `blank`, `procedure`, … |
| `name`, `description` | VARCHAR | |
| `icon` | VARCHAR(16) | |
| `props_schema` | JSON | List of `{key, label, type, options, required}` |
| `default_content` | JSON | Initial TipTap document |
| `is_system` | BOOLEAN | System templates cannot be deleted |

**`assets`**

| Column | Type | Notes |
|---|---|---|
| `id` | CHAR(36) PK | |
| `node_id` | CHAR(36) NULL FK | Page the image was pasted in |
| `filename` | VARCHAR(255) | Original name |
| `mime_type` | VARCHAR(100) | |
| `size_bytes` | INT | |
| `width`, `height` | INT | |
| `sha256` | CHAR(64) | De-duplication |
| `storage_path` | VARCHAR(500) | Relative path on disk / object key |
| `created_at` | DATETIME | |

Images are **files on disk** (volume) or S3-compatible storage, never blobs in MySQL.

### 4.2 Seed data

`flask seed` creates: the `blank` and `procedure` templates, one admin user, and demo folders/pages.

**Procedure template**
- `props_schema`: `app` (text, "Application / Specialty"), `purpose` (text, "Purpose"), `status` (select: Draft, To review, Validated).
- `default_content`: heading 2 "Prerequisites" + bullet list, heading 2 "Steps" + ordered list, heading 2 "Notes" + paragraph.

### 4.3 Content validation rules (`content_service`)

- Root node is `doc`; allowed nodes: `paragraph`, `heading` (levels 1-2), `bulletList`, `orderedList`, `listItem`, `pageLink`, `image`, `hardBreak`, `text`.
- Allowed marks: `bold`, `italic`, `link`.
- `link.href`: only `http`, `https`, `mailto`.
- `image.src`: only `/api/v1/assets/<uuid>` that exists.
- `pageLink.pageId`: must reference an existing page.
- Limits: max document size 2 MB, max nesting depth 10.
- Unknown nodes/marks are rejected (422) — this is the XSS protection: the server never stores arbitrary HTML.

### 4.4 Tree integrity rules (`tree_service`)

| Rule | Enforcement |
|---|---|
| A **folder**'s parent is a folder or root | Service check |
| A **page**'s parent is a folder, a page (sub-page) or root | Service check |
| No cycles (cannot move a node into itself or a descendant) | Recursive CTE |
| Max folder depth 8 (configurable) | Recursive CTE on create/move |
| Sub-page ↔ `pageLink` consistency | Deleting a `pageLink` removes the sub-page; deleting a sub-page removes its `pageLink` |
| Deleting a node deletes its whole subtree (soft) | Recursive CTE sets `deleted_at` |

Cycle check (descendants of the moved node):

```sql
WITH RECURSIVE sub AS (
  SELECT id FROM nodes WHERE id = :moved_id
  UNION ALL
  SELECT n.id FROM nodes n JOIN sub ON n.parent_id = sub.id
)
SELECT 1 FROM sub WHERE id = :target_parent_id;   -- row found => forbidden
```

### 4.5 Ordering (`position`)

- New siblings get `position = last + 1024` (gaps of 1024).
- `move` with `before_id` / `after_id`: new position = midpoint between neighbours.
- If the gap becomes < 1, **rebalance** that parent's children (renumber 1024, 2048, …) in the same transaction.
- Display order: folders first, then pages, then `position` (the front end sorts).

---

## 5. REST API (v1)

Base path: `/api/v1`. JSON everywhere except uploads/exports. Authentication: `Authorization: Bearer <access_token>`.

### 5.1 Endpoints

**Auth**

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Email + password → access token, sets refresh cookie |
| POST | `/auth/refresh` | New access token |
| POST | `/auth/logout` | Clears refresh cookie |
| GET | `/auth/me` | Current user |

**Tree and nodes**

| Method | Path | Purpose |
|---|---|---|
| GET | `/tree` | **Lightweight flat list** of all non-deleted nodes: `id, type, parent_id, name, icon, position, template_id, updated_at` (no content) |
| POST | `/nodes` | Create folder or page (`type`, `parent_id`, `name`, `template_id`) |
| GET | `/nodes/{id}` | Full node (page: props + content + version) |
| PATCH | `/nodes/{id}` | Update `name`, `icon`, `props`, `content` (requires `If-Match: <version>`) |
| POST | `/nodes/{id}/move` | Move/reorder: `{ parent_id, before_id?, after_id? }` |
| GET | `/nodes/{id}/breadcrumb` | Ancestors list |
| DELETE | `/nodes/{id}` | Soft delete (subtree); response includes the count of affected nodes |
| GET | `/nodes/{id}/stats` | Number of descendants (for the delete confirmation) |

**Trash**

| Method | Path | Purpose |
|---|---|---|
| GET | `/trash` | Deleted top-level items |
| POST | `/trash/{id}/restore` | Restore subtree (to original parent, or root if parent is gone) |
| DELETE | `/trash/{id}` | Permanent delete |
| DELETE | `/trash` | Empty trash |

**Templates**

| Method | Path | Purpose |
|---|---|---|
| GET | `/templates` | List |
| POST / PATCH / DELETE | `/templates[/{id}]` | Manage custom templates (V2) |

**Assets**

| Method | Path | Purpose |
|---|---|---|
| POST | `/assets` | Multipart upload (field `file`, optional `node_id`) → `{ id, url, width, height }` |
| GET | `/assets/{id}` | Serve the image (cache headers, ETag) |

**Search**

| Method | Path | Purpose |
|---|---|---|
| GET | `/search` | Query params below |

`GET /search?q=backup&scope=all|title|content&folder_id=…&template_id=…&status=…&limit=20&offset=0`

Response item:

```json
{
  "id": "p_42",
  "name": "Weekly backup",
  "icon": "🛠️",
  "path": [{"id": "f_it", "name": "IT"}, {"id": "f_bk", "name": "Backups"}],
  "snippet": "…check that the backup completed…",
  "matches": [[16, 22]],
  "updated_at": "2026-11-13T10:12:00Z"
}
```

**Export / backup**

| Method | Path | Purpose |
|---|---|---|
| GET | `/export/{id}?format=md|html|txt&images=embed|assets` | Page → single file; folder → single file or ZIP (see below) |
| GET | `/export/{id}?format=zip` | Folder → ZIP mirroring the tree (one file per page, images in `assets/`) |
| GET | `/backup` | Full JSON backup of the base |
| POST | `/backup/restore` | Restore from a backup (admin) |

**Health**

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + DB check |

### 5.2 Conventions

- **Errors:** RFC 7807 `application/problem+json`: `{ "type", "title", "status", "detail", "errors": {…} }`.
- **Status codes:** 200, 201, 204, 400 (bad input), 401, 403, 404, 409 (version conflict), 422 (validation), 429.
- **Optimistic locking:** `PATCH` requires `If-Match: <version>`; mismatch returns **409** with the current version so the UI can offer reload/overwrite.
- **Idempotent creation:** the client may send its own UUID as `id` to make retries safe.
- **Pagination:** `limit` / `offset` with `X-Total-Count` header (search, trash).
- **Versioning:** `/api/v1` prefix; breaking changes go to `/v2`.
- **OpenAPI:** served at `/api/v1/openapi.json`, Swagger UI at `/api/docs` (dev only).

---

## 6. Search

### 6.1 Approach

`search_text` holds the plain text of the page (content + property values), refreshed on every save by `content_service`.

| Scope | Query |
|---|---|
| `title` | `name LIKE %q%` (accent/case-insensitive thanks to the collation) |
| `content` | `MATCH(search_text) AGAINST (:q IN NATURAL LANGUAGE MODE)` or `LIKE` for short terms |
| `all` | Title matches first, then content matches |

Notes:
- InnoDB FULLTEXT ignores very short words (default `innodb_ft_min_token_size = 3`) and stop words; for terms under 3 characters fall back to `LIKE`.
- Substring matching inside a word is not supported by FULLTEXT → combine with `LIKE` for partial matches (acceptable up to a few thousand pages).
- Filter `folder_id` using the recursive CTE of descendants; `template_id`/`status` filter on `template_id` and `JSON_EXTRACT(props, '$.status')`.
- Snippets and `matches` offsets are computed in Python around the first hit (plain text, no HTML — the front end highlights safely).
- Ranking: title hit > content hit; then `updated_at` desc.

### 6.2 Scaling path

If the base grows beyond what MySQL FULLTEXT handles comfortably: add **Meilisearch** (typo tolerance, fast prefix search) fed by the same `search_text`, behind the same `/search` endpoint.

---

## 7. Export

`export_service` converts the TipTap JSON to each format through one small recursive renderer (the node set is tiny).

| Format | Rules |
|---|---|
| **HTML** | Standalone document; headings shifted by hierarchy level; images embedded (base64) or relative `assets/` |
| **Markdown** | `#` headings per hierarchy, `-` / `1.` lists, `**bold**`, `*italic*`, links, `![](…)` images; properties as YAML front matter |
| **Text** | Headings upper-cased/underlined, lists with `-`, images as `[image]` |
| **ZIP** | `folder/subfolder/page.md` mirroring the tree; `assets/` for images; names sanitized and de-duplicated |

Rules (match the specification, EXP-01 to EXP-08):
- Folder export is **recursive** and includes sub-pages (`pageLink`) after their parent page.
- Heading level = hierarchy depth, capped at 6.
- Large exports are **streamed** (generators / `zipfile` on a spooled temp file); `Content-Disposition: attachment` with a slugified filename.

---

## 8. Security

| Topic | Measure |
|---|---|
| Authentication | Argon2 password hashes; short-lived access token (15 min) + refresh token in `HttpOnly; Secure; SameSite=Lax` cookie |
| Authorization | Every query scoped by `owner_id` (V1); roles `admin/editor/reader` in V2 |
| XSS | No raw HTML stored; strict JSON content validation; links restricted to safe schemes; CSP headers set by Nginx |
| Uploads | Allowed types: PNG, JPEG, WebP, GIF; verified with Pillow (not only extension); max 5 MB; re-encoded and EXIF stripped; random storage names |
| SQL injection | ORM / bound parameters only |
| Abuse | Flask-Limiter (login: 5/min/IP; uploads and search: sensible limits) |
| Transport | HTTPS only, HSTS |
| Secrets | Environment variables (`.env` not committed) |
| CORS | Disabled in production (same origin); allow-list in dev |
| Logs | Structured JSON logs; no passwords/tokens/content in logs |

---

## 9. Configuration and Environments

| Variable | Purpose |
|---|---|
| `FLASK_ENV`, `SECRET_KEY` | Flask |
| `DATABASE_URL` | `mysql+pymysql://user:pass@db:3306/docbase?charset=utf8mb4` |
| `JWT_SECRET_KEY`, `JWT_ACCESS_TTL`, `JWT_REFRESH_TTL` | Auth |
| `UPLOAD_DIR`, `MAX_UPLOAD_MB` | Assets |
| `MAX_FOLDER_DEPTH` | Default 8 |
| `TRASH_RETENTION_DAYS` | Default 30 |
| `CORS_ORIGINS` | Dev only |

Environments: `development` (Docker Compose + hot reload), `test` (ephemeral MySQL), `production`.

---

## 10. Testing Strategy

Priority test cases (pytest, real MySQL in Docker/CI):

1. **Tree rules:** folder cannot go under a page; no cycle; depth limit; page can be root.
2. **Move/reorder:** before/after/inside; rebalancing when gaps run out; sibling order preserved after reload.
3. **Delete/restore:** recursive soft delete; counts correct; `pageLink` ↔ sub-page cleanup; restore when parent was deleted.
4. **Content validation:** rejects unknown nodes, bad link schemes, foreign image URLs, oversize docs.
5. **Optimistic locking:** concurrent PATCH returns 409.
6. **Search:** accent/case-insensitive; title/content/all scopes; folder filter; short terms; snippet offsets.
7. **Export:** golden-file tests for md/html/txt; ZIP structure; heading-level cap; sub-pages included.
8. **Assets:** type spoofing rejected; resize; de-duplication by hash.
9. **Auth:** login, refresh, protected routes, rate limit.

Targets: ≥ 85 % coverage on `services/`; CI runs Ruff, mypy, pytest.

---

## 11. Deployment

- **Docker Compose:** `nginx` (TLS, static front end, proxies `/api`), `api` (Gunicorn, 2-4 workers), `db` (MySQL 8 with a named volume).
- **Migrations:** `flask db upgrade` on deploy (run once per release).
- **Backups:** nightly `mysqldump` + copy of the `uploads` volume; restore procedure documented and tested.
- **Trash purge:** `flask purge-trash` via cron daily.
- **Monitoring:** `/health`, access/error logs, optional Sentry.

---

## 12. Implementation Plan

| Phase | Tasks | Deliverable |
|---|---|---|
| **B0 — Setup** (2-3 days) | Repo, Docker Compose, Flask factory, config, MySQL connection, Alembic, CI (lint + tests), health endpoint | Running skeleton |
| **B1 — Data & auth** (3-4 days) | Models, migrations, seed (templates, admin), login/refresh/me | Authenticated API |
| **B2 — Tree core** (5-6 days) | `/tree`, create/get/patch/delete, `move` with ordering, cycle/depth checks, breadcrumb, stats, optimistic locking | Tree CRUD + move, fully tested |
| **B3 — Content & assets** (4-5 days) | Content validator, `search_text` extraction, `pageLink` ↔ sub-page logic, image upload/serve/compress | Pages with images and sub-pages |
| **B4 — Search** (3 days) | FULLTEXT + LIKE strategy, scopes, filters, snippets | `/search` |
| **B5 — Export & backup** (4-5 days) | JSON→md/html/txt renderer, ZIP export, JSON backup/restore | Downloads |
| **B6 — Trash & hardening** (3 days) | Trash endpoints + purge job, rate limits, security headers, logs, OpenAPI polish | Production-ready API |
| **B7 — Release** (2 days) | Production compose, TLS, backups, docs | Deployed v1 |

Rough total: **26-32 working days** for one developer (parallelizable with the front end after B2).

### Suggested order of work with the front end
1. B0-B2 → front end can build the tree, creation and drag & drop against real endpoints.
2. B3 → editor with image paste and sub-pages.
3. B4-B5 → search UI and export dialog.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| MySQL FULLTEXT limits (short words, no substring) | Hybrid with `LIKE`; Meilisearch as an upgrade path |
| Concurrent edits overwrite each other | Optimistic locking + 409 handling |
| Tree corruption (bad moves) | All rules in `tree_service`, wrapped in transactions, heavily tested |
| Large ZIP exports block workers | Streaming + size limits; async job if needed |
| Content schema drift with the editor | Shared schema documented once; contract tests with front-end sample documents |
| Image storage growth | Compression, de-duplication, orphan cleanup command (`flask clean-assets`) |

---

## 14. Open Points (backend side)

1. Single user or multi-user at launch (Q5)? Affects roles/permissions work in B1/B6.
2. File storage: local volume or S3-compatible bucket?
3. Is a page version history needed (V2)? If yes, add a `node_versions` table (snapshot per save, rate-limited).
4. Hosting target (on-premise server, VPS, cloud)?
