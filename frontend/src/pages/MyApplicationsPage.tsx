import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMyApplicationsQuery } from "@/features/applications/hooks/useApplications";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import LoadingState from "@/shared/ui/feedback/LoadingState";

export default function MyApplicationsPage() {
  const navigate = useNavigate();

  const { data, isLoading, isError, refetch } = useMyApplicationsQuery();
  const applications = data?.items ?? [];

  return (
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
                  <p className="text-sm text-muted-foreground mb-4">
                    投递时间：{new Date(app.created_at).toLocaleDateString()}
                  </p>
                  <div className="flex gap-2">
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
  );
}
