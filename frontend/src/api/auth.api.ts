import { apiClient } from "./client";

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    email: string;
    name: string;
    role: "job_seeker" | "recruiter";
    phone?: string | null;
    avatar_url?: string | null;
    is_active: boolean;
  };
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const res = await apiClient.post("/auth/login", { email, password });
  return res.data;
}

export async function registerUser(data: {
  email: string;
  password: string;
  name: string;
  phone?: string;
  role: "job_seeker" | "recruiter";
}): Promise<AuthResponse> {
  const res = await apiClient.post("/auth/register", data);
  return res.data;
}