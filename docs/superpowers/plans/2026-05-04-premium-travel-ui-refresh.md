# Premium Travel UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the travel chat frontend into a production-style premium travel UI without changing the existing AG-UI behavior or result contracts.

**Architecture:** Keep the current data flow and tool rendering intact, but replace the demo-oriented surface with a shared UI layer, a cleaner app shell, and a modal state viewer. Reuse existing component boundaries where possible so the refactor stays presentation-focused.

**Tech Stack:** React 18, TypeScript, Vite, lucide-react, CSS

---

### Task 1: Lock State Viewer Popup Behavior

**Files:**
- Modify: `frontend/tests/e2e/state-panel-sidebar/state-panel-basic.spec.ts`
- Modify: `frontend/tests/e2e/state-panel-sidebar/state-panel-updates.spec.ts`

- [ ] Update the state-panel E2E expectations from fixed sidebar behavior to popup behavior with an explicit open action.
- [ ] Keep the state-field assertions, but make the tests open the state viewer before reading values.
- [ ] Run targeted Playwright state-panel tests and confirm they fail before UI changes.

### Task 2: Add Shared UI Primitives

**Files:**
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/dialog.tsx`
- Create: `frontend/src/components/ui/textarea.tsx`

- [ ] Add a minimal local UI layer with shadcn-style component APIs for button, card, badge, dialog, and textarea.
- [ ] Keep the implementation CSS-class driven so it fits the repo’s existing non-Tailwind setup.
- [ ] Limit the new layer to primitives used by the refreshed travel UI.

### Task 3: Refresh the App Shell

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] Replace the current demo-style header and empty state with a premium travel service shell.
- [ ] Remove emoji and dev-only copy from the primary surface.
- [ ] Replace the fixed sidebar mount with dialog open/close state while preserving existing send, stop, clear, suggestion, and favorite flows.

### Task 4: Refresh Message and Result Presentation

**Files:**
- Modify: `frontend/src/components/ChatMessageBubble.tsx`
- Modify: `frontend/src/components/ToolCallIndicator.tsx`
- Modify: `frontend/src/components/ToolResultCard.tsx`
- Modify: `frontend/src/components/UserInputForm.tsx`
- Modify: `frontend/src/components/FavoritePanel.tsx`

- [ ] Replace emoji-first message identity and tool indicators with calmer visual treatments.
- [ ] Keep the renderer contract unchanged for `search_hotels`, `search_flights`, `get_travel_tips`, and `get_hotel_detail`.
- [ ] Preserve the existing form submission behavior while upgrading the surface styling and interaction affordances.

### Task 5: Convert StatePanel into Popup Content

**Files:**
- Modify: `frontend/src/components/StatePanel.tsx`

- [ ] Remove the embedded toggle button and sidebar-only shell from `StatePanel`.
- [ ] Keep the existing field groupings and highlight pulse logic.
- [ ] Make the component render cleanly inside a dialog body controlled by `App.tsx`.

### Task 6: Replace Global Styles

**Files:**
- Modify: `frontend/src/index.css`

- [ ] Replace the current demo-oriented CSS with a premium service visual system that still supports the existing component selectors used by tests.
- [ ] Add styles for the new shared primitives and modal state viewer.
- [ ] Keep stable selectors such as `.input-box`, `.send-btn`, `.tool-card`, `.bubble`, and `.sp-field` so existing tests and app hooks continue to work.

### Task 7: Verify Build and Focused E2E

**Files:**
- No file changes required

- [ ] Run `npm run build` in `frontend` and fix any type or build errors.
- [ ] Run focused Playwright coverage for state panel behavior and a representative happy-path chat flow.
- [ ] Record any residual gaps if full E2E coverage is not practical in this turn.
