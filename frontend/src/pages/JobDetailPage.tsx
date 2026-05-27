import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import type { Job } from "@/types/job";
import axios from "axios";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [job, setJob] = useState<Job | null>(null);

  const isRecruiter = user?.role === "recruiter";

  useEffect(() => {
    let ignore = false;

    const fetchJob = async () => {
      try {
        const res = await apiClient.get(`/jobs/${id}`);
        if (!ignore) setJob(res.data);
      } catch {
        if (!ignore) {
          toast.error("岗位不存在或已删除");
          navigate("/jobs");
        }
      }
    };

    fetchJob();

    return () => {
      ignore = true;
    };
  }, [id]);

  const handleApply = () => navigate(`/apply/${id}`);

  const handleStatusChange = async (newStatus: string) => {
    try {
      await apiClient.patch(`/jobs/${id}/status`, {
        status: newStatus,
      });
      toast.success("状态更新成功");
      const res = await apiClient.get(`/jobs/${id}`);
      setJob(res.data);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail || "状态更新失败"
        : "状态更新失败";
      toast.error(msg);
    }
  };

  if (!job) return <div className="text-center py-8">加载中...</div>;

  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">{job.title}</CardTitle>
          <div className="text-sm text-muted-foreground">
            {job.location && `${job.location} · `}{job.work_type}
          </div>
          <div className="flex gap-2 mt-2">
            {job.skills_required?.map((skill: string) => (
              <Badge key={skill} variant="secondary">{skill}</Badge>
            ))}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="whitespace-pre-wrap">{job.description}</p>
          <Separator />
          {(job.salary_min || job.salary_max) && (
            <p className="text-sm font-medium">
              薪资范围：{job.salary_min ? `${job.salary_min}K` : "不限"} - {job.salary_max ? `${job.salary_max}K` : "不限"}
            </p>
          )}
          <Separator />

          <div className="flex flex-wrap gap-2 items-center">
            {!isRecruiter && (
              <Button onClick={handleApply}>投递简历</Button>
            )}

            {isRecruiter && (
              <>
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

              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}