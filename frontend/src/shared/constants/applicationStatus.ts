import type { JobStatus } from "@/features/jobs/types/job";

export type ApplicationStatus = "pending" | "reviewed" | "interview" | "rejected" | "hired";

export interface StatusStyle {
  label: string;
  className: string;
}

export const JOB_STATUS_MAP: Record<JobStatus, StatusStyle> = {
  active: {
    label: "活跃",
    className: "bg-green-100 text-green-800 hover:bg-green-100/80",
  },
  draft: {
    label: "草稿",
    className: "bg-slate-100 text-slate-800 hover:bg-slate-100/80",
  },
  closed: {
    label: "已关闭",
    className: "bg-red-100 text-red-800 hover:bg-red-100/80",
  },
};

export const APPLICATION_STATUS_MAP: Record<ApplicationStatus, StatusStyle> = {
  pending: {
    label: "待审核",
    className: "bg-amber-100 text-amber-800 hover:bg-amber-100/80",
  },
  reviewed: {
    label: "已审阅",
    className: "bg-blue-100 text-blue-800 hover:bg-blue-100/80",
  },
  interview: {
    label: "面试中",
    className: "bg-indigo-100 text-indigo-800 hover:bg-indigo-100/80",
  },
  rejected: {
    label: "已拒绝",
    className: "bg-red-100 text-red-800 hover:bg-red-100/80",
  },
  hired: {
    label: "已录用",
    className: "bg-green-100 text-green-800 hover:bg-green-100/80",
  },
};
