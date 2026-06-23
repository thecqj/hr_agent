import { apiClient } from "@/shared/api/client";
import type { Applicant, CreateApplicationPayload, MyApplication, PaginatedResponse } from "@/features/applications/types/application";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";

export async function createApplication(payload: CreateApplicationPayload, force = false): Promise<void> {
  await apiClient.post("/applications/", payload, { params: { force } });
}

export async function getMyApplications(): Promise<PaginatedResponse<MyApplication>> {
  const res = await apiClient.get<PaginatedResponse<MyApplication>>("/applications/my");
  return res.data;
}

export async function getApplicationsByJob(jobId: string): Promise<PaginatedResponse<Applicant>> {
  const res = await apiClient.get<PaginatedResponse<Applicant>>(`/applications/job/${jobId}`);
  return res.data;
}

export async function updateApplicationStatus(applicantId: string, status: ApplicationStatus): Promise<void> {
  await apiClient.patch(`/applications/${applicantId}/status`, { status });
}
