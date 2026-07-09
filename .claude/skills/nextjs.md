---
name: nextjs
description: Next.js App Router conventions, server components, data fetching, and routing patterns
---

# Next.js Skill (App Router)

## Routing Conventions

```
app/
  page.tsx          → /
  layout.tsx        → layout wrapper
  loading.tsx       → loading UI (Suspense)
  error.tsx         → error boundary
  not-found.tsx     → 404
  (auth)/           → route group
    login/page.tsx  → /login
  api/
    route.ts        → API route handler
```

## Data Fetching

### Server Components (default)
```tsx
// Fetch directly in server component
async function Page() {
  const data = await fetch('https://api.example.com/data');
  const json = await data.json();
  return <div>{json.map(...)}</div>;
}
```

### Client Components
```tsx
'use client';
// Use SWR, React Query, or useEffect for client-side fetching
```

## Server Actions
```tsx
'use server';
export async function submitForm(formData: FormData) {
  'use server';
  // mutate data, revalidate cache
  revalidatePath('/path');
  redirect('/other');
}
```

## Key Patterns

- Default to Server Components; add `'use client'` only when needed
- Use `generateMetadata` for dynamic SEO metadata
- Use `generateStaticParams` for static generation
- Use `next/image` for optimized images
- Use `next/link` for client-side navigation
- Use `next/navigation` hooks (`useRouter`, `usePathname`, `useSearchParams`)
- Use `revalidatePath` / `revalidateTag` for ISR/on-demand revalidation
- Use `unstable_cache` for memoized data fetching

## Caching

- `fetch()` is cached by default; opt out with `cache: 'no-store'` or `next: { revalidate: N }`
- `revalidateTag(tag)` for targeted cache invalidation
- `revalidatePath(path)` for path-based invalidation
