# Docbase

Documentation base: folders, pages (blocks, templates, sub-pages), search, export.

- `backend/`  Flask + MySQL REST API (see `backend/README.md`)
- `frontend/` Vue 3 + Tailwind client (see `frontend/README.md`)
- `docker-compose.yml` runs everything: `docker compose up -d --build`, then `docker compose exec api flask init-db`
  and `docker compose exec api flask seed`, and open http://localhost:8080
- Design documents: `specification_documentation.md`, `backend.md`, `frontend.md` (kept alongside the code)
