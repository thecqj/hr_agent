// src/types/job.ts

export interface Job {
  id: string;
  recruiter_id: string;
  title: string;
  description: string;
  salary_min: number | null;
  salary_max: number | null;
  location: string | null;
  work_type: "remote" | "onsite" | "hybrid";
  skills_required: string[];
  status: "draft" | "active" | "closed";
  created_at: string;
  updated_at: string;
  recruiter_name?: string; // 可选，用于展示
  total: number;
  page: number;
  page_size: number;
  items: Job[];
}