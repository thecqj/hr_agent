import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/features/auth/store/authStore";

export function useLogout() {
  const navigate = useNavigate();
  const { clearAuth } = useAuthStore();

  return () => {
    clearAuth();
    navigate("/login");
  };
}
