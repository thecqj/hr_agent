import { cn } from "@/lib/utils";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";

interface StatusBadgeProps {
  status: ApplicationStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = APPLICATION_STATUS_MAP[status];
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
