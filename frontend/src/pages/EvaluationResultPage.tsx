import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Download,
  Loader2,
  Sparkles,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  useEvaluationTaskQuery,
  useConfirmEvaluationMutation,
  useTriggerEvaluationMutation,
} from "@/features/applications/hooks/useApplications";
import { useJobDetailQuery } from "@/features/jobs/hooks/useJobs";
import { getApiErrorMessage } from "@/shared/api/error";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import type { ConfirmDecision } from "@/features/applications/api/applications";
import { exportEvaluation } from "@/features/applications/api/applications";
import type { EvaluationDetail } from "@/features/applications/types/application";
import EvaluationTriggerDialog from "@/features/applications/components/EvaluationTriggerDialog";

interface DecisionOverride {
  applicationId: string;
  decision: "interview" | "reject" | "ai";
  reason: string;
}

export default function EvaluationResultPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [overrides, setOverrides] = useState<Map<string, DecisionOverride>>(
    new Map(),
  );

  const {
    data: task,
    isLoading,
    isError,
    refetch,
  } = useEvaluationTaskQuery(taskId);
  const { data: job } = useJobDetailQuery(task?.job_id);
  const confirmMutation = useConfirmEvaluationMutation();
  const triggerEvalMutation = useTriggerEvaluationMutation();
  const [showEvalDialog, setShowEvalDialog] = useState(false);

  useEffect(() => {
    setBreadcrumbItems([
      { label: "首页", href: "/dashboard" },
      { label: "我的岗位", href: "/dashboard" },
      ...(job
        ? [
            {
              label: job.title,
              href: `/dashboard/applicants/${task?.job_id}`,
            },
          ]
        : []),
      { label: "评估结果" },
    ]);
  }, [setBreadcrumbItems, job, task]);

  const toggleRow = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDecisionChange = (
    applicationId: string,
    decision: "interview" | "reject" | "ai",
  ) => {
    setOverrides((prev) => {
      const next = new Map(prev);
      if (decision === "ai") {
        next.delete(applicationId);
      } else {
        next.set(applicationId, {
          applicationId,
          decision,
          reason: next.get(applicationId)?.reason || "",
        });
      }
      return next;
    });
  };

  const handleReasonChange = (applicationId: string, reason: string) => {
    setOverrides((prev) => {
      const next = new Map(prev);
      const existing = next.get(applicationId);
      if (existing) {
        next.set(applicationId, { ...existing, reason });
      }
      return next;
    });
  };

  const handleExportExcel = async () => {
    if (!taskId) return;
    try {
      const blob = await exportEvaluation(taskId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `评估结果_${taskId.slice(0, 8)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("导出成功");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "导出失败"));
    }
  };

  const handleConfirm = async () => {
    if (!taskId) return;

    const decisions: ConfirmDecision[] = [];
    for (const [, override] of overrides) {
      decisions.push({
        application_id: override.applicationId,
        final_decision: override.decision as "interview" | "reject",
        override_reason: override.reason || undefined,
      });
    }

    try {
      await confirmMutation.mutateAsync({ taskId, decisions });
      toast.success("评估结果已确认");
      if (task?.job_id) {
        navigate(`/dashboard/applicants/${task.job_id}`);
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err, "确认失败"));
    }
  };

  const handleTriggerEval = async (mode: "new_only" | "all") => {
    if (!task?.job_id) return;
    try {
      const result = await triggerEvalMutation.mutateAsync({
        jobId: task.job_id,
        payload: { mode },
      });
      setShowEvalDialog(false);
      toast.success(`评估已启动，共 ${result.total_count} 份简历待评估`);
      navigate(`/dashboard/evaluation/${result.task_id}`);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "触发评估失败"));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError || !task) {
    return (
      <ErrorState
        message="获取评估结果失败"
        onRetry={refetch}
      />
    );
  }

  if (task.status !== "completed") {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-muted-foreground">
          {task.status === "running"
            ? `评估进行中 (${task.evaluated_count}/${task.total_count})`
            : `任务状态：${task.status}`}
        </p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          {"返回"}
        </Button>
      </div>
    );
  }

  const summary = task.result_summary;
  const recommendCount = summary?.recommend_count ?? 0;
  const rejectCount = summary?.reject_count ?? 0;
  const evaluationDetails: EvaluationDetail[] = (
    (task.result_summary as Record<string, unknown> | undefined)
      ?.evaluation_details as EvaluationDetail[] | undefined
  ) ?? [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {job?.title ?? "岗位"} {"·"} {"评估结果"}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {"任务 ID: "} {taskId}
          </p>
        </div>
        <div className="flex gap-2">
          {task?.job_id && (
            <Button variant="outline" onClick={() => setShowEvalDialog(true)}>
              <Sparkles className="h-4 w-4 mr-2" />
              触发新评估
            </Button>
          )}
          <Button variant="outline" onClick={handleExportExcel}>
            <Download className="h-4 w-4 mr-2" />
            导出 Excel
          </Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              总评估数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{task.total_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {"推荐进面"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">
              {recommendCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {"建议淘汰"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{rejectCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Candidate table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>{"姓名"}</TableHead>
              <TableHead>{"AI 总分"}</TableHead>
              <TableHead>{"AI 决策"}</TableHead>
              <TableHead>{"最终决策"}</TableHead>
              <TableHead>{"决策理由"}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {evaluationDetails.map((detail) => {
              const appId = detail.application_id;
              const isExpanded = expandedRows.has(appId);
              const override = overrides.get(appId);

              return (
                <>
                  <TableRow key={appId}>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => toggleRow(appId)}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="font-medium">
                      {detail.applicant_name}
                    </TableCell>
                    <TableCell>
                      <span className="font-semibold">
                        {detail.ai_score.toFixed(1)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          detail.ai_decision === "recommend"
                            ? "default"
                            : "destructive"
                        }
                      >
                        {detail.ai_decision === "recommend" ? (
                          <>
                            <CheckCircle className="h-3 w-3 mr-1" />
                            {"推荐"}
                          </>
                        ) : (
                          <>
                            <XCircle className="h-3 w-3 mr-1" />
                            {"淘汰"}
                          </>
                        )}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={override?.decision ?? "ai"}
                        onValueChange={(val) =>
                          handleDecisionChange(
                            appId,
                            val as "interview" | "reject" | "ai",
                          )
                        }
                      >
                        <SelectTrigger className="w-28 h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ai">
                            {"保持 AI 建议"}
                          </SelectItem>
                          <SelectItem value="interview">
                            {"改为进面"}
                          </SelectItem>
                          <SelectItem value="reject">
                            {"改为淘汰"}
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                      {override ? (
                        <Textarea
                          value={override.reason}
                          onChange={(e) =>
                            handleReasonChange(appId, e.target.value)
                          }
                          placeholder="填写覆盖理由"
                          className="h-8 text-xs min-w-[160px]"
                        />
                      ) : (
                        detail.ai_decision_reason
                      )}
                    </TableCell>
                  </TableRow>
                  {isExpanded && (
                    <TableRow key={`${appId}-detail`}>
                      <TableCell
                        colSpan={6}
                        className="bg-muted/30 px-8 py-3"
                      >
                        <div className="space-y-2">
                          <p className="text-sm font-medium">
                            {"维度评分"}
                          </p>
                          {detail.ai_evaluation.map((dim, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-3 text-sm"
                            >
                              <span className="w-20 text-muted-foreground">
                                {dim.name}
                              </span>
                              <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-primary rounded-full"
                                  style={{ width: `${dim.score}%` }}
                                />
                              </div>
                              <span className="w-8 text-right font-medium">
                                {dim.score.toFixed(0)}
                              </span>
                              <span className="w-12 text-xs text-muted-foreground">
                                {"权重 "} {dim.weight.toFixed(2)}
                              </span>
                            </div>
                          ))}
                          {detail.ai_decision_reason && (
                            <p className="text-xs text-muted-foreground mt-2">
                              {"评估理由："}
                              {detail.ai_decision_reason}
                            </p>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Confirm button */}
      <div className="mt-6 flex justify-end">
        <Button
          size="lg"
          onClick={handleConfirm}
          disabled={confirmMutation.isPending}
        >
          {confirmMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              {"确认中..."}
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4 mr-2" />
              {"确认评估结果"}
            </>
          )}
        </Button>
      </div>

      {/* Evaluation trigger dialog */}
      <EvaluationTriggerDialog
        open={showEvalDialog}
        onOpenChange={setShowEvalDialog}
        jobTitle={job?.title ?? "该岗位"}
        onConfirm={handleTriggerEval}
      />
    </div>
  );
}
