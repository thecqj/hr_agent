import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { LogOut, Briefcase } from "lucide-react";
import type { Job } from "@/types/job";

export default function JobMarketPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [keyword, setKeyword] = useState("");
  const [workType, setWorkType] = useState<string>("all");
  const [loading, setLoading] = useState(false);
  const { clearAuth } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    let ignore = false;
    const fetchJobs = async () => {
      setLoading(true);
      try {
        const params: Record<string, string> = {};
        if (keyword) params.keyword = keyword;
        if (workType && workType !== "all") params.work_type = workType;
        const res = await apiClient.get("/jobs/", { params });
        if (!ignore) setJobs(res.data.items);
      } catch {
        if (!ignore) toast.error("获取岗位列表失败");
      } finally {
        if (!ignore) setLoading(false);
      }
    };

    fetchJobs();
    return () => { ignore = true; };
  }, [keyword, workType]);

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ========== 求职者导航栏 ========== */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-6 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-primary" />
            <h1 className="text-xl font-bold text-primary">智能投递</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate("/jobs")}>
              岗位市场
            </Button>
            <Button variant="ghost" onClick={() => navigate("/my-applications")}>
              我的投递
            </Button>
            <Button variant="ghost" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              退出登录
            </Button>
          </div>
        </div>
      </header>

      {/* ========== 内容区 ========== */}
      <main className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">岗位市场</h1>

        {/* 搜索与筛选区域 */}
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

        {/* 岗位列表 */}
        {loading ? (
          <p>加载中...</p>
        ) : jobs.length === 0 ? (
          <p className="text-muted-foreground">暂无岗位</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <Link to={`/jobs/${job.id}`} key={job.id} className="block hover:no-underline">
                <Card className="h-full hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <CardTitle className="text-xl">{job.title}</CardTitle>
                    <div className="text-sm text-muted-foreground">
                      {job.location && `${job.location} · `}{job.work_type}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1 mb-3">
                      {job.skills_required?.slice(0, 3).map((skill) => (
                        <Badge key={skill} variant="secondary">{skill}</Badge>
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
    </div>
  );
}