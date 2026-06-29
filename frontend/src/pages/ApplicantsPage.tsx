import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  CheckCircle,
  XCircle,
  FileText,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
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
  useUpdateApplicationStatusMutation,
} from "@/features/applications/hooks/useApplications";
import type { Applicant } from "@/features/applications/types/application";
import { useJobDetailQuery } from "@/features/jobs/hooks/useJobs";
import { getApiErrorMessage } from "@/shared/api/error";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";
import { CategoryTabs } from "@/shared/ui/CategoryTabs";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";

// Status filter tabs (全部 / 待审核 / 已通过 / 已拒绝)
const STATUS_CATEGORIES = [
  { key: "all", label: "全部" },
  { key: "pending", label: "待审核" },
  { key: "reviewed", label: "已审阅" },
  { key: "rejected", label: "已拒绝" },
];

function formatDate(dateStr?: string) {
  if (!dateStr) return "至今";
  return new Date(dateStr).toLocaleDateString();
}

export default function ApplicantsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedApplicant, setSelectedApplicant] = useState<Applicant | null>(null);
  const [rejectTarget, setRejectTarget] = useState<Applicant | null>(null);

  const { data: job } = useJobDetailQuery(jobId);
  const { data, isLoading, isError, refetch } = useApplicantsByJobQuery(jobId);
  const updateStatusMutation = useUpdateApplicationStatusMutation(jobId);
  const allApplicants = data?.items ?? [];

  // Filter applicants by status
  const applicants = useMemo(() => {
    if (statusFilter === "all") return allApplicants;
    return allApplicants.filter((a) => a.status === statusFilter);
  }, [allApplicants, statusFilter]);

  useEffect(() => {
    setBreadcrumbItems([
      { label: "首页", href: "/dashboard" },
      { label: "我的岗位", href: "/dashboard" },
      ...(job ? [{ label: job.title }] : []),
      { label: "申请人" },
    ]);
  }, [setBreadcrumbItems, job]);

  const updateStatus = async (applicantId: string, newStatus: ApplicationStatus) => {
    try {
      await updateStatusMutation.mutateAsync({ applicantId, status: newStatus });
      toast.success("状态已更新");
      setSelectedApplicant(null); // Close dialog — cache invalidation will refresh table
    } catch (err) {
      toast.error(getApiErrorMessage(err, "状态更新失败"));
    }
  };

  const handleReject = async () => {
    if (!rejectTarget) return;
    try {
      await updateStatusMutation.mutateAsync({ applicantId: rejectTarget.id, status: "rejected" });
      toast.success("状态已更新");
      setRejectTarget(null);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "状态更新失败"));
    }
  };

  const renderResumeDialog = () => {
    if (!selectedApplicant) return null;
    const resume = selectedApplicant.structured_resume;

    return (
      <Dialog open={!!selectedApplicant} onOpenChange={() => setSelectedApplicant(null)}>
        <DialogContent className="!max-w-4xl !max-h-[85vh] flex flex-col p-0">
          <DialogHeader className="shrink-0 px-6 py-4 border-b">
            <DialogTitle className="flex items-center gap-3">
              {selectedApplicant.applicant_name} 的简历
              <StatusBadge status={selectedApplicant.status} />
            </DialogTitle>
            <DialogDescription className="sr-only">
              查看申请人的详细简历信息
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6 text-sm">
            {resume ? (
              <>
                {/* 基本信息 */}
                <div className="bg-muted/50 p-4 rounded-lg">
                  <h3 className="font-semibold mb-3 text-base border-b pb-2">基本信息</h3>
                  <div className="grid grid-cols-2 gap-y-2 gap-x-6">
                    <div>
                      <span className="font-medium">姓名：</span>
                      {resume.name}
                    </div>
                    <div>
                      <span className="font-medium">工作年限：</span>
                      {resume.work_experience_years}年
                    </div>
                    {resume.education_level && (
                      <div>
                        <span className="font-medium">最高学历：</span>
                        {resume.education_level}
                      </div>
                    )}
                  </div>
                </div>

                {/* 联系方式 */}
                {resume.contact && Object.values(resume.contact).some(Boolean) && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">联系方式</h3>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                      {resume.contact.phone && (
                        <div><span className="font-medium">📱 手机：</span>{resume.contact.phone}</div>
                      )}
                      {resume.contact.email && (
                        <div><span className="font-medium">✉️ 邮箱：</span>{resume.contact.email}</div>
                      )}
                      {resume.contact.wechat && (
                        <div><span className="font-medium">💬 微信：</span>{resume.contact.wechat}</div>
                      )}
                      {resume.contact.other && (
                        <div><span className="font-medium">🔗 其他：</span>{resume.contact.other}</div>
                      )}
                    </div>
                  </div>
                )}

                {/* 工作经历 */}
                {resume.work_experience?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">工作经历</h3>
                    {resume.work_experience.map((exp, index) => (
                      <div key={index} className="mb-3 border-l-4 border-primary/30 pl-4 last:mb-0">
                        <p className="font-semibold">{exp.company}</p>
                        <p className="text-sm text-muted-foreground">
                          {exp.position} &nbsp;|&nbsp; {formatDate(exp.start_date)} ~ {formatDate(exp.end_date)}
                        </p>
                        <p className="mt-1 text-muted-foreground">{exp.description}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* 项目经历 */}
                {resume.project_experience?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">项目经历</h3>
                    {resume.project_experience.map((proj, index) => (
                      <div key={index} className="mb-3 border-l-4 border-primary/30 pl-4 last:mb-0">
                        <p className="font-semibold">{proj.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {proj.role} &nbsp;|&nbsp; {formatDate(proj.start_date)} ~ {formatDate(proj.end_date)}
                        </p>
                        <p className="mt-1 text-muted-foreground">{proj.description}</p>
                        {proj.technologies?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {proj.technologies.map((tech) => (
                              <Badge key={tech} variant="secondary" className="text-xs">
                                {tech}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* 教育经历 */}
                {resume.education?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">教育经历</h3>
                    {resume.education.map((edu, index) => (
                      <div key={index} className="flex justify-between items-center mb-2 border-b border-dashed pb-1 last:border-0 last:mb-0">
                        <span>
                          <span className="font-medium">{edu.school}</span> · {edu.major} · {edu.degree}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(edu.start_date)} ~ {formatDate(edu.end_date)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* 资格证书 */}
                {resume.certificates?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">资格证书</h3>
                    <div className="flex flex-wrap gap-2">
                      {resume.certificates.map((cert, index) => (
                        <Badge key={index} variant="outline" className="text-sm py-1 px-3">
                          {cert.name}{cert.date ? ` (${cert.date})` : ""}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* 专业技能 */}
                {resume.skills?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">专业技能</h3>
                    <div className="flex flex-wrap gap-2">
                      {resume.skills.map((skill, index) => (
                        <Badge key={skill} variant="default" className="bg-primary/20 text-primary-foreground hover:bg-primary/30 text-sm py-1 px-3">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* 自我评价 */}
                {resume.self_evaluation && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">自我评价</h3>
                    <p className="whitespace-pre-wrap leading-relaxed">{resume.self_evaluation}</p>
                  </div>
                )}
              </>
            ) : (
              <div>
                <h3 className="font-semibold mb-2">简历内容（纯文本）</h3>
                <p className="whitespace-pre-wrap text-sm">
                  {selectedApplicant.resume_text || "无简历内容"}
                </p>
              </div>
            )}

            {/* 求职信 */}
            {selectedApplicant.cover_letter && (
              <div className="bg-muted/50 p-4 rounded-lg">
                <h3 className="font-semibold mb-2 text-base border-b pb-2">求职信</h3>
                <p className="whitespace-pre-wrap text-sm">{selectedApplicant.cover_letter}</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    );
  };

  if (isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-48 mb-6" />
        <Skeleton className="h-10 w-64 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return <ErrorState message="获取投递列表失败" onRetry={refetch} />;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {job ? job.title : "岗位"} · 申请人
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            共 {applicants.length} 位申请人
          </p>
        </div>
      </div>

      {/* Status filter */}
      <div className="mb-6">
        <CategoryTabs
          categories={STATUS_CATEGORIES}
          activeKey={statusFilter}
          onSelect={setStatusFilter}
        />
      </div>

      {/* Content */}
      {applicants.length === 0 ? (
        <EmptyState
          icon={Users}
          message="暂无申请人"
        />
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>姓名</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>工作年限</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {applicants.map((app) => (
                <TableRow key={app.id}>
                  <TableCell className="font-medium">{app.applicant_name}</TableCell>
                  <TableCell>
                    <StatusBadge status={app.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {app.structured_resume?.work_experience_years != null
                      ? `${app.structured_resume.work_experience_years}年`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedApplicant(app)}
                      >
                        <FileText className="h-4 w-4 mr-1" />
                        查看简历
                      </Button>
                      {app.status === "pending" && (
                        <>
                          <Button
                            size="sm"
                            onClick={() => updateStatus(app.id, "reviewed")}
                            disabled={updateStatusMutation.isPending}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            通过
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => setRejectTarget(app)}
                            disabled={updateStatusMutation.isPending}
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            拒绝
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Resume dialog */}
      {renderResumeDialog()}

      {/* Reject confirmation dialog */}
      <Dialog open={!!rejectTarget} onOpenChange={() => setRejectTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认拒绝</DialogTitle>
            <DialogDescription>
              确定要拒绝该申请人吗？
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectTarget(null)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={updateStatusMutation.isPending}
            >
              确认拒绝
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
