---
name: qknote-frontend-style
description: Visual language, component styles, and motion rules to replicate the QkNote light UI look and feel. Use when restyling frontends to match QkNote visuals (colors, typography, cards, buttons, dropdowns, toggles, status pills), without prescribing any layout skeleton or project-specific flows.
---

# QkNote Frontend Style

## Scope
- Provide a consistent visual language (colors, typography, surfaces, shadows).
- Provide component styling and motion rules (buttons, dropdowns, toggles, status pills, prose/markdown).
- Avoid layout skeletons and project-specific flows.

## Do not include
- Page layout grids or column structures.
- Project-specific sections (config/session/note flows).
- Backend logic or data workflows.

## Assets
- `assets/style.css`: tokens, components, and motion.
- `assets/template.html`: minimal demo of components (no layout skeleton).

## Quick apply
1. Copy the tokens and base styles from `assets/style.css`.
2. Use the component classes as needed:
   - Cards and surfaces: `.qk-card`, `.qk-section-title`, `.qk-status`
   - Inputs: `.qk-input`, `.qk-select`, `.qk-textarea`
   - Buttons: `.qk-button` (primary), `.qk-ghost` (secondary)
   - Dropdown: `.qk-dropdown`, `.qk-dropdown-trigger`, `.qk-dropdown-menu`, `.qk-dropdown-option`
   - Toggle group: `.qk-toggle-group`, `.qk-toggle-btn`
   - Status pill (with waiting ring): `.qk-pill` + `is-pending|is-running|is-completed|is-failed`
   - Prose/markdown: `.qk-prose`

## Motion rules
- Dropdown enter/leave: 0.18s ease, translateY(-6px) to 0.
- Fade-slide content: 0.25s ease, translateY(6px) to 0.
- Prefer short, soft easing. Disable motion when `prefers-reduced-motion` is set.

## Waiting ring behavior
- Use `.qk-pill.is-running` to show a red-to-green ring that fills over time.
- When complete, switch to `.is-completed` (solid green border).
- When failed, switch to `.is-failed` (red border).

## Example usage
Open `assets/template.html` to see a minimal example that uses these classes.
