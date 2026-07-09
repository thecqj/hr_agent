---
name: react
description: React 19 best practices, patterns, and conventions for building components, hooks, and performance optimization
---

# React 19 Skill

## Core Principles

- **Components**: Functional components only, no class components
- **Hooks**: Use built-in hooks (useState, useEffect, useCallback, useMemo, useRef, useContext) following rules of hooks
- **Server Components** (Next.js): Default to server components, add 'use client' only when needed (event handlers, hooks, browser APIs)
- **Composition**: Prefer composition over inheritance; extract reusable logic into custom hooks

## Component Patterns

### Component Structure
```tsx
// imports
// types/interfaces
// component function
// styles (CSS modules / Tailwind)
// exports
```

### Props Pattern
```tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  disabled?: boolean;
  onClick?: () => void;
}
```

### Custom Hook Pattern
```tsx
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}
```

## Performance

- Use `React.memo` for pure components that render often with same props
- Use `useMemo` for expensive computations
- Use `useCallback` for stable function references passed to child components
- Use `useTransition` for non-urgent state updates
- Use `Suspense` with `React.lazy` for code splitting

## React 19 Specifics

- **use() Hook**: Read promises and context directly in render
- **Actions**: Use `useActionState` for form actions
- **Server Actions**: Use `'use server'` for server-side mutations
- **Ref as prop**: Refs can be passed as props directly (no forwardRef needed)
- **Improved hooks**: useOptimistic for optimistic updates
