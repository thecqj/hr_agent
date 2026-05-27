import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { LogOut, FileText, Briefcase } from "lucide-react";

interface Application {
  id: string;
  job_id: string;
  job_title: string;
  company_name?: string;
  resume_text: string;
  cover_letter?: string;
  match_score: number | null;
  status: string;
  created_at: string;
}

const STATUS_MAP: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "待查看", variant: "outline" },
  reviewed: { label: "已查看", variant: "secondary" },
  interview: { label: "面试中", variant: "default" },
  rejected: { label: "不合适", variant: "destructive" },
  hired: { label: "已录用", variant: "default" },
};

export default function MyApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const { clearAuth } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    let ignore = false;
    const fetchApplications = async () => {
      try {
        const res = await apiClient.get("/applications/my");
        if (!ignore) setApplications(res.data.items);
      } catch {
        if (!ignore) toast.error("获取投递记录失败");
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    fetchApplications();
    return () => { ignore = true; };
  }, []);

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 导航栏（与岗位市场一致） */}
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

      {/* 内容 */}
      <main className="container mx-auto p-6">
        <div className="flex items-center gap-2 mb-6">
          <FileText className="w-6 h-6" />
          <h2 className="text-3xl font-bold">我的投递</h2>
        </div>

        {loading ? (
          <p className="text-center py-10">加载中...</p>
        ) : applications.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-xl text-muted-foreground">你还没有投递过简历</p>
            <Button className="mt-4" onClick={() => navigate("/jobs")}>
              去看看岗位
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {applications.map((app) => (
              <Card key={app.id} className="hover:shadow-lg">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <CardTitle
                      className="text-lg cursor-pointer hover:underline"
                      onClick={() => navigate(`/jobs/${app.job_id}`)}
                    >
                      {app.job_title}
                    </CardTitle>
                    <Badge variant={STATUS_MAP[app.status]?.variant || "outline"}>
                      {STATUS_MAP[app.status]?.label || app.status}
                    </Badge>
                  </div>
                  {app.company_name && (
                    <p className="text-sm text-muted-foreground mt-1">{app.company_name}</p>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">匹配度</span>
                    <span className="font-semibold">
                      {app.match_score != null
                        ? `${Math.round(app.match_score * 100)}%`
                        : "未评估"}
                    </span>
                  </div>
                  <Separator className="my-2" />
                  <div className="text-sm text-muted-foreground">
                    投递时间：{new Date(app.created_at).toLocaleDateString()}
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/jobs/${app.job_id}`)}
                    >
                      查看岗位
                    </Button>
                    {/* 可以添加一个查看简历详情的弹窗，此处省略 */}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}