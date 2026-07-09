---
name: tailwind-css
description: Tailwind CSS v4 conventions and patterns for utility-first styling with the project design system
---

# Tailwind CSS Skill

## Design System Tokens

This project uses Tailwind CSS with a custom design system defined in `tailwind.config.ts`.

## Naming Conventions

- Use Tailwind utility classes directly in JSX — no custom CSS unless required
- Extract repeated utility patterns into reusable components (not CSS classes)
- Use `@apply` only in component libraries, never in app code

## Layout Patterns

```tsx
// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

// Flexbox centering
<div className="flex items-center justify-between">

// Stack layout
<div className="flex flex-col space-y-4">
```

## Responsive Design

- Mobile-first: base styles = mobile, `sm:` = tablet, `md:` = desktop, `lg:` = wide
- Use `container` for max-width containment
- Use `prose` for rich text content

## States & Variants

```tsx
// Hover, focus, active, disabled
<button className="hover:bg-primary-600 focus:ring-2 active:scale-95 disabled:opacity-50">

// Dark mode
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">

// Group hover
<div className="group">
  <p className="group-hover:text-primary-500">
```

## Animations

- Use `transition-{property}` and `duration-{n}` for transitions
- Use `animate-{name}` for keyframe animations defined in config
- Prefer CSS transitions over JS animation libraries for simple cases
