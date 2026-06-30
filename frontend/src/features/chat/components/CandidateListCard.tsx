import { Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { CandidateListCardData } from "@/features/chat/types/chat";

interface CandidateListCardProps {
  card: CandidateListCardData;
}

const decisionLabels: Record<string, { label: string; className: string }> = {
  recommend: { label: "推荐", className: "text-green-600" },
  reject: { label: "不推荐", className: "text-red-500" },
};

const statusLabels: Record<string, { label: string; className: string }> = {
  pending: { label: "待审核", className: "bg-yellow-100 text-yellow-700" },
  interview: { label: "面试中", className: "bg-green-100 text-green-700" },
  rejected: { label: "已拒绝", className: "bg-red-100 text-red-600" },
  hired: { label: "已录用", className: "bg-purple-100 text-purple-700" },
};

export function CandidateListCard({ card }: CandidateListCardProps) {
  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-3">
          <Users className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">
            {card.job_title} ({card.job_code})
          </span>
          <span className="text-xs text-muted-foreground">({card.candidates.length} 人)</span>
        </div>

        <div className="space-y-1.5">
          {card.candidates.map((candidate, i) => {
            const decisionInfo = decisionLabels[candidate.ai_decision || ""] || { label: "未评估", className: "text-gray-500" };
            const statusInfo = statusLabels[candidate.status] || { label: candidate.status, className: "bg-gray-100 text-gray-600" };
            return (
              <div
                key={i}
                className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-muted/50 text-sm"
              >
                <span className="font-medium">{candidate.name}</span>
                <div className="flex items-center gap-2">
                  {candidate.ai_score != null && (
                    <span className="text-xs font-mono text-muted-foreground">{candidate.ai_score}分</span>
                  )}
                  <span className={`text-xs ${decisionInfo.className}`}>
                    {decisionInfo.label}
                  </span>
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
