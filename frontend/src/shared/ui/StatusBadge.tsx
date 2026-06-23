import { cn } from "@/lib/utils";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";

interface StatusBadgeProps {
  status: ApplicationStatus;
}

const STATUS_STYLES: Record<ApplicationStatus, { label: string; className: string }> = {
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

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_STYLES[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}
