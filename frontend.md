# Frontend Plan: Vue.js + Tailwind CSS

| | |
|---|---|
| **Document** | frontend.md |
| **Version** | 1.0 (draft) |
| **Date** | November 13, 2026 |
| **Related** | `specification_documentation.md`, `backend.md` |

---

## 1. Goals

A fast, keyboard-friendly single-page app where users browse a **recursive tree of folders and pages**, edit pages in a **block-style rich-text editor**, fill **template properties**, **drag and drop** items in the tree, **search**, and **export**.

---

## 2. Stack

| Concern | Choice | Why |
|---|---|---|
| Framework | **Vue 3** (Composition API, `<script setup>`) | Requested |
| Language | **TypeScript** | Safer refactors, typed API client |
| Build tool | **Vite** | Fast dev server, simple production build |
| Styling | **Tailwind CSS v4** (`@tailwindcss/vite`) + `@tailwindcss/typography` | Requested; `prose` classes for editor content |
| State | **Pinia** | Official store |
| Routing | **Vue Router 4** | Deep links to pages |
| Server state | **TanStack Query (Vue)** | Caching, optimistic updates, retries |
| HTTP | `ofetch` or Axios (thin wrapper) | Auth header, refresh, error mapping |
| API types | **openapi-typescript** (generated from the backend OpenAPI) | One source of truth |
| Editor | **TipTap 2/3** (`@tiptap/vue-3`, ProseMirror) | Block-like editing, slash menu, drag handle, JSON output |
| UI primitives | **Headless UI for Vue** (menus, dialogs, comboboxes) | Accessible, Tailwind-friendly |
| Icons | `lucide-vue-next` | Lightweight |
| Utilities | VueUse | Debounce, hotkeys, media queries |
| i18n | `vue-i18n` (French default, English-ready) | |
| Tests | Vitest + Vue Test Utils, MSW (API mocks), **Playwright** (E2E) | |
| Quality | ESLint, Prettier, `vue-tsc` | |

> BlockNote (mentioned in the specification) is React-only, so **TipTap** is the editor for Vue.

---

## 3. Application Structure

```
frontend/
├── index.html
├── vite.config.ts              # dev proxy /api -> Flask
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/index.ts
│   ├── api/
│   │   ├── client.ts           # fetch wrapper, auth, 401 refresh
│   │   ├── schema.d.ts         # generated from OpenAPI
│   │   └── endpoints/          # tree.ts, nodes.ts, search.ts, assets.ts, export.ts, auth.ts
│   ├── stores/
│   │   ├── tree.ts             # nodes map, children index, expanded state
│   │   ├── page.ts             # open page, dirty flag, save status
│   │   ├── search.ts
│   │   ├── ui.ts               # theme, sidebar, dialogs, toasts
│   │   └── auth.ts
│   ├── composables/
│   │   ├── useTreeDnd.ts       # drag & drop logic (zones, validation)
│   │   ├── useTreeKeyboard.ts  # arrow keys, F2, Delete…
│   │   ├── useAutosave.ts      # debounce + flush + conflict handling
│   │   ├── useUndoToast.ts
│   │   └── useDownload.ts
│   ├── components/
│   │   ├── layout/             # AppShell, Sidebar, TopBar, Breadcrumb
│   │   ├── tree/               # TreeView, TreeNode, TreeContextMenu, MoveToDialog, DropIndicator
│   │   ├── editor/             # PageEditor, SlashMenu, BlockMenu, BubbleToolbar, extensions/
│   │   ├── page/               # PageHeader, PropertiesPanel, TemplatePicker, SaveStatus
│   │   ├── search/             # SearchBar, SearchResults, ScopeSelect
│   │   ├── export/             # ExportDialog
│   │   └── common/             # ConfirmDialog, PromptDialog, Toast, EmptyState, Spinner
│   ├── views/                  # PageView, HomeView, SearchView, TrashView, LoginView
│   ├── lib/                    # tree utils, search highlight, slug, icons
│   ├── i18n/                   # fr.json, en.json
│   ├── styles/main.css         # @import "tailwindcss"; theme tokens
│   └── types/
└── tests/ (unit, e2e)
```

---

## 4. Routing

| Route | View | Notes |
|---|---|---|
| `/login` | LoginView | Public |
| `/` | HomeView | Empty state / recent pages |
| `/p/:id` | PageView | Opens a page; sidebar auto-expands ancestors |
| `/f/:id` | FolderView (optional) | Folder overview |
| `/search?q=&scope=` | SearchView | Shareable search URL |
| `/trash` | TrashView | Restore / delete permanently |

Guards: redirect to `/login` if unauthenticated; unknown `:id` shows a "Page not found" state.

---

## 5. State Management

### 5.1 `tree` store (central piece)

- Loaded once from `GET /tree` (flat list, no content).
- Stored as `nodesById: Record<id, TreeNode>` + `childrenByParent: Record<parentId|'root', id[]>` for O(1) lookups.
- **Getters:** `visibleRows` (flattened list of nodes respecting `expanded`), `breadcrumb(id)`, `isDescendant(a, b)`, `descendantsCount(id)`.
- **Actions:** `create`, `rename`, `remove`, `move`, `toggle`, `expandTo(id)`.
- `expanded` state persisted in `localStorage`.
- Sorting rule: folders first, then pages, then `position`.

### 5.2 `page` store

- Holds the open page (`props`, `content`, `version`), `saveStatus` (`idle | saving | saved | error | conflict`).
- Content is managed by TipTap; the store only keeps the last saved JSON and version.

### 5.3 Server-state rules (TanStack Query)

- `['tree']`, `['node', id]`, `['search', params]`, `['trash']`, `['templates']`.
- **Optimistic updates** for rename, move, delete (with rollback on error).
- Search queries are cached for 30 s.

---

## 6. Core Features: Design

### 6.1 Tree view

**Rendering**
- Recursive component `TreeNode` (or a flat `visibleRows` list with indentation — preferred for performance and keyboard navigation).
- Row: chevron (folders), icon (📁 / template icon), name, hover actions (**+**, rename, export, delete).
- **+** on a folder opens a menu: *New page* / *New folder* → template picker for pages → page is created **in that folder** and opened with the title focused.
- Sub-pages are shown under their parent page with extra indentation.

**Accessibility**
- `role="tree"`, `role="treeitem"`, `aria-expanded`, `aria-level`, roving `tabindex`.
- Keyboard: ↑ ↓ move, → expand / go to child, ← collapse / go to parent, Enter open, **F2** rename, **Delete** delete, **Ctrl+M** "Move to…", `+` new item.

**Context menu** (right-click / long-press): New page, New folder, Rename, Move to…, Export, Delete.

### 6.2 Drag and drop (tree)

Implemented in the `useTreeDnd` composable, on top of **native HTML5 DnD** for desktop and **Pointer Events** (long-press ≈ 400 ms) for touch. (If custom code proves heavy, evaluate `dnd-kit`-style libraries for Vue; the zone logic stays the same.)

**Drop zones per row** (computed from the pointer's Y inside the row):

| Zone | Pointer position | Effect |
|---|---|---|
| Before | top 25 % | Insert before this node (same parent) |
| Inside | middle 50 % | Drop **into** this node (if it is a folder; if it is a page → sub-page, per Q3) |
| After | bottom 25 % | Insert after this node (same parent) |

**Behaviour**
- Dragged row becomes semi-transparent; a **drop indicator** (thin line with indent) shows before/after; the target row gets a highlight for "inside".
- **Validation (mirrors the server):** reject drop into itself or a descendant, a folder into a page, or beyond max depth → "forbidden" cursor, no highlight.
- **Auto-expand** a collapsed folder after 700 ms hover.
- **Auto-scroll** the sidebar near top/bottom edges.
- **Root drop zone:** the tree header / empty area moves an item to the root.
- **Optimistic move:** update the store immediately, call `POST /nodes/{id}/move` with `{ parent_id, before_id | after_id }`; on error roll back and show a toast.
- **Undo toast:** "Page moved to *HR* — Undo" (8 s), which calls `move` back to the previous parent/position.
- Drag and drop is **disabled in search-results mode**.
- **Keyboard / mobile alternative:** `MoveToDialog` (a searchable folder tree picker) offering the same result.
- The currently open page stays open; breadcrumb updates after the move.

### 6.3 Page editor (TipTap)

**Extensions**

| Need | Implementation |
|---|---|
| Text, Heading 1-2, bullet & ordered lists | `StarterKit` (headings limited to levels 1-2) |
| Bold, italic, links | Built-in marks + `Link` (safe schemes only) |
| Markdown shortcuts (`#`, `##`, `-`, `1.`) | Built-in input rules |
| Slash menu (`/`) | `@tiptap/suggestion` → `SlashMenu.vue` (Text, Title 1, Title 2, Bullet list, Numbered list, Page) |
| Block handle (`+`, `⋮⋮`, drag to reorder) | TipTap `DragHandle` extension + `BlockMenu.vue` (convert, move up/down, delete) |
| Paste images (Ctrl+V) | `handlePaste` / `handleDrop`: upload to `POST /assets`, insert a placeholder, then the final `Image` node with `/api/v1/assets/{id}` |
| Paste text | Plain-text by default; multi-line paste becomes several blocks |
| **Sub-page block** | Custom node **`pageLink`** (atom, block): attrs `{ pageId }`; node view shows a card (icon + title) and navigates on click |
| Placeholder | `Placeholder` extension ("Type '/' for blocks…") |
| Undo/redo | `History` (Ctrl+Z / Ctrl+Y) |
| Search highlight | Decoration plugin driven by `?q=` |

**Inserting a sub-page** (`/Page` or "+ → Page"): open the template picker → `POST /nodes` with `parent_id = current page` → insert `pageLink` → add the child to the tree under the page.

**Content contract:** the editor emits **ProseMirror JSON**, exactly the node/mark whitelist enforced by the backend (see `backend.md` §4.3). A shared set of sample documents is used in contract tests on both sides.

### 6.4 Template properties

- `PropertiesPanel.vue` renders fields from the template's `props_schema` (text, select now; date, tags, checkbox later).
- Layout: two-column rows (label | value), inline editing, same autosave pipeline.
- `TemplatePicker.vue`: cards (icon, name, description) shown in a dialog when creating a page; the title input is optional.
- Badge above the title shows the template (e.g. *🛠️ Procedure*).

### 6.5 Autosave

`useAutosave`:
1. Editor/props change → mark `dirty`.
2. **Debounce 800 ms**, then `PATCH /nodes/{id}` with `If-Match: version`.
3. On success: update `version`, status "Saved".
4. Flush immediately on blur, route change and `beforeunload` (use `fetch` with `keepalive`).
5. **409 conflict:** dialog "This page was changed elsewhere": *Reload* / *Overwrite* / *Copy my text*.
6. Network error: keep the local draft in memory, retry with backoff, show "Offline — will retry".
7. Header shows `SaveStatus` ("Saving…", "Saved", "Error").

### 6.6 Search

- `SearchBar` in the sidebar: input + scope select (*Title + content*, *Title only*, *Content only*) + optional "in this folder" toggle.
- Debounce 200 ms, minimum 2 characters; requests cancelled when superseded.
- Results replace the tree: icon, title (highlighted), path (Folder › Subfolder), snippet with highlights built from `matches` offsets (rendered with text nodes/`<mark>`, **never `v-html` on raw text**).
- Click opens the page at `/p/:id?q=term` and highlights matches in the editor.
- Shortcut: **Ctrl+K** (or `/` outside the editor) focuses the search field.
- Later: filters by template and status.

### 6.7 Export

- `ExportDialog`: format (Markdown / HTML / Text), images (embed / separate files), and for folders "ZIP (keep tree)".
- Calls `GET /export/{id}` with the auth header, receives a `Blob`, triggers a download (`useDownload`).
- Entry points: page top bar, tree row action, context menu.
- Real file download replaces the prototype's "Copy" workflow; a **Copy to clipboard** button remains as a convenience.

### 6.8 Trash, auth, settings

- **Trash view:** list of deleted items with *Restore* and *Delete permanently*; deletion confirmation shows the number of affected items (from `/nodes/{id}/stats`).
- **Auth:** login form; access token in memory, refresh via `HttpOnly` cookie; automatic refresh on 401; redirect on failure.
- **Settings:** theme (light/dark/system), language.

---

## 7. UI and Design System (Tailwind)

### 7.1 Layout

- **AppShell:** resizable sidebar (min 240 px, max 420 px, width remembered) + main area.
- **Mobile (< 768 px):** sidebar becomes an off-canvas drawer (hamburger in the top bar); tree actions available through the context menu / long-press.
- Page content column: `max-w-3xl`, generous padding; editor typography via `prose`.

### 7.2 Tokens and theming

- Tailwind v4 theme variables (`@theme`) for colors: `--color-surface`, `--color-surface-alt`, `--color-text`, `--color-muted`, `--color-line`, `--color-accent`, `--color-danger`.
- Dark mode: `dark:` variant driven by the `class` strategy (toggle + system default).
- Accent: calm green (as in the prototype); contrast checked for WCAG AA in both themes.
- Spacing and radius scale: 4 px base, `rounded-lg` for cards/inputs.

### 7.3 Reusable components (Tailwind + Headless UI)

`Button` (primary/secondary/ghost/danger), `IconButton`, `Input`, `Select`, `Dialog`, `Menu`, `Combobox`, `Toast`, `Badge`, `Tooltip`, `Skeleton`.

### 7.4 Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `/` (in editor) | Insert block menu |
| `Ctrl+B` / `Ctrl+I` / `Ctrl+K` (in editor: link) | Format |
| `Ctrl+K` (outside editor) / `/` | Focus search |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `F2` | Rename (tree) |
| `Delete` | Delete (tree, with confirmation) |
| `Ctrl+M` | Move to… |
| `Esc` | Close menu / dialog |

> `Ctrl+K` is used for links inside the editor and for search outside it; this is a point to confirm.

---

## 8. Performance

- Route-level code splitting; **lazy-load TipTap** (only when a page opens).
- `GET /tree` is metadata only; page content fetched on open (prefetch on hover).
- Flat `visibleRows` + `v-memo`/`key` stability; add **virtual scrolling** (`vue-virtual-scroller`) if the visible tree exceeds ~1 000 rows.
- Debounced search, cancelled requests, cached results.
- Images: `loading="lazy"`, width/height attributes from asset metadata to avoid layout shift.
- Target: initial load < 2 s on a standard connection; page switch < 300 ms (cached).

---

## 9. Accessibility and i18n

- WCAG 2.1 AA: focus rings, labels on icon buttons, ARIA tree pattern, `aria-live` announcements for moves ("Page moved to HR") and saves.
- Every drag-and-drop action has a keyboard equivalent (`Move to…`).
- Respect `prefers-reduced-motion`.
- All strings in `vue-i18n` files (French default); dates formatted with `Intl`.

---

## 10. Testing Strategy

| Level | Tooling | Focus |
|---|---|---|
| Unit | Vitest | Tree utils (`isDescendant`, positions), DnD zone calculation, search highlight, store actions |
| Component | Vue Test Utils | TreeNode states, PropertiesPanel from schema, SlashMenu, dialogs |
| API mocks | MSW | Optimistic update + rollback, 409 conflict, 401 refresh |
| E2E | Playwright | Create folder → sub-folder → page; **drag page into folder**; forbidden drop; reorder persists after reload; paste image; template properties; search scopes; export download; trash restore |
| Accessibility | axe-core in Playwright | No critical violations on main screens |
| Visual (optional) | Playwright screenshots | Light/dark layouts |

Acceptance scenarios CA-1 to CA-9 from the specification are automated as E2E tests.

---

## 11. Build, Config and Delivery

- Env: `VITE_API_BASE_URL` (defaults to `/api/v1`); dev proxy to Flask in `vite.config.ts`.
- `pnpm build` → static assets served by Nginx (SPA fallback to `index.html`).
- Types generated with `openapi-typescript` from `/api/v1/openapi.json` in a `pnpm gen:api` script (CI fails if the generated file is stale).
- CI: lint → type-check → unit → build → E2E (against a Compose stack).

---

## 12. Implementation Plan

| Phase | Tasks | Deliverable |
|---|---|---|
| **F0 — Setup** (2 days) | Vite + Vue + TS, Tailwind v4, ESLint/Prettier, Pinia, Router, i18n, API client + type generation, CI | App skeleton |
| **F1 — Shell & auth** (3 days) | AppShell, sidebar layout, theme toggle, login, token refresh, toasts, dialogs | Authenticated shell |
| **F2 — Tree** (5-6 days) | Tree store, TreeView/TreeNode, expand state, create page/folder in a folder, rename, delete (with count), context menu, breadcrumb, keyboard navigation | Fully usable tree |
| **F3 — Drag and drop** (4-5 days) | `useTreeDnd`, zones, indicators, validation, auto-expand/scroll, optimistic move + undo toast, `MoveToDialog`, touch support | Drag & drop complete |
| **F4 — Page & editor** (6-8 days) | PageView, TipTap setup, slash menu, block handle/menu, Markdown shortcuts, links, `pageLink` node, template picker, properties panel, autosave + conflict dialog | Editing experience |
| **F5 — Images** (2-3 days) | Paste/drop upload, placeholders, error states, lazy display | Image support |
| **F6 — Search** (3 days) | SearchBar, scopes, results list, in-page highlight, Ctrl+K | Search UI |
| **F7 — Export & trash** (3 days) | ExportDialog, downloads (single file, ZIP), trash view | Export + restore |
| **F8 — Polish & QA** (4-5 days) | Accessibility pass, mobile layout, performance, E2E suite, empty states, i18n review | Release candidate |

Rough total: **32-38 working days** for one developer. F2-F3 can start as soon as backend phase B2 is available (or earlier with MSW mocks).

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Custom drag & drop is fiddly (zones, touch, auto-scroll) | Isolate in `useTreeDnd`, unit-test the zone maths, always provide `Move to…` |
| TipTap custom node/slash menu complexity | Build `pageLink` and slash menu early (F4), use official examples as base |
| Editor content drifts from the backend whitelist | Shared sample documents + contract tests; reject unknown nodes on the client too |
| Autosave conflicts / data loss | Optimistic locking, flush on leave, clear conflict dialog, in-memory retry |
| Large trees slow down rendering | Flat visible-rows model, virtual scroll option |
| `Ctrl+K` shortcut collision (search vs link) | Decide a single mapping (e.g. link = `Ctrl+Shift+K` or keep as proposed) |

---

## 14. Open Points (frontend side)

1. Confirm Q3: dropping a page **on a page** creates a sub-page (proposed) or only reorders.
2. Keyboard mapping for search vs link (`Ctrl+K`).
3. Do we need a folder overview page (`/f/:id`) in V1?
4. UI language: French only, or French + English from the start?
5. Branding (logo, accent colour) to replace the prototype's neutral green.
