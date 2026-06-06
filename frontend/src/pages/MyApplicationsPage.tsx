import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useLogout } from "@/features/auth/hooks/useLogout";
import { useMyApplicationsQuery } from "@/features/applications/hooks/useApplications";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import LoadingState from "@/shared/ui/feedback/LoadingState";
import SeekerHeader from "@/shared/ui/layout/SeekerHeader";

export default function MyApplicationsPage() {
  const navigate = useNavigate();
  const logout = useLogout();

  const { data, isLoading, isError, refetch } = useMyApplicationsQuery();
  const applications = data?.items ?? [];

  return (
    <div className="min-h-screen bg-gray-50">
      <SeekerHeader onNavigate={navigate} onLogout={logout} />

      <main className="container mx-auto p-6">
        <div className="flex items-center gap-2 mb-6">
          <FileText className="w-6 h-6" />
          <h2 className="text-3xl font-bold">我的投递</h2>
        </div>

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState message="获取投递记录失败" onRetry={refetch} />
        ) : applications.length === 0 ? (
          <div className="text-center py-20">
            <EmptyState message="你还没有投递过简历" />
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
                    <Badge variant={APPLICATION_STATUS_MAP[app.status].variant}>
                      {APPLICATION_STATUS_MAP[app.status].label}
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
                      {app.match_score != null ? `${Math.round(app.match_score * 100)}%` : "未评估"}
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
