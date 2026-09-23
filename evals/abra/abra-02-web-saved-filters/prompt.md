---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
model: sonnet
runs: 5
---
Design the verification scenarios for the change described below with a sub-agent. Do not design them yourself and do not look for the repository; the brief is the only input. Return the sub-agent's checklist verbatim and nothing else. Each scenario must use exactly this shape:

```text
V1 · surface: web · mutating: no · criterion: <which>
  pre: <preconditions, or none>
  steps: <numbered, concrete>
  expect: <observable result>
```

---

Surfaces in play: web (React app). Environment: shared staging at https://staging.orders.example — other testers use it, so mutating scenarios are discouraged and must clean up after themselves. A test account `qa-filters@example.com` exists with 24 orders (8 status=shipped, 16 status=pending).

## Acceptance criteria
- [ ] AC1 — On `/orders`, choosing status=shipped and clicking "Save filter", then entering the name "Shipped only", shows a "Shipped only" entry in the left sidebar under "Saved filters".
- [ ] AC2 — Clicking a saved filter in the sidebar narrows the orders table to matching rows and the table header shows "8 orders".
- [ ] AC3 — Hovering a saved filter and clicking its trash icon removes it from the sidebar; the table returns to the unfiltered "24 orders" state.
- [ ] AC4 — With no saved filters, the sidebar section shows the text "No saved filters yet".

## Change map
| Area | File(s) | New / Modify | Responsibility |
| --- | --- | --- | --- |
| UI | `src/pages/Orders.tsx` | Modify | filter bar, "Save filter" button |
| UI | `src/components/SavedFilters.tsx` | New | sidebar list, delete icon, empty state |
| API client | `src/api/filters.ts` | New | `listFilters`, `createFilter`, `deleteFilter` |

## Testing notes
- Component tests cover the empty state and the delete confirmation. No end-to-end coverage exists yet.
