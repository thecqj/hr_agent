import { apiClient } from "@/shared/api/client";
import type { AuthResponse, LoginData, RegisterData } from "@/features/auth/types/auth";

export async function loginUser(data: LoginData): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>("/auth/login", data);
  return res.data;
}

export async function registerUser(data: RegisterData): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>("/auth/register", data);
  return res.data;
}
