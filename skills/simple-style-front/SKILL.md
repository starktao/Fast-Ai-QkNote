---
name: simple-style-front
description: Apply the warm notebook-style frontend theme (radial + linear cream background, soft white cards, muted green accent, Spectral + Space Grotesk typography). Use when recreating or matching this exact UI look in any frontend stack (Vue/React/HTML) or when a user asks to ?use the same simple style front? or ?match the current UI style.?
---

# Simple Style Front

## Overview

Recreate the exact warm notebook UI used in this project: cream gradient backdrop, soft card surfaces, muted green accents, and serif headline typography.

## Core Style Recipe

- **Typography**: Load Google Fonts `Spectral` (headlines) and `Space Grotesk` (body). Keep H1 in Spectral, everything else in Space Grotesk.
- **Palette**: Use the CSS variables from `assets/style.css` without modifications.
- **Background**: Keep the dual-layer background (radial highlight + vertical gradient).
- **Cards**: White cards with 16px radius, thin border, subtle shadow.
- **Controls**: Rounded inputs/buttons (10px radius), thin border, solid accent button.
- **Layout**: Page max width 1100px, 32px top padding, 56px bottom padding.

## Apply the Style

1) Copy `assets/style.css` into your global stylesheet (or import it into your app root).
2) Use the class names from `assets/template.html` (`page`, `section-title`, `grid`, `sessions`, `session-item`, `badge`, etc.).
3) Keep the header structure: `header > h1 + p` for the serif headline and muted subtitle.
4) Preserve the responsive breakpoint at 900px for the two-column session layout.

## Assets

- `assets/style.css` (authoritative theme)
- `assets/template.html` (reference structure; adapt to any framework)