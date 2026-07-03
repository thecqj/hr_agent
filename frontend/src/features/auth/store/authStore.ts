import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/features/auth/types/auth";

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  setAuth: (token: string, refreshToken: string, user: User) => void;
  clearAuth: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      setAuth: (token, refreshToken, user) => set({ token, refreshToken, user }),
      clearAuth: () => {
        // Clear chat session localStorage entries
        Object.keys(localStorage)
          .filter(key => key.startsWith("chat-session-id:"))
          .forEach(key => localStorage.removeItem(key));
        set({ token: null, refreshToken: null, user: null });
      },
      logout: () => {
        // Clear chat session localStorage entries
        Object.keys(localStorage)
          .filter(key => key.startsWith("chat-session-id:"))
          .forEach(key => localStorage.removeItem(key));
        set({ token: null, refreshToken: null, user: null });
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
);
