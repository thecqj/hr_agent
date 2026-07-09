---
name: zod
description: Zod v3 schema validation patterns, type inference, and integration patterns
---

# Zod Skill

## Core Patterns

### Schema Definition
```ts
import { z } from 'zod';

// Primitive schemas
const StringSchema = z.string();
const NumberSchema = z.number().positive();
const BooleanSchema = z.boolean();

// Object schemas
const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  email: z.string().email(),
  age: z.number().int().min(0).optional(),
  role: z.enum(['admin', 'user', 'viewer']),
  tags: z.array(z.string()).default([]),
  metadata: z.record(z.string()).optional(),
});

// Infer types
type User = z.infer<typeof UserSchema>;
```

### Refinements
```ts
const PasswordSchema = z.string()
  .min(8)
  .max(128)
  .refine((val) => /[A-Z]/.test(val), 'Must contain uppercase')
  .refine((val) => /[0-9]/.test(val), 'Must contain number');
```

### Transformations
```ts
const DateStringSchema = z.string().transform((str) => new Date(str));
const TrimmedSchema = z.string().transform((s) => s.trim());
```

## API Response Patterns
```ts
const ApiResponseSchema = <T extends z.ZodTypeAny>(data: T) =>
  z.object({
    success: z.boolean(),
    data: data.optional(),
    error: z.string().optional(),
  });

type ApiResponse<T> = z.infer<ReturnType<typeof ApiResponseSchema<T>>>;
```

## Key Patterns

- Use `z.infer<typeof Schema>` for type inference (never duplicate types)
- Use `z.discriminatedUnion()` for discriminated unions
- Use `.safeParse()` instead of `.parse()` in server code (no throwing)
- Use `.transform()` for data normalization
- Use `.default()` for optional fields with defaults
- Use `.describe()` for documentation/schema generation
- Use `z.literal()` for exact value constraints
- Use `z.discriminatedUnion()` for tagged union types (better error messages)
