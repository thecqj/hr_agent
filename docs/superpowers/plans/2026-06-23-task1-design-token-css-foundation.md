# Task 1: Design Token & CSS Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default shadcn neutral theme tokens with a blue-primary, slate-neutral professional recruitment design system.

**Architecture:** Single-file change to `index.css` — update all CSS custom properties in `:root` and `.dark` to establish the new design token foundation. All existing shadcn components and pages continue to work through the same token names; only the values change.

**Tech Stack:** Tailwind CSS v4, oklch color space, shadcn/ui theme tokens

## Global Constraints

- Brand primary: blue-600 = `oklch(54.6% 0.245 262.881)`
- Neutral palette: slate (cool-tinted, harmonizes with blue primary)
- All token values use oklch color space for consistency
- Dark mode tokens must be maintained (`.dark` class variant)
- No page/component code changes in this task — tokens only
- Spec: `docs/superpowers/specs/2026-06-23-frontend-ui-redesign-design.md`

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/index.css` | Modify | All design token definitions |

---

### Task 1: Update Light Mode Design Tokens

**Files:**
- Modify: `frontend/src/index.css:58-91` (the `:root` block)

**Interfaces:**
- Consumes: None (foundation task)
- Produces: All CSS custom properties (`--primary`, `--background`, etc.) that shadcn components and pages consume via Tailwind utility classes

This task replaces all `:root` CSS custom properties with the new blue-primary, slate-neutral token system.

- [ ] **Step 1: Update primary tokens to blue-600**

Replace the `:root` block (lines 58-91) with the following. The key changes: `--primary` becomes blue-600, `--primary-foreground` becomes white, `--ring` becomes primary, and all neutral values shift from pure gray (chroma=0) to slate (slight blue chroma).

```css
:root {
  --background: oklch(98.4% 0.003 247.858);
  --foreground: oklch(20.8% 0.042 265.755);
  --card: oklch(1 0 0);
  --card-foreground: oklch(20.8% 0.042 265.755);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(20.8% 0.042 265.755);
  --primary: oklch(54.6% 0.245 262.881);
  --primary-foreground: oklch(1 0 0);
  --secondary: oklch(96.8% 0.007 247.896);
  --secondary-foreground: oklch(37.2% 0.044 257.287);
  --muted: oklch(96.8% 0.007 247.896);
  --muted-foreground: oklch(55.4% 0.046 257.417);
  --accent: oklch(93.2% 0.032 255.585);
  --accent-foreground: oklch(37.2% 0.044 257.287);
  --destructive: oklch(57.7% 0.245 27.325);
  --border: oklch(92.9% 0.013 255.508);
  --input: oklch(92.9% 0.013 255.508);
  --ring: oklch(54.6% 0.245 262.881);
  --chart-1: oklch(54.6% 0.245 262.881);
  --chart-2: oklch(62.7% 0.194 149.214);
  --chart-3: oklch(66.6% 0.179 58.318);
  --chart-4: oklch(70.4% 0.191 22.216);
  --chart-5: oklch(44.6% 0.043 257.281);
  --radius: 0.625rem;
  --sidebar: oklch(1 0 0);
  --sidebar-foreground: oklch(20.8% 0.042 265.755);
  --sidebar-primary: oklch(54.6% 0.245 262.881);
  --sidebar-primary-foreground: oklch(1 0 0);
  --sidebar-accent: oklch(97% 0.014 254.604);
  --sidebar-accent-foreground: oklch(37.2% 0.044 257.287);
  --sidebar-border: oklch(92.9% 0.013 255.508);
  --sidebar-ring: oklch(54.6% 0.245 262.881);
}
```

Token mapping rationale:
| Token | Source | Why |
|-------|--------|-----|
| `--background` | slate-50 | Page background, slight cool tint vs pure white |
| `--foreground` | slate-900 | Primary text, cool dark |
| `--card` | pure white | Cards pop against the cool page bg |
| `--primary` | blue-600 | Brand blue, the core identity |
| `--primary-foreground` | white | Text on blue buttons/badges |
| `--secondary` | slate-100 | Subtle backgrounds for tags, secondary actions |
| `--muted` | slate-100 | Muted backgrounds match secondary |
| `--muted-foreground` | slate-500 | Placeholder/secondary text |
| `--accent` | blue-100 | Accent backgrounds, lighter than primary |
| `--accent-foreground` | slate-700 | Text on accent backgrounds |
| `--destructive` | red-600 | Error/rejection red |
| `--border` | slate-200 | Borders and dividers |
| `--ring` | blue-600 | Focus rings match primary brand |
| `--sidebar-primary` | blue-600 | Sidebar uses brand primary |
| `--sidebar-accent` | blue-50 | Sidebar active item background (very light blue) |
| Charts | mixed | blue + green + amber + red + slate for chart series |

- [ ] **Step 2: Verify dev server starts without errors**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npx vite build 2>&1 | tail -5`
Expected: Build succeeds with no CSS errors

- [ ] **Step 3: Commit light mode tokens**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): update light mode design tokens to blue-primary slate-neutral"
```

---

### Task 2: Update Dark Mode Design Tokens

**Files:**
- Modify: `frontend/src/index.css` (the `.dark` block)

**Interfaces:**
- Consumes: Light mode token structure from Task 1
- Produces: Dark mode variants of all tokens

- [ ] **Step 1: Replace the `.dark` block with blue-primary dark variants**

Replace the `.dark` block with:

```css
.dark {
  --background: oklch(12.9% 0.042 264.695);
  --foreground: oklch(96.8% 0.007 247.896);
  --card: oklch(20.8% 0.042 265.755);
  --card-foreground: oklch(96.8% 0.007 247.896);
  --popover: oklch(20.8% 0.042 265.755);
  --popover-foreground: oklch(96.8% 0.007 247.896);
  --primary: oklch(70.7% 0.165 254.624);
  --primary-foreground: oklch(20.8% 0.042 265.755);
  --secondary: oklch(27.9% 0.041 260.031);
  --secondary-foreground: oklch(96.8% 0.007 247.896);
  --muted: oklch(27.9% 0.041 260.031);
  --muted-foreground: oklch(70.4% 0.04 256.788);
  --accent: oklch(27.9% 0.041 260.031);
  --accent-foreground: oklch(96.8% 0.007 247.896);
  --destructive: oklch(70.4% 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(70.7% 0.165 254.624);
  --chart-1: oklch(70.7% 0.165 254.624);
  --chart-2: oklch(79.2% 0.209 151.711);
  --chart-3: oklch(82.8% 0.189 84.429);
  --chart-4: oklch(70.4% 0.191 22.216);
  --chart-5: oklch(70.4% 0.04 256.788);
  --sidebar: oklch(20.8% 0.042 265.755);
  --sidebar-foreground: oklch(96.8% 0.007 247.896);
  --sidebar-primary: oklch(70.7% 0.165 254.624);
  --sidebar-primary-foreground: oklch(20.8% 0.042 265.755);
  --sidebar-accent: oklch(27.9% 0.041 260.031);
  --sidebar-accent-foreground: oklch(96.8% 0.007 247.896);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(70.7% 0.165 254.624);
}
```

Dark mode token mapping:
| Token | Source | Why |
|-------|--------|-----|
| `--background` | slate-950 | Darkest background |
| `--foreground` | slate-100 | Light text |
| `--primary` | blue-400 | Lighter blue for dark bg contrast |
| `--primary-foreground` | slate-900 | Dark text on blue |
| `--muted-foreground` | slate-400 | Softer secondary text |
| `--ring` | blue-400 | Focus ring matches lightened primary |

- [ ] **Step 2: Verify build still passes**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npx vite build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit dark mode tokens**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): update dark mode design tokens to blue-primary slate-neutral"
```

---

### Task 3: Update Body Styles and Base Layer

**Files:**
- Modify: `frontend/src/index.css:8-13` (body block) and `127-137` (@layer base block)

**Interfaces:**
- Consumes: Token values from Tasks 1-2
- Produces: Correct body rendering via design tokens instead of hardcoded hex colors

- [ ] **Step 1: Replace hardcoded body colors with token references**

Replace the `body` block (lines 8-13):

```css
body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

Remove the hardcoded `background-color: #f9fafb` and `color: #111827` — these are now handled by the `@layer base` block which applies `bg-background text-foreground` via Tailwind classes.

- [ ] **Step 2: Verify the full index.css file is correct**

The complete file should read as:

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";
@import "@fontsource-variable/geist";

@custom-variant dark (&:is(.dark *));

body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

@theme inline {
  --font-heading: var(--font-sans);
  --font-sans: 'Geist Variable', sans-serif;
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --color-foreground: var(--foreground);
  --color-background: var(--background);
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
  --radius-2xl: calc(var(--radius) * 1.8);
  --radius-3xl: calc(var(--radius) * 2.2);
  --radius-4xl: calc(var(--radius) * 2.6);
}

:root {
  --background: oklch(98.4% 0.003 247.858);
  --foreground: oklch(20.8% 0.042 265.755);
  --card: oklch(1 0 0);
  --card-foreground: oklch(20.8% 0.042 265.755);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(20.8% 0.042 265.755);
  --primary: oklch(54.6% 0.245 262.881);
  --primary-foreground: oklch(1 0 0);
  --secondary: oklch(96.8% 0.007 247.896);
  --secondary-foreground: oklch(37.2% 0.044 257.287);
  --muted: oklch(96.8% 0.007 247.896);
  --muted-foreground: oklch(55.4% 0.046 257.417);
  --accent: oklch(93.2% 0.032 255.585);
  --accent-foreground: oklch(37.2% 0.044 257.287);
  --destructive: oklch(57.7% 0.245 27.325);
  --border: oklch(92.9% 0.013 255.508);
  --input: oklch(92.9% 0.013 255.508);
  --ring: oklch(54.6% 0.245 262.881);
  --chart-1: oklch(54.6% 0.245 262.881);
  --chart-2: oklch(62.7% 0.194 149.214);
  --chart-3: oklch(66.6% 0.179 58.318);
  --chart-4: oklch(70.4% 0.191 22.216);
  --chart-5: oklch(44.6% 0.043 257.281);
  --radius: 0.625rem;
  --sidebar: oklch(1 0 0);
  --sidebar-foreground: oklch(20.8% 0.042 265.755);
  --sidebar-primary: oklch(54.6% 0.245 262.881);
  --sidebar-primary-foreground: oklch(1 0 0);
  --sidebar-accent: oklch(97% 0.014 254.604);
  --sidebar-accent-foreground: oklch(37.2% 0.044 257.287);
  --sidebar-border: oklch(92.9% 0.013 255.508);
  --sidebar-ring: oklch(54.6% 0.245 262.881);
}

.dark {
  --background: oklch(12.9% 0.042 264.695);
  --foreground: oklch(96.8% 0.007 247.896);
  --card: oklch(20.8% 0.042 265.755);
  --card-foreground: oklch(96.8% 0.007 247.896);
  --popover: oklch(20.8% 0.042 265.755);
  --popover-foreground: oklch(96.8% 0.007 247.896);
  --primary: oklch(70.7% 0.165 254.624);
  --primary-foreground: oklch(20.8% 0.042 265.755);
  --secondary: oklch(27.9% 0.041 260.031);
  --secondary-foreground: oklch(96.8% 0.007 247.896);
  --muted: oklch(27.9% 0.041 260.031);
  --muted-foreground: oklch(70.4% 0.04 256.788);
  --accent: oklch(27.9% 0.041 260.031);
  --accent-foreground: oklch(96.8% 0.007 247.896);
  --destructive: oklch(70.4% 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(70.7% 0.165 254.624);
  --chart-1: oklch(70.7% 0.165 254.624);
  --chart-2: oklch(79.2% 0.209 151.711);
  --chart-3: oklch(82.8% 0.189 84.429);
  --chart-4: oklch(70.4% 0.191 22.216);
  --chart-5: oklch(70.4% 0.04 256.788);
  --sidebar: oklch(20.8% 0.042 265.755);
  --sidebar-foreground: oklch(96.8% 0.007 247.896);
  --sidebar-primary: oklch(70.7% 0.165 254.624);
  --sidebar-primary-foreground: oklch(20.8% 0.042 265.755);
  --sidebar-accent: oklch(27.9% 0.041 260.031);
  --sidebar-accent-foreground: oklch(96.8% 0.007 247.896);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(70.7% 0.165 254.624);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
  html {
    @apply font-sans;
  }
}
```

- [ ] **Step 3: Build and verify**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npx vite build 2>&1 | tail -10`
Expected: Build succeeds with no errors

- [ ] **Step 4: Visual smoke test — start dev server and check**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npx vite --host 2>&1 &`

Open the browser and verify:
- Buttons that use `bg-primary` are now blue instead of near-black
- Text that uses `text-primary` is now blue
- Page background is slightly cool-tinted (not pure gray)
- Card backgrounds are still white
- Border and input border colors have a subtle cool tint
- The overall feel is "professional blue" not "plain gray"

- [ ] **Step 5: Commit body style cleanup**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): remove hardcoded body colors, use design tokens"
```

---

## Self-Review

**1. Spec coverage:** The spec requires:
- ✅ Blue-600 primary color → `--primary: oklch(54.6% 0.245 262.881)` (blue-600)
- ✅ Slate-tinted neutral palette → all neutral tokens use slate oklch values with slight chroma
- ✅ Semantic colors (success/warning/destructive) → chart tokens map to green/amber/red; `--destructive` uses red-600
- ✅ Typography → Geist Variable retained, no changes needed (type scale is applied via Tailwind classes in page components, not tokens)
- ✅ Spacing & radius → `--radius: 0.625rem` retained (matches spec)
- ✅ Shadows → handled via Tailwind utility classes in components, not tokens
- ✅ Sidebar tokens → configured for white sidebar with blue-50 accent (RecruiterLayout prep)

**2. Placeholder scan:** No TBD/TODO/vague references found. All token values are explicit oklch values.

**3. Type consistency:** Single-file CSS change. No type dependencies between tasks. Token names match what shadcn components consume (e.g., `--primary` → `text-primary`, `bg-primary`).
