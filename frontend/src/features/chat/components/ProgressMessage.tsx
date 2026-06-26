import { Loader2 } from "lucide-react";

import type { ProgressInfo } from "@/features/chat/types/chat";

interface ProgressMessageProps {
  progress: ProgressInfo;
}

export function ProgressMessage({ progress }: ProgressMessageProps) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      <span>{progress.status}</span>
      {progress.evaluated_count != null && progress.total_count != null && (
        <span className="text-xs">
          ({progress.evaluated_count}/{progress.total_count})
        </span>
      )}
    </div>
  );
}
