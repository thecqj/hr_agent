import { useState } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

type EvalMode = "new_only" | "all";

interface EvaluationTriggerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  jobTitle: string;
  onConfirm: (mode: EvalMode) => Promise<void>;
}

const MODE_OPTIONS: { value: EvalMode; title: string; desc: string }[] = [
  {
    value: "new_only",
    title: "仅评估新投递的简历",
    desc: "只评估尚未处理的新投递申请，已评估过的简历不会重复评估",
  },
  {
    value: "all",
    title: "重新评估所有简历",
    desc: "对该岗位下所有投递重新进行 AI 评估，之前的评估结果将被覆盖",
  },
];

export default function EvaluationTriggerDialog({
  open,
  onOpenChange,
  jobTitle,
  onConfirm,
}: EvaluationTriggerDialogProps) {
  const [mode, setMode] = useState<EvalMode>("new_only");
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm(mode);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            AI 智能评估
          </DialogTitle>
          <DialogDescription>
            对「{jobTitle}」的投递简历进行 AI 评估，系统将根据岗位要求自动评分并推荐候选人。
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-3">
          {MODE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setMode(opt.value)}
              className={cn(
                "w-full text-left rounded-lg border p-4 transition-colors cursor-pointer",
                mode === opt.value
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "hover:bg-muted/50",
              )}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 mt-0.5",
                    mode === opt.value
                      ? "border-primary bg-primary"
                      : "border-muted-foreground",
                  )}
                >
                  {mode === opt.value && <Check className="h-3 w-3 text-white" />}
                </div>
                <div>
                  <p className="font-medium text-sm">{opt.title}</p>
                  <p className="text-sm text-muted-foreground mt-1">{opt.desc}</p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            取消
          </Button>
          <Button onClick={handleConfirm} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                触发中...
              </>
            ) : (
              "开始评估"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
