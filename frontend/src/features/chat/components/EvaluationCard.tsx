import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { ChatCard } from "@/features/chat/types/chat";

interface EvaluationCardProps {
  card: ChatCard;
}

export function EvaluationCard({ card }: EvaluationCardProps) {
  const navigate = useNavigate();

  return (
    <Card
      className="mt-2 cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={() => navigate(card.result_page_url)}
    >
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">{card.job_title}</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
          <div>
            总计 <span className="font-medium text-foreground">{card.total_count}</span>
          </div>
          <div>
            推荐 <span className="font-medium text-green-600">{card.recommended_count}</span>
          </div>
          <div>
            淘汰 <span className="font-medium text-red-500">{card.rejected_count}</span>
          </div>
        </div>
        <p className="text-xs text-primary mt-2">点击查看详情 →</p>
      </CardContent>
    </Card>
  );
}
