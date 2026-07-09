import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate } from "react-router-dom";
import { ExternalLink, FileText } from "lucide-react";

import type { ChatMessage } from "@/features/chat/types/chat";
import { ProgressMessage } from "./ProgressMessage";
import { Button } from "@/components/ui/button";

interface AssistantMessageProps {
  message: ChatMessage;
}

/** 从消息文本中提取 task_id（匹配"任务 ID: xxx"格式） */
function extractTaskId(content: string): string | null {
  const match = content.match(/任务 ID:\s*(\S+)/);
  return match ? match[1] : null;
}

/** 判断消息是否包含评估完成信息（文本回退检测） */
function isEvaluationResult(content: string): boolean {
  return content.includes("评估完成") && content.includes("任务 ID:");
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  const navigate = useNavigate();

  // Structured evaluation data takes priority
  const evalComplete = message.evaluationComplete;
  const taskId = evalComplete?.task_id ?? extractTaskId(message.content);
  const showEvalButton = evalComplete || (isEvaluationResult(message.content) && taskId);

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-muted rounded-2xl rounded-bl-sm px-3.5 py-2.5">
        {message.progress ? (
          <ProgressMessage progress={message.progress} />
        ) : message.toolStatus?.status === "started" ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span>{message.content}</span>
          </div>
        ) : (
          <div className="text-sm leading-relaxed prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-table:text-xs">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>

            {/* Evaluation result button — structured data or text fallback */}
            {showEvalButton && (
              <div className="mt-3 pt-3 border-t border-border">
                {evalComplete ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground mb-2">
                      <div>
                        总计 <span className="font-medium text-foreground">{evalComplete.total_count}</span>
                      </div>
                      <div>
                        推荐 <span className="font-medium text-green-600">{evalComplete.recommend_count}</span>
                      </div>
                      <div>
                        淘汰 <span className="font-medium text-red-500">{evalComplete.reject_count}</span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => navigate(evalComplete.result_page_url)}
                      className="w-full"
                    >
                      <FileText className="h-4 w-4 mr-2" />
                      查看完整评估报告
                    </Button>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => navigate(`/dashboard/evaluation/${taskId}`)}
                    className="w-full"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    查看评估结果详情
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
