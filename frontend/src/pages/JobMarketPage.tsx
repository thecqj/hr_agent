import { useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { WorkType } from "@/features/jobs/types/job";
import { useJobsQuery } from "@/features/jobs/hooks/useJobs";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import LoadingState from "@/shared/ui/feedback/LoadingState";

export default function JobMarketPage() {
  const [keyword, setKeyword] = useState("");
  const [workType, setWorkType] = useState<string>("all");

  const params = {
    ...(keyword ? { keyword } : {}),
    ...(workType !== "all" ? { work_type: workType as WorkType } : {}),
  };

  const { data, isLoading, isError, refetch } = useJobsQuery(params);
  const jobs = data?.items ?? [];

  return (
    <main className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">岗位市场</h1>

        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="flex-1">
            <Input
              placeholder="搜索岗位名称或描述..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </div>
          <div className="w-40">
            <Select value={workType} onValueChange={(v) => setWorkType(v)}>
              <SelectTrigger>
                <SelectValue placeholder="工作类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="remote">远程</SelectItem>
                <SelectItem value="onsite">现场</SelectItem>
                <SelectItem value="hybrid">混合</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState message="获取岗位列表失败" onRetry={refetch} />
        ) : jobs.length === 0 ? (
          <EmptyState message="暂无岗位" />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <Link to={`/jobs/${job.id}`} key={job.id} className="block hover:no-underline">
                <Card className="h-full hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <CardTitle className="text-xl">{job.title}</CardTitle>
                    <div className="text-sm text-muted-foreground">
                      {job.location && `${job.location} · `}
                      {job.work_type}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1 mb-3">
                      {job.skills_required?.slice(0, 3).map((skill) => (
                        <Badge key={skill} variant="secondary">
                          {skill}
                        </Badge>
                      ))}
                      {job.skills_required?.length > 3 && (
                        <Badge variant="outline">+{job.skills_required.length - 3}</Badge>
                      )}
                    </div>
                    <p className="text-sm line-clamp-3">{job.description}</p>
                    {(job.salary_min || job.salary_max) && (
                      <p className="text-sm mt-2 font-medium">
                        {job.salary_min && `${job.salary_min}K`}
                        {job.salary_min && job.salary_max && " - "}
                        {job.salary_max && `${job.salary_max}K`}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
  );
}
