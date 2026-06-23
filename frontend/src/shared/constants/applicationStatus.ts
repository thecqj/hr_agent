export type BadgeVariant = "default" | "secondary" | "destructive" | "outline" | "ghost" | "link";

export type ApplicationStatus = "pending" | "reviewed" | "interview" | "rejected" | "hired";

export const APPLICATION_STATUS_MAP: Record<
  ApplicationStatus,
  { label: string; variant: BadgeVariant }
> = {
  pending: { label: "待审核", variant: "outline" },
  reviewed: { label: "已审阅", variant: "secondary" },
  interview: { label: "面试中", variant: "default" },
  rejected: { label: "已拒绝", variant: "destructive" },
  hired: { label: "已录用", variant: "default" },
};
