import { apiClient } from "@/shared/api/client";
import type { Applicant, CreateApplicationPayload, MyApplication, PaginatedResponse } from "@/features/applications/types/application";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";

export async function createApplication(payload: CreateApplicationPayload, force = false): Promise<void> {
  await apiClient.post("/applications/", payload, { params: { force } });
}

interface ApplicationListParams {
  page?: number;
  page_size?: number;
  status?: ApplicationStatus;
}

export async function getMyApplications(params: ApplicationListParams = {}): Promise<PaginatedResponse<MyApplication>> {
  const res = await apiClient.get<PaginatedResponse<MyApplication>>("/applications/my", { params });
  return res.data;
}

export async function getApplicationsByJob(jobId: string): Promise<PaginatedResponse<Applicant>> {
  const res = await apiClient.get<PaginatedResponse<Applicant>>(`/applications/job/${jobId}`, {
    params: { page_size: 100 },
  });
  return res.data;
}

export async function updateApplicationStatus(applicantId: string, status: ApplicationStatus): Promise<void> {
  await apiClient.patch(`/applications/${applicantId}/status`, { status });
}

// ── Agent / Evaluation API ─────────────────────────────────

export interface TaskStatusResponse {
  task_id: string;
  job_id: string;
  status: "pending" | "running" | "completed" | "confirmed" | "failed";
  total_count: number;
  evaluated_count: number;
  result_summary?: {
    recommend_count: number;
    reject_count: number;
    cutoff_score: number;
    total_evaluated: number;
    borderline_adjustments: number;
  };
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ConfirmDecision {
  application_id: string;
  final_decision: "interview" | "reject";
  override_reason?: string;
}

export interface ConfirmResponse {
  updated_count: number;
  message: string;
}

export async function getEvaluationTask(taskId: string): Promise<TaskStatusResponse> {
  const res = await apiClient.get<TaskStatusResponse>(`/agent/task/${taskId}`);
  return res.data;
}

export async function confirmEvaluation(
  taskId: string,
  decisions: ConfirmDecision[] = [],
): Promise<ConfirmResponse> {
  const res = await apiClient.post<ConfirmResponse>(`/agent/confirm/${taskId}`, {
    decisions,
  });
  return res.data;
}

// ── Agent Trigger / Tasks / Export ─────────────────────

export interface TriggerEvaluationPayload {
  mode: "new_only" | "all";
}

export interface TriggerEvaluationResponse {
  task_id: string;
  status: string;
  total_count: number;
}

export interface JobTaskItem {
  task_id: string;
  status: string;
  mode: string;
  total_count: number;
  evaluated_count: number;
  created_at: string;
  updated_at: string;
}

export interface JobEvaluationTasksResponse {
  tasks: JobTaskItem[];
}

export async function triggerEvaluation(
  jobId: string,
  payload: TriggerEvaluationPayload = { mode: "new_only" },
): Promise<TriggerEvaluationResponse> {
  const res = await apiClient.post<TriggerEvaluationResponse>(
    `/agent/evaluate/${jobId}`,
    payload,
  );
  return res.data;
}

export async function getJobTasks(jobId: string): Promise<JobEvaluationTasksResponse> {
  const res = await apiClient.get<JobEvaluationTasksResponse>(`/agent/tasks/${jobId}`);
  return res.data;
}

export async function exportEvaluation(taskId: string): Promise<Blob> {
  const res = await apiClient.get(`/agent/export/${taskId}`, {
    responseType: "blob",
  });
  return res.data;
}
