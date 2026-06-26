import type { ApplicationStatus } from "@/shared/constants/applicationStatus";

export interface Contact {
  phone?: string;
  email?: string;
  wechat?: string;
  other?: string;
}

export interface WorkExperience {
  company: string;
  position: string;
  start_date: string;
  end_date?: string;
  description: string;
}

export interface ProjectExperience {
  name: string;
  role: string;
  start_date: string;
  end_date?: string;
  description: string;
  technologies: string[];
}

export interface Education {
  school: string;
  major: string;
  degree: string;
  start_date: string;
  end_date?: string;
}

export interface Certificate {
  name: string;
  date?: string;
}

export interface DimensionScore {
  name: string;
  score: number;
  weight: number;
  reason: string;
}

export interface EvaluationDetail {
  application_id: string;
  applicant_name: string;
  ai_score: number;
  ai_evaluation: DimensionScore[];
  ai_decision: "recommend" | "reject" | "neutral";
  ai_decision_reason: string;
}

export interface StructuredResume {
  name: string;
  work_experience_years: number;
  education_level?: string;
  contact: Contact;
  work_experience: WorkExperience[];
  project_experience: ProjectExperience[];
  education: Education[];
  certificates: Certificate[];
  skills: string[];
  self_evaluation?: string;
}

export interface Applicant {
  id: string;
  applicant_name: string;
  resume_text: string;
  cover_letter?: string;
  structured_resume?: StructuredResume;
  status: ApplicationStatus;
  // AI evaluation fields (Phase 2)
  ai_score?: number;
  ai_evaluation?: DimensionScore[];
  ai_decision?: string;
  ai_decision_reason?: string;
  ai_evaluated_at?: string;
}

export interface MyApplication {
  id: string;
  job_id: string;
  job_title: string;
  company_name?: string;
  resume_text: string;
  cover_letter?: string;
  status: ApplicationStatus;
  created_at: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface CreateApplicationPayload {
  job_id?: string;
  resume_text: string;
  structured_resume: StructuredResume;
  cover_letter?: string;
}
