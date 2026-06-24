import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Briefcase,
  Eye,
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

export default function JobDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);
  const [closeTarget, setCloseTarget] = useState<Job | null>(null);

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
              <TableHead>状态</TableHead>
              <TableHead className="text-center">申请人数</TableHead>
              <TableHead>发布时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell className="font-medium">{job.title}</TableCell>
                <TableCell>
                  <JobStatusBadge status={job.status} />
                </TableCell>
                <TableCell className="text-center">
                  {job.applications_count ?? 0}
                </TableCell>
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
    </div>
  );
}
