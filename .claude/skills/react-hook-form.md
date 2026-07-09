---
name: react-hook-form
description: React Hook Form v7 patterns with Zod validation, type-safe forms, and best practices
---

# React Hook Form Skill

## Basic Setup with Zod
```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type FormData = z.infer<typeof schema>;

function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data: FormData) => {
    // handle submission
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
      <button disabled={isSubmitting}>Submit</button>
    </form>
  );
}
```

## With shadcn/ui
```tsx
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form';

<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Email</FormLabel>
          <FormControl>
            <Input {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  </form>
</Form>
```

## Key Patterns

- Always use Zod resolver for type safety
- Use `useFormContext` for deeply nested forms
- Use `useFieldArray` for dynamic field lists
- Use `watch()` for reactive field values
- Use `setValue()` / `reset()` for programmatic updates
- Use `Controller` for custom UI components
- Set `mode: 'onBlur'` or `mode: 'onChange'` for validation timing
- Use `shouldUnregister: false` to preserve form state on unmount
