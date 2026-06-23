import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from "@/features/auth/store/authStore";
import {
  useDeleteJobMutation,
  useRecruiterJobsQuery,
  useUpdateJobStatusMutation,
} from "@/features/jobs/hooks/useJobs";
import type { Job, JobStatus } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import LoadingState from "@/shared/ui/feedback/LoadingState";

export default function JobDashboardPage() {
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);
  const navigate = useNavigate();

  const { user } = useAuthStore();

  const { data: jobs = [], isLoading, isError, refetch } = useRecruiterJobsQuery(user?.id);
  const updateStatusMutation = useUpdateJobStatusMutation();
  const deleteJobMutation = useDeleteJobMutation();

  const handleStatusChange = async (jobId: string, newStatus: string) => {
    try {
      await updateStatusMutation.mutateAsync({
        jobId,
        status: newStatus as JobStatus,
      });
      toast.success("状态已更新");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "状态更新失败"));
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

  return (
    <main>
      {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState message="获取岗位列表失败" onRetry={refetch} />
        ) : jobs.length === 0 ? (
          <EmptyState message="你暂未发布岗位" />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <Card key={job.id} className="hover:shadow-lg">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <CardTitle
                      className="text-lg cursor-pointer"
                      onClick={() => navigate(`/jobs/${job.id}`)}
                    >
                      {job.title}
                    </CardTitle>
                    <Select value={job.status} onValueChange={(v) => handleStatusChange(job.id, v)}>
                      <SelectTrigger className="w-28 h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">活跃</SelectItem>
                        <SelectItem value="draft">草稿</SelectItem>
                        <SelectItem value="closed">关闭</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Badge variant={job.status === "active" ? "default" : "secondary"}>
                    {job.status === "active" ? "活跃" : job.status === "draft" ? "草稿" : "已关闭"}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    创建于 {new Date(job.created_at).toLocaleDateString()}
                  </p>
                  <div className="mt-2">
                    {job.applications_count != null && job.applications_count > 0 ? (
                      <p className="text-2xl font-bold">目前收到 {job.applications_count} 份简历</p>
                    ) : (
                      <p className="text-lg text-muted-foreground font-medium">暂未收到简历</p>
                    )}
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/dashboard/applicants/${job.id}`)}
                    >
                      查看申请
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setDeleteTarget(job)}
                    >
                      删除
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

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
    </main>
  );
}
