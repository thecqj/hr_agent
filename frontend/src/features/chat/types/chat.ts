// ── 漏斗阶段 ─────────────────────────────────────────────

export interface FunnelStageData {
  status: string;
  count: number;
  percentage: number;
}

// ── 候选人条目 ─────────────────────────────────────────────

export interface CandidateItemData {
  name: string;
  ai_score: number | null;
  ai_decision: string | null;
  status: string;
}

// ── 卡片类型 ─────────────────────────────────────────────

export interface EvaluationSummaryCardData {
  type: "evaluation_summary";
  task_id: string;
  job_title: string;
  total_count: number;
  recommended_count: number;
  rejected_count: number;
  result_page_url: string;
}

export interface JobListCardData {
  type: "job_list";
  jobs: {
    job_code: string;
    title: string;
    status: string;
    head_count: number;
  }[];
}

export interface JobDetailCardData {
  type: "job_detail";
  job: {
    job_code: string;
    title: string;
    description: string;
    requirements: string;
    skills_required: string[];
    salary_min: number | null;
    salary_max: number | null;
    location: string | null;
    work_type: string;
    head_count: number;
    interview_quota: number;
    status: string;
  };
}

export interface FunnelCardData {
  type: "funnel";
  job_code: string;
  job_title: string;
  stages: FunnelStageData[];
}

export interface CandidateListCardData {
  type: "candidate_list";
  job_code: string;
  job_title: string;
  candidates: CandidateItemData[];
}

export interface ConfirmCardData {
  type: "confirm";
  action: string;
  params: Record<string, unknown>;
}

// ── 联合类型 ─────────────────────────────────────────────

export type ChatCard =
  | EvaluationSummaryCardData
  | JobListCardData
  | JobDetailCardData
  | FunnelCardData
  | CandidateListCardData
  | ConfirmCardData;

// ── 消息 & 进度 ─────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  cards?: ChatCard[];
  progress?: ProgressInfo;
  timestamp: number;
}

export interface ProgressInfo {
  status: string;
  evaluated_count?: number;
  total_count?: number;
}
