# Premium Travel UI Refresh Design

## Goal

Refine the existing travel AG-UI frontend so it feels like a production-ready premium travel service rather than a development demo, while preserving current functionality, tool-result behavior, and chat/state flows.

## Scope

- Keep all existing travel assistant behavior intact.
- Remove emoji-driven and demo-like visual treatment from the primary UI.
- Introduce `shadcn/ui`-style primitives for the main layout and interaction surfaces.
- Move developer-oriented state visibility out of the default layout into a popup surface.

## Non-Goals

- No backend contract changes.
- No changes to AG-UI message semantics, tool payloads, or state sync behavior.
- No rewrite of domain-specific result rendering logic beyond presentation and layout cleanup.

## UX Direction

The UI should feel like a premium travel booking assistant:

- restrained and polished rather than playful
- clean spacing and quiet surfaces
- strong visual hierarchy for search, results, and status
- developer-facing details hidden unless explicitly requested

## Architecture

### Layout

- Replace the current demo header and split layout with a single primary chat surface.
- Keep the conversation flow as the main experience.
- Add a lightweight top bar with:
  - product title
  - run/idle status
  - state viewer trigger
  - conversation reset action

### State Viewer

- Remove the current always-visible right sidebar from the default page layout.
- Preserve `StatePanel` data content, but present it in a popup container instead of a fixed side panel.
- Preferred implementation is a dialog-style overlay so the default screen remains focused on the user task.

### Chat Surfaces

- Rework message bubbles, tool-status blocks, and result cards around shared card and badge primitives.
- Keep current rendering order:
  - tool activity
  - tool results
  - user input request forms
  - message text

### Welcome State

- Replace the current empty-state hero with a quieter service-style introduction.
- Keep suggestion shortcuts, but render them as clean cards or secondary buttons rather than demo chips.

### Input Composer

- Upgrade the footer composer to a cleaner service-style input area.
- Replace symbol-based controls with polished icon buttons.
- Remove developer-oriented helper text from the default visible footer.

## Component Plan

### Introduce shared UI primitives

Add a minimal local `shadcn/ui`-style component layer for:

- `Button`
- `Card`
- `Dialog`
- `Badge`
- `Textarea`
- optional `ScrollArea` or thin custom scroll wrapper if needed

These components should be used only where they materially improve consistency and should not force a large refactor.

### App-level updates

Update `frontend/src/App.tsx` to:

- render the premium header
- replace sidebar state-panel mounting with dialog open/close state
- simplify the empty state
- preserve existing send/interrupt/clear/favorite flows

### Message rendering

Update `frontend/src/components/ChatMessageBubble.tsx` to:

- remove emoji avatars
- use calmer assistant/user identity styling
- keep streaming cursor behavior
- preserve existing form submission and snapshot rendering behavior

### Result cards

Update `frontend/src/components/ToolResultCard.tsx` to:

- remove emoji-led headers and placeholder visuals
- use premium travel card styling
- keep hotel click-through behavior
- keep current tool-based branching intact

### State panel popup

Update `frontend/src/components/StatePanel.tsx` to:

- support dialog/modal presentation cleanly
- remove embedded mobile sidebar toggle affordance
- preserve current field groupings and highlight behavior

## Error Handling

- Existing error banners remain functionally identical.
- Styling should be toned down to match the refined UI, but error visibility must remain clear.

## Testing

Validation should cover:

- frontend type-check and build
- existing E2E coverage most likely affected by DOM/layout changes
- manual browser check for:
  - empty state
  - chat flow
  - hotel detail click flow
  - state popup open/close behavior

## Risks

- E2E selectors may depend on current DOM shape or visible text.
- Result-card styling changes must not disturb the `search_hotels` renderer contract.
- State panel refactor must not remove live state visibility needed for debugging.

## Implementation Boundary

This is a presentation-focused refactor. Logic changes should stay narrowly scoped to UI state needed for the popup and shared component usage.
