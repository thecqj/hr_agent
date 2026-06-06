import { apiClient } from "@/shared/api/client";
import type { CreateJobPayload, Job, JobListParams, JobListResponse, JobStatus } from "@/features/jobs/types/job";

export async function getJobs(params: JobListParams = {}): Promise<JobListResponse> {
  const res = await apiClient.get<JobListResponse>("/jobs/", { params });
  return res.data;
}

export async function getJobById(id: string): Promise<Job> {
  const res = await apiClient.get<Job>(`/jobs/${id}`);
  return res.data;
}

export async function updateJobStatus(jobId: string, status: JobStatus): Promise<void> {
  await apiClient.patch(`/jobs/${jobId}/status`, { status });
}

export async function createJob(payload: CreateJobPayload): Promise<void> {
  await apiClient.post("/jobs/", payload);
}

export async function deleteJob(jobId: string): Promise<void> {
  await apiClient.delete(`/jobs/${jobId}`);
}

export async function evaluateJob(jobId: string): Promise<void> {
  await apiClient.post(`/agent/evaluate/${jobId}`);
}
