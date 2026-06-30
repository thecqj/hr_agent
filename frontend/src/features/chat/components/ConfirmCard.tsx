import { AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { ConfirmCardData } from "@/features/chat/types/chat";

interface ConfirmCardProps {
  card: ConfirmCardData;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmCard({ card, onConfirm, onCancel }: ConfirmCardProps) {
  return (
    <Card className="mt-2 border-yellow-200 bg-yellow-50/50">
      <CardContent className="p-3">
        <div className="flex items-start gap-2 mb-3">
          <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 shrink-0" />
          <span className="text-sm">{card.action}</span>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={onCancel}>
            取消
          </Button>
          <Button variant="default" size="sm" onClick={onConfirm}>
            确认
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
