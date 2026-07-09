---
name: typescript
description: TypeScript strict mode conventions, type patterns, and best practices for production code
---

# TypeScript Skill

## Strict Mode

This project uses `strict: true` in tsconfig. All code must pass without `any` escapes.

## Type Patterns

### Prefer type over interface for unions/utility types
```ts
// Prefer
type Status = 'idle' | 'loading' | 'success' | 'error';
type ApiResponse<T> = { data: T; error: null } | { data: null; error: string };

// interface for object shapes that may be extended
interface User {
  id: string;
  name: string;
  email: string;
}
```

### Discriminated Unions
```ts
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };
```

### Generic Constraints
```ts
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
```

### Branded Types
```ts
type Brand<T, B> = T & { __brand: B };
type UserId = Brand<string, 'UserId'>;
```

## Patterns

- Use `satisfies` operator for type validation without widening
- Use `as const` for literal types and readonly tuples
- Use `Record<K, V>` for dictionary objects
- Use `Partial<T>`, `Required<T>`, `Pick<T, K>`, `Omit<T, K>` for type transformations
- Use `z.infer<typeof schema>` for Zod-derived types
- Avoid type assertions (`as`) — use type guards instead

## Type Guards
```ts
function isError(value: unknown): value is Error {
  return value instanceof Error;
}
```
