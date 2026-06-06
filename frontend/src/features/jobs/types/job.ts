export type WorkType = "remote" | "onsite" | "hybrid";
export type JobStatus = "draft" | "active" | "closed";

export interface Job {
  id: string;
  recruiter_id: string;
  title: string;
  description: string;
  salary_min: number | null;
  salary_max: number | null;
  location: string | null;
  work_type: WorkType;
  skills_required: string[];
  status: JobStatus;
  created_at: string;
  updated_at: string;
  recruiter_name?: string;
  applications_count?: number;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export type JobListResponse = PaginatedResponse<Job>;

export interface JobListParams {
  keyword?: string;
  work_type?: WorkType;
  status?: JobStatus | "all";
}

export interface CreateJobPayload {
  title: string;
  description: string;
  location?: string;
  work_type?: WorkType;
  salary_min?: number;
  salary_max?: number;
  skills_required: string[];
}
