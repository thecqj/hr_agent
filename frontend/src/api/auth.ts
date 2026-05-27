import { apiClient } from "./client";

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: { id: string; email: string; name: string; role: "job_seeker" | "recruiter"; phone?: string | null; avatar_url?: string | null; is_active: boolean; };
}

export interface LoginData { email: string; password: string }
export interface RegisterData { email: string; password: string; name: string; role: string; phone?: string }

export const loginUser = (data: LoginData) => apiClient.post<AuthResponse>('/auth/login', data);
export const registerUser = (data: RegisterData) => apiClient.post<AuthResponse>('/auth/register', data);