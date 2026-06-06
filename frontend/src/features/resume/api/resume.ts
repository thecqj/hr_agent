import { apiClient } from "@/shared/api/client";
import type { StructuredResume } from "@/features/applications/types/application";

export async function parseResumeFile(file: File): Promise<StructuredResume> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await apiClient.post<StructuredResume>("/resume/parse", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return res.data;
}
