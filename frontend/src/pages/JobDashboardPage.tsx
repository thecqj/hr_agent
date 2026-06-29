import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Briefcase,
  Eye,
  FileText,
  MapPin,
  Power,
  MoreHorizontal,
  TrendingUp,
  XCircle,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuthStore } from "@/features/auth/store/authStore";
import {
  useDeleteJobMutation,
  useJobDetailQuery,
  useRecruiterJobsQuery,
  useUpdateJobStatusMutation,
} from "@/features/jobs/hooks/useJobs";
import type { Job } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import { JobStatusBadge } from "@/shared/ui/JobStatusBadge";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { StatCard } from "@/shared/ui/StatCard";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";

const WORK_TYPE_LABELS: Record<string, string> = {
  remote: "远程",
  onsite: "现场",
  hybrid: "混合",
};

function JobDetailContent({ jobId }: { jobId: string }) {
  const { data: job, isLoading } = useJobDetailQuery(jobId);

  if (isLoading) {
    return <div className="space-y-3"><div className="h-6 w-48 bg-muted rounded" /><div className="h-4 w-32 bg-muted rounded" /><div className="h-20 w-full bg-muted rounded" /></div>;
  }

  if (!job) {
    return <p className="text-muted-foreground">无法加载岗位信息</p>;
  }

  const hasSalary = job.salary_min != null || job.salary_max != null;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">{job.title}</h3>
        <div className="flex items-center gap-2 mt-1">
          <JobStatusBadge status={job.status} />
          {job.location && (
            <span className="text-sm text-muted-foreground flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {job.location}
            </span>
          )}
          {job.work_type && (
            <span className="text-sm text-muted-foreground">
              {WORK_TYPE_LABELS[job.work_type] ?? job.work_type}
            </span>
          )}
        </div>
      </div>

      {hasSalary && (
        <p className="text-primary font-bold">
          {job.salary_min != null ? `${job.salary_min}k` : ""}
          {job.salary_min != null && job.salary_max != null ? " - " : ""}
          {job.salary_max != null ? `${job.salary_max}k` : ""}
        </p>
      )}

      {job.skills_required.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {job.skills_required.map((skill) => (
            <Badge key={skill} variant="secondary">{skill}</Badge>
          ))}
        </div>
      )}

      {job.description && (
        <div>
          <h4 className="text-sm font-medium mb-1">岗位描述</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-line">{job.description}</p>
        </div>
      )}

      {job.requirements && (
        <div>
          <h4 className="text-sm font-medium mb-1">任职要求</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-line">{job.requirements}</p>
        </div>
      )}

      <div className="text-xs text-muted-foreground space-y-0.5">
        <p>发布时间：{new Date(job.created_at).toLocaleString()}</p>
        <p>更新时间：{new Date(job.updated_at).toLocaleString()}</p>
      </div>
    </div>
  );
}

export default function JobDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);
  const [closeTarget, setCloseTarget] = useState<Job | null>(null);
  const [detailTarget, setDetailTarget] = useState<string | null>(null);

  const { data: jobs = [], isLoading, isError, refetch } = useRecruiterJobsQuery(user?.id);
  const updateStatusMutation = useUpdateJobStatusMutation();
  const deleteJobMutation = useDeleteJobMutation();

  // Compute stats from jobs array
  const activeJobs = jobs.filter((j) => j.status === "active").length;
  const closedJobs = jobs.filter((j) => j.status === "closed").length;
  const totalApplications = jobs.reduce((sum, j) => sum + (j.applications_count ?? 0), 0);

  useEffect(() => {
    setBreadcrumbItems([{ label: "首页", href: "/dashboard" }, { label: "我的岗位" }]);
  }, [setBreadcrumbItems]);

  const handleCloseJob = async () => {
    if (!closeTarget) return;
    try {
      await updateStatusMutation.mutateAsync({ jobId: closeTarget.id, status: "closed" });
      toast.success("岗位已关闭");
      setCloseTarget(null);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "关闭岗位失败"));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteJobMutation.mutateAsync(deleteTarget.id);
      toast.success("岗位已删除");
      setDeleteTarget(null);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "删除失败"));
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">我的岗位</h1>
        {/* Skeleton stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
        {/* Skeleton table rows */}
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return <ErrorState message="获取岗位列表失败" onRetry={refetch} />;
  }

  if (jobs.length === 0) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">我的岗位</h1>
        <EmptyState
          icon={Briefcase}
          message="暂未发布岗位"
          action={{ label: "发布新岗位", onClick: () => navigate("/dashboard/post") }}
        />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">我的岗位</h1>

      {/* Stat cards row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard icon={Briefcase} value={activeJobs} label="在线岗位" iconColor="text-blue-600" />
        <StatCard icon={XCircle} value={closedJobs} label="已关闭岗位" iconColor="text-slate-500" />
        <StatCard icon={Users} value={totalApplications} label="总申请数" iconColor="text-green-600" />
        {/* TODO: compute from jobs data filtered by created_at within last 7 days */}
        <StatCard icon={TrendingUp} value={0} label="本周新增" iconColor="text-amber-600" />
      </div>

      {/* Job table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>岗位名称</TableHead>
              <TableHead className="w-[100px]">岗位编号</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-center">申请人数</TableHead>
              <TableHead className="text-center w-[90px]">进面人数</TableHead>
              <TableHead className="text-center w-[90px]">招聘人数</TableHead>
              <TableHead>发布时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell className="font-medium">{job.title}</TableCell>
                <TableCell className="font-mono text-muted-foreground text-sm">
                  {job.job_code}
                </TableCell>
                <TableCell>
                  <JobStatusBadge status={job.status} />
                </TableCell>
                <TableCell className="text-center">
                  {job.applications_count ?? 0}
                </TableCell>
                <TableCell className="text-center">{job.interview_quota}</TableCell>
                <TableCell className="text-center">{job.head_count}</TableCell>
                <TableCell>
                  {new Date(job.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => setDetailTarget(job.id)}>
                        <FileText className="h-4 w-4 mr-2" />
                        查看详情
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => navigate(`/dashboard/applicants/${job.id}`)}>
                        <Eye className="h-4 w-4 mr-2" />
                        查看申请人
                      </DropdownMenuItem>
                      {job.status === "active" && (
                        <DropdownMenuItem onClick={() => setCloseTarget(job)}>
                          <Power className="h-4 w-4 mr-2" />
                          关闭岗位
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => setDeleteTarget(job)}
                      >
                        <XCircle className="h-4 w-4 mr-2" />
                        删除
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Close job confirmation dialog */}
      <Dialog open={!!closeTarget} onOpenChange={() => setCloseTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认关闭岗位</DialogTitle>
            <DialogDescription>
              确定要关闭岗位「{closeTarget?.title}」吗？关闭后将不再接受新的投递。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseTarget(null)}>
              取消
            </Button>
            <Button onClick={handleCloseJob} disabled={updateStatusMutation.isPending}>
              确认关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要永久删除岗位「{deleteTarget?.title}」吗？此操作无法撤销，相关投递记录也会被删除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteJobMutation.isPending}
            >
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Job detail dialog */}
      <Dialog open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>岗位详情</DialogTitle>
            <DialogDescription>查看已发布岗位的完整信息</DialogDescription>
          </DialogHeader>
          {detailTarget && <JobDetailContent jobId={detailTarget} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
