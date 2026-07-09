import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  Sparkles,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useApplicantsByJobQuery,
  useEvaluationTasksQuery,
  useTriggerEvaluationMutation,
} from "@/features/applications/hooks/useApplications";
import { useJobDetailQuery } from "@/features/jobs/hooks/useJobs";
import { getApiErrorMessage } from "@/shared/api/error";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import EvaluationTriggerDialog from "@/features/applications/components/EvaluationTriggerDialog";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";

function formatDate(dateStr?: string | null) {
  if (!dateStr) return "至今";
  return new Date(dateStr).toLocaleDateString();
}

export default function JobEvaluationPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [showEvalDialog, setShowEvalDialog] = useState(false);
  const [selectedResume, setSelectedResume] = useState<any>(null);

  const { data: job, isLoading: jobLoading } = useJobDetailQuery(jobId);
  const { data: applicantsData, isLoading, isError, refetch } = useApplicantsByJobQuery(jobId);
  const { data: tasksData } = useEvaluationTasksQuery(jobId);
  const triggerEvalMutation = useTriggerEvaluationMutation();

  const applicants = applicantsData?.items ?? [];
  const tasks = tasksData?.tasks ?? [];
  const latestCompletedTask = tasks.find((t) => t.status === "completed" || t.status === "confirmed");

  // Stats
  const totalCount = applicants.length;
  const evaluatedCount = applicants.filter((a) => a.ai_score != null).length;
  const recommendCount = applicants.filter((a) => a.ai_decision === "recommend").length;
  const rejectCount = applicants.filter((a) => a.ai_decision === "reject").length;

  useEffect(() => {
    setBreadcrumbItems([
      { label: "首页", href: "/dashboard" },
      { label: "我的岗位", href: "/dashboard" },
      ...(job ? [{ label: job.title }] : []),
      { label: "AI 评估" },
    ]);
  }, [setBreadcrumbItems, job]);

  const toggleRow = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleTriggerEval = async (mode: "new_only" | "all") => {
    if (!jobId) return;
    try {
      const result = await triggerEvalMutation.mutateAsync({
        jobId,
        payload: { mode },
      });
      setShowEvalDialog(false);
      toast.success(`评估已启动，共 ${result.total_count} 份简历待评估`);
      navigate(`/dashboard/evaluation/${result.task_id}`);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "触发评估失败"));
    }
  };

  if (isLoading || jobLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError) {
    return <ErrorState message="获取数据失败" onRetry={refetch} />;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {job?.title ?? "岗位"} · AI 评估
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            共 {totalCount} 位申请人，{evaluatedCount} 份已评估
          </p>
        </div>
        <div className="flex gap-2">
          {latestCompletedTask && (
            <Button
              variant="outline"
              onClick={() => navigate(`/dashboard/evaluation/${latestCompletedTask.task_id}`)}
            >
              <FileText className="h-4 w-4 mr-2" />
              查看完整评估报告
            </Button>
          )}
          <Button onClick={() => setShowEvalDialog(true)}>
            <Sparkles className="h-4 w-4 mr-2" />
            触发新评估
          </Button>
          <Button variant="outline" onClick={() => navigate("/dashboard")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总申请数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{totalCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">已评估</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">{evaluatedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">推荐进面</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">{recommendCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">建议淘汰</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{rejectCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Applicants table with AI evaluation */}
      {applicants.length === 0 ? (
        <EmptyState icon={FileText} message="暂无申请人" />
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>姓名</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>AI 总分</TableHead>
                <TableHead>AI 决策</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {applicants.map((app) => {
                const appId = app.id;
                const isExpanded = expandedRows.has(appId);
                const hasEval = app.ai_score != null;
                const evalData = app.ai_evaluation as Array<{ name: string; score: number; weight: number; reason: string }> | undefined;

                return (
                  <>
                    <TableRow key={appId}>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => toggleRow(appId)}
                          disabled={!hasEval}
                        >
                          {hasEval && (isExpanded ? (
                            <ChevronDown className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronRight className="h-3.5 w-3.5" />
                          ))}
                        </Button>
                      </TableCell>
                      <TableCell className="font-medium">{app.applicant_name}</TableCell>
                      <TableCell>
                        <StatusBadge status={app.status as any} />
                      </TableCell>
                      <TableCell>
                        {hasEval ? (
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden w-20">
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${Math.min((app.ai_score ?? 0), 100)}%`,
                                  backgroundColor:
                                    (app.ai_score ?? 0) >= 60 ? "#22c55e" : (app.ai_score ?? 0) >= 40 ? "#eab308" : "#ef4444",
                                }}
                              />
                            </div>
                            <span className="font-semibold text-sm w-8 text-right">
                              {app.ai_score?.toFixed(1)}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">待评估</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {app.ai_decision === "recommend" ? (
                          <Badge variant="default" className="bg-green-600">
                            <CheckCircle className="h-3 w-3 mr-1" />推荐
                          </Badge>
                        ) : app.ai_decision === "reject" ? (
                          <Badge variant="destructive">
                            <XCircle className="h-3 w-3 mr-1" />淘汰
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedResume(app)}
                        >
                          <FileText className="h-3.5 w-3.5 mr-1" />
                          查看简历
                        </Button>
                      </TableCell>
                    </TableRow>
                    {isExpanded && hasEval && (
                      <TableRow key={`${appId}-detail`}>
                        <TableCell colSpan={6} className="bg-muted/30 px-8 py-3">
                          <div className="space-y-2">
                            <p className="text-sm font-medium">维度评分</p>
                            {evalData?.map((dim, i) => (
                              <div key={i} className="flex items-center gap-3 text-sm">
                                <span className="w-20 text-muted-foreground">{dim.name}</span>
                                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-primary rounded-full"
                                    style={{ width: `${dim.score}%` }}
                                  />
                                </div>
                                <span className="w-8 text-right font-medium">{dim.score.toFixed(0)}</span>
                                <span className="w-14 text-xs text-muted-foreground">权重 {dim.weight.toFixed(2)}</span>
                              </div>
                            ))}
                            {app.ai_decision_reason && (
                              <p className="text-xs text-muted-foreground mt-2">
                                评估理由：{app.ai_decision_reason}
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
      )}

      {/* Resume detail dialog */}
      <Dialog open={!!selectedResume} onOpenChange={() => setSelectedResume(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedResume?.applicant_name} 的简历</DialogTitle>
          </DialogHeader>
          <div className="text-sm space-y-4">
            {selectedResume?.structured_resume ? (
              <>
                <div>
                  <h4 className="font-semibold mb-2">基本信息</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <div><span className="text-muted-foreground">姓名：</span>{selectedResume.structured_resume.name}</div>
                    <div><span className="text-muted-foreground">工作年限：</span>{selectedResume.structured_resume.work_experience_years}年</div>
                    {selectedResume.structured_resume.education_level && (
                      <div><span className="text-muted-foreground">最高学历：</span>{selectedResume.structured_resume.education_level}</div>
                    )}
                  </div>
                </div>
                {(selectedResume.structured_resume.skills?.length ?? 0) > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">专业技能</h4>
                    <div className="flex flex-wrap gap-1">
                      {selectedResume.structured_resume.skills.map((s: string) => (
                        <Badge key={s} variant="secondary">{s}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-muted-foreground">{selectedResume?.resume_text || "无简历内容"}</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

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
