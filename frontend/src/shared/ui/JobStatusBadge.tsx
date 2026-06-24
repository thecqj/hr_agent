import { cn } from "@/lib/utils";
import { JOB_STATUS_MAP } from "@/shared/constants/applicationStatus";
import type { JobStatus } from "@/features/jobs/types/job";

interface JobStatusBadgeProps {
  status: JobStatus;
  className?: string;
}

export function JobStatusBadge({ status, className }: JobStatusBadgeProps) {
  const config = JOB_STATUS_MAP[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
