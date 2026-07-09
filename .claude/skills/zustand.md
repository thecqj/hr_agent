---
name: zustand
description: Zustand state management patterns with TypeScript, middleware, and best practices
---

# Zustand Skill

## Store Pattern
```ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface CounterState {
  count: number;
  increment: () => void;
  decrement: () => void;
  reset: () => void;
}

const useCounterStore = create<CounterState>()(
  devtools(
    persist(
      immer((set) => ({
        count: 0,
        increment: () => set((state) => { state.count += 1; }),
        decrement: () => set((state) => { state.count -= 1; }),
        reset: () => set({ count: 0 }),
      })),
      { name: 'counter-storage' }
    ),
    { name: 'CounterStore' }
  )
);
```

## Async Actions
```ts
interface UserStore {
  user: User | null;
  loading: boolean;
  fetchUser: (id: string) => Promise<void>;
}

const useUserStore = create<UserStore>()((set) => ({
  user: null,
  loading: false,
  fetchUser: async (id: string) => {
    set({ loading: true });
    try {
      const user = await api.getUser(id);
      set({ user, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
```

## Selectors (Performance)
```tsx
// In component — use selectors to prevent unnecessary re-renders
const count = useCounterStore((state) => state.count);
const increment = useCounterStore((state) => state.increment);

// Or use shallow comparison for multiple values
import { shallow } from 'zustand/shallow';
const { count, increment } = useCounterStore(
  (state) => ({ count: state.count, increment: state.increment }),
  shallow
);
```

## Slices Pattern (Large Stores)
```ts
// Split large stores into slices, then combine
import { create } from 'zustand';
import { type StoreApi, type UseBoundStore } from 'zustand';

type WithSelectors<S> = S extends { getState: () => infer T }
  ? S & { use: { [K in keyof T]: () => T[K] } }
  : never;

const createSelectors = <S extends UseBoundStore<StoreApi<object>>>(
  _store: S
) => {
  const store = _store as WithSelectors<typeof _store>;
  store.use = {} as any;
  for (const k of Object.keys(store.getState())) {
    (store.use as any)[k] = () => store((s) => (s as any)[k]);
  }
  return store;
};
```

## Key Patterns

- Use `devtools` middleware for Redux DevTools integration
- Use `persist` middleware for persisted state (localStorage/AsyncStorage)
- Use `immer` middleware for nested state updates
- Use selectors to prevent unnecessary re-renders
- Use `shallow` comparison for selecting multiple values
- Use slices pattern for stores with >10 properties
- Keep stores flat when possible; use composition over nesting
- Define store types explicitly (do not infer complex store types)
