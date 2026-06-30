import { BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { FunnelCardData } from "@/features/chat/types/chat";

interface FunnelCardProps {
  card: FunnelCardData;
}

const stageColors: Record<string, string> = {
  "待审核": "bg-blue-500",
  "面试中": "bg-green-500",
  "已拒绝": "bg-red-400",
  "已录用": "bg-purple-500",
};

const stageTextColors: Record<string, string> = {
  "待审核": "text-blue-700",
  "面试中": "text-green-700",
  "已拒绝": "text-red-600",
  "已录用": "text-purple-700",
};

export function FunnelCard({ card }: FunnelCardProps) {
  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">
            {card.job_title} ({card.job_code})
          </span>
        </div>

        <div className="space-y-2.5">
          {card.stages.map((stage) => {
            const barColor = stageColors[stage.status] || "bg-gray-400";
            const textColor = stageTextColors[stage.status] || "text-gray-700";
            return (
              <div key={stage.status}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className={`font-medium ${textColor}`}>{stage.status}</span>
                  <span className="text-muted-foreground">
                    {stage.count} 人 ({stage.percentage}%)
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${barColor} transition-all`}
                    style={{ width: `${Math.max(stage.percentage, 2)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
