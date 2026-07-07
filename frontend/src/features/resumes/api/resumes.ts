import { apiClient } from "@/shared/api/client";
import type { StructuredResume } from "@/features/applications/types/application";

export interface ResumeListItem {
  id: string;
  name: string;
  file_name: string;
  file_type: string;
  created_at: string;
}

export interface ResumeResponse {
  id: string;
  user_id: string;
  name: string;
  file_name: string;
  file_type: string;
  parsed_text: string | null;
  structured_data: StructuredResume | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeListResponse {
  total: number;
  items: ResumeListItem[];
}

export interface ParseResumeResponse {
  parsed_text: string;
  structured_data: StructuredResume;
}

export interface DownloadResponse {
  file_name: string;
  file_type: string;
  file_data: string; // base64
}

export async function parseResume(file: File): Promise<ParseResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiClient.post<ParseResumeResponse>("/resumes/parse", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function uploadResume(file: File, name: string): Promise<ResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  const res = await apiClient.post<ResumeResponse>("/resumes/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function getResumeList(): Promise<ResumeListResponse> {
  const res = await apiClient.get<ResumeListResponse>("/resumes/");
  return res.data;
}

export async function getResumeDetail(id: string): Promise<ResumeResponse> {
  const res = await apiClient.get<ResumeResponse>(`/resumes/${id}`);
  return res.data;
}

export async function downloadResume(id: string): Promise<DownloadResponse> {
  const res = await apiClient.get<DownloadResponse>(`/resumes/${id}/download`);
  return res.data;
}

export async function updateResumeName(id: string, name: string): Promise<ResumeResponse> {
  const res = await apiClient.put<ResumeResponse>(`/resumes/${id}`, { name });
  return res.data;
}

export async function deleteResume(id: string): Promise<void> {
  await apiClient.delete(`/resumes/${id}`);
}
