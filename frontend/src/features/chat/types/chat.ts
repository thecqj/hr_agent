export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  cards?: ChatCard[];
  progress?: ProgressInfo;
  timestamp: number;
}

export interface ChatCard {
  type: "evaluation_summary";
  task_id: string;
  job_title: string;
  total_count: number;
  recommended_count: number;
  rejected_count: number;
  result_page_url: string;
}

export interface ProgressInfo {
  status: string;
  evaluated_count?: number;
  total_count?: number;
}
