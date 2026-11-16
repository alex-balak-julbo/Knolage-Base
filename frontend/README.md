# Docbase frontend (Vue 3 + Tailwind CSS v4)

Implements `frontend.md` against the REST API in `../backend`.

## Run it

```bash
# terminal 1: API with demo data (login admin@example.com / admin1234)
cd backend && pip install -r requirements.txt
SEED_DEMO=1 flask --app wsgi:app run          # http://127.0.0.1:5000

# terminal 2: this app
cd frontend && pnpm install                   # or npm install
pnpm dev                                      # http://localhost:5173 (proxies /api to the API)
```

`pnpm typecheck` runs `vue-tsc`, `pnpm build` produces `dist/`, `pnpm test:unit` runs the logic tests
(Node 22+, no extra dependency). With Docker: `docker compose up --build` from the repository root, then open http://localhost:8080.

## What is in it

| Area | Files |
|---|---|
| Tree rules, drag & drop planning, search highlight, document sanitising (pure TypeScript, unit-tested) | `src/lib/*` |
| REST client (Bearer token in memory, single refresh on 401, problem+json errors) | `src/api/*` |
| State (Pinia): tree, open page + autosave, search, auth, templates, UI | `src/stores/*` |
| Sidebar tree: keyboard model, context menu, HTML5 drag & drop (before / inside / after, auto-expand, auto-scroll, root zone, undo) | `src/components/tree/*`, `src/composables/useTreeDnd.ts` |
| Editor: TipTap with slash menu, toolbar, image paste/drop upload, sub-page cards | `src/components/editor/*` |
| Template properties, dialogs (prompt, confirm, template picker, move-to, export, version conflict) | `src/components/page`, `src/components/dialogs` |
| Views: login, home, page, trash | `src/views/*` |

## Behaviour worth knowing

- **Autosave**: 800 ms debounce, `If-Match` version on every save, flush on route change and on tab close, retry on network/5xx errors,
  a dialog on version conflict (reload / overwrite).
- **Server whitelist**: the editor schema only allows what the API accepts (headings 1-2, lists, image, bold, italic, link, sub-page card);
  `sanitizeForSave` removes unsafe links and foreign images before sending, so a page can never become unsaveable.
- **Sub-pages**: created from `/ Sub-page` (or the toolbar). The editor inserts the card at the cursor; dropping a page onto another page in the tree
  turns it into a sub-page (the server keeps the card in sync and the open page is reloaded when it changed).
- **Drag & drop** uses native HTML5 events, which touch screens do not fire: use "Move to…" (⋯ menu or Ctrl+M) there.
- **Language / theme**: FR or EN (browser language by default), light / dark / system. Both in the sidebar footer.

## Not done yet

Block drag handle and per-block menu, Ctrl+K link shortcut, highlighting search hits inside the page, folder overview page,
virtual scrolling for very large trees, Playwright end-to-end tests, toolbar labels switching language without a reload.
