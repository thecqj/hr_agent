import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, MapPin, Building2, Coins } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useMyApplicationsQuery } from "@/features/applications/hooks/useApplications";
import { useJobDetailQuery, useUpdateJobStatusMutation } from "@/features/jobs/hooks/useJobs";
import type { JobStatus } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import ErrorState from "@/shared/ui/feedback/ErrorState";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isRecruiter = user?.role === "recruiter";
  const fallbackPath = isRecruiter ? "/dashboard" : "/jobs";

  const { data: job, isLoading, isError, refetch } = useJobDetailQuery(id);
  const statusMutation = useUpdateJobStatusMutation();
  const isJobSeeker = user?.role === "job_seeker";
  const { data: applicationsData } = useMyApplicationsQuery(
    { page: 1, page_size: 100 },
    { enabled: isJobSeeker }
  );
  const myApplication = isJobSeeker
    ? (applicationsData?.items ?? []).find((app) => app.job_id === id)
    : undefined;
  const hasApplied = myApplication != null;
  const isRejected = myApplication?.status === "rejected";
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    if (job) {
      setBreadcrumbItems([
        { label: "岗位市场", href: "/jobs" },
        { label: job.title },
      ]);
    } else {
      setBreadcrumbItems([
        { label: "岗位市场", href: "/jobs" },
        { label: "岗位详情" },
      ]);
    }
  }, [job, setBreadcrumbItems]);

  const handleApply = () => navigate(`/apply/${id}`);

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

  if (isLoading) {
    return (
      <div className="max-w-7xl">
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-5 w-32" />
          <div className="flex gap-2 mt-3">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
          <Separator />
          <Skeleton className="h-40 w-full" />
          <Separator />
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div className="max-w-7xl">
        <ErrorState
          message="岗位不存在或已删除"
          onRetry={async () => {
            const result = await refetch();
            if (result.isError) navigate(fallbackPath);
          }}
        />
      </div>
    );
  }

  const hasSalary = job.salary_min != null || job.salary_max != null;

  return (
    <div className="max-w-7xl">
      {/* Back link */}
      <button
        onClick={() => navigate(fallbackPath)}
        className="inline-flex items-center text-primary hover:underline text-sm mb-6"
      >
        <ArrowLeft className="mr-1 h-4 w-4" />
        返回岗位市场
      </button>

      {/* Header section */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{job.title}</h1>
        <p className="text-sm text-muted-foreground font-mono">{job.job_code}</p>
        <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-muted-foreground">
          {job.recruiter_name && (
            <span className="inline-flex items-center gap-1">
              <Building2 className="h-4 w-4" />
              {job.recruiter_name}
            </span>
          )}
          {job.location && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              {job.location}
            </span>
          )}
          <span>{job.work_type === "remote" ? "远程" : job.work_type === "onsite" ? "现场" : "混合"}</span>
        </div>
        {hasSalary && (
          <p className="text-primary font-bold text-lg mt-2 inline-flex items-center gap-1">
            <Coins className="h-4 w-4" />
            {job.salary_min != null ? `${job.salary_min}k` : "不限"} - {job.salary_max != null ? `${job.salary_max}k` : "不限"}
          </p>
        )}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {job.skills_required?.map((skill: string) => (
            <Badge key={skill} variant="secondary">
              {skill}
            </Badge>
          ))}
        </div>
      </div>

      {/* Content sections */}
      <Card className="shadow-sm hover:shadow-md transition-shadow duration-200">
        <CardContent className="p-6 space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-3">岗位描述</h2>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{job.description}</p>
          </div>

          <Separator />

          <div>
            <h2 className="text-xl font-semibold mb-3">任职要求</h2>
            {job.requirements ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{job.requirements}</p>
            ) : job.skills_required.length > 0 ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                熟悉或掌握以下技能：{job.skills_required.join("、")}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">暂无具体要求</p>
            )}
          </div>

          <Separator />

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-3">
            {!isRecruiter && (
              isRejected ? (
                <Button size="lg" variant="destructive" disabled>
                  已拒绝
                </Button>
              ) : hasApplied ? (
                <Button size="lg" variant="secondary" disabled>
                  已投递
                </Button>
              ) : (
                <Button size="lg" onClick={handleApply}>
                  立即投递
                </Button>
              )
            )}
            {isRecruiter && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">当前状态：</span>
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
    </div>
  );
}
