import { useMutation } from "@tanstack/react-query";

import { loginUser, registerUser } from "@/features/auth/api/auth";
import { useAuthStore } from "@/features/auth/store/authStore";
import type { LoginData, RegisterData } from "@/features/auth/types/auth";

export function useLoginMutation() {
  const { setAuth } = useAuthStore();

  return useMutation({
    mutationFn: (data: LoginData) => loginUser(data),
    onSuccess: (data) => {
      setAuth(data.access_token, data.refresh_token, data.user);
    },
  });
}

export function useRegisterMutation() {
  const { setAuth } = useAuthStore();

  return useMutation({
    mutationFn: (data: RegisterData) => registerUser(data),
    onSuccess: (data) => {
      setAuth(data.access_token, data.refresh_token, data.user);
    },
  });
}
