import { ArrowLeft } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

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
import { Separator } from "@/components/ui/separator";
import { useLogout } from "@/features/auth/hooks/useLogout";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useJobDetailQuery, useUpdateJobStatusMutation } from "@/features/jobs/hooks/useJobs";
import type { JobStatus } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import LoadingState from "@/shared/ui/feedback/LoadingState";
import RecruiterHeader from "@/shared/ui/layout/RecruiterHeader";
import SeekerHeader from "@/shared/ui/layout/SeekerHeader";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const logout = useLogout();
  const { user } = useAuthStore();
  const isRecruiter = user?.role === "recruiter";
  const fallbackPath = isRecruiter ? "/dashboard" : "/jobs";

  const { data: job, isLoading, isError, refetch } = useJobDetailQuery(id);
  const statusMutation = useUpdateJobStatusMutation();

  const handleApply = () => navigate(`/apply/${id}`);

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }
    navigate(fallbackPath);
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!id) return;
    try {
      await statusMutation.mutateAsync({
        jobId: id,
        status: newStatus as JobStatus,
      });
      toast.success("状态更新成功");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "状态更新失败"));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {isRecruiter ? (
        <RecruiterHeader onNavigate={navigate} onLogout={logout} />
      ) : (
        <SeekerHeader onNavigate={navigate} onLogout={logout} />
      )}

      <main className="container mx-auto p-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Button variant="ghost" size="sm" className="-ml-2" onClick={handleBack}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            返回上一页
          </Button>
          <Button variant="outline" size="sm" onClick={() => navigate(fallbackPath)}>
            {isRecruiter ? "回到我的岗位" : "返回岗位市场"}
          </Button>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : isError || !job ? (
          <ErrorState
            message="岗位不存在或已删除"
            onRetry={async () => {
              const result = await refetch();
              if (result.isError) navigate(fallbackPath);
            }}
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">{job.title}</CardTitle>
              <div className="text-sm text-muted-foreground">
                {job.location && `${job.location} · `}
                {job.work_type}
              </div>
              <div className="mt-2 flex gap-2">
                {job.skills_required?.map((skill: string) => (
                  <Badge key={skill} variant="secondary">
                    {skill}
                  </Badge>
                ))}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="whitespace-pre-wrap">{job.description}</p>
              <Separator />
              {(job.salary_min || job.salary_max) && (
                <p className="text-sm font-medium">
                  薪资范围：{job.salary_min ? `${job.salary_min}K` : "不限"} -
                  {job.salary_max ? `${job.salary_max}K` : "不限"}
                </p>
              )}
              <Separator />

              <div className="flex flex-wrap items-center gap-2">
                {!isRecruiter && <Button onClick={handleApply}>投递简历</Button>}

                {isRecruiter && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm">当前状态：</span>
                    <Select value={job.status} onValueChange={handleStatusChange}>
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">活跃</SelectItem>
                        <SelectItem value="draft">草稿</SelectItem>
                        <SelectItem value="closed">关闭</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
