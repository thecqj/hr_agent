import { Briefcase } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { JobListCardData } from "@/features/chat/types/chat";

interface JobListCardProps {
  card: JobListCardData;
}

const statusLabels: Record<string, { label: string; className: string }> = {
  active: { label: "活跃", className: "bg-green-100 text-green-700" },
  closed: { label: "已关闭", className: "bg-gray-100 text-gray-600" },
  draft: { label: "草稿", className: "bg-yellow-100 text-yellow-700" },
};

export function JobListCard({ card }: JobListCardProps) {
  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-3">
          <Briefcase className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">岗位列表</span>
          <span className="text-xs text-muted-foreground">({card.jobs.length})</span>
        </div>
        <div className="space-y-2">
          {card.jobs.map((job) => {
            const statusInfo = statusLabels[job.status] || { label: job.status, className: "bg-gray-100 text-gray-600" };
            return (
              <div
                key={job.job_code}
                className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-muted/50 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{job.job_code}</span>
                  <span>{job.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{job.head_count}人</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${statusInfo.className}`}>
                    {statusInfo.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
