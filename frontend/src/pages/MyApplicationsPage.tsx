import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, MapPin } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
import type { MyApplication } from "@/features/applications/types/application";
import { useMyApplicationsQuery } from "@/features/applications/hooks/useApplications";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { CategoryTabs } from "@/shared/ui/CategoryTabs";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const STATUS_CATEGORIES = [
  { key: "all" as const, label: "全部" },
  ...Object.entries(APPLICATION_STATUS_MAP).map(([key, val]) => ({
    key: key as ApplicationStatus,
    label: val.label,
  })),
];

export default function MyApplicationsPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [detailTarget, setDetailTarget] = useState<MyApplication | null>(null);
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbItems([{ label: "我的投递" }]);
  }, [setBreadcrumbItems]);

  const params = {
    ...(statusFilter !== "all" ? { status: statusFilter as ApplicationStatus } : {}),
  };

  const { data, isLoading, isError, refetch } = useMyApplicationsQuery(params);
  const applications = data?.items ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">我的投递</h1>

      {/* Status filter tabs */}
      <div className="mb-6">
        <CategoryTabs
          categories={STATUS_CATEGORIES}
          activeKey={statusFilter}
          onSelect={setStatusFilter}
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState message="获取投递记录失败" onRetry={refetch} />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          message="暂无投递记录"
          action={{ label: "去看看岗位", onClick: () => navigate("/jobs") }}
        />
      ) : (
        <div className="space-y-4">
          {applications.map((app) => (
            <Card
              key={app.id}
              className="hover:shadow-md transition-shadow duration-200 cursor-pointer"
              onClick={() => setDetailTarget(app)}
            >
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold truncate">
                      {app.job_title || "未知岗位"}
                    </h3>
                    {app.company_name && (
                      <p className="text-sm text-muted-foreground mt-1">{app.company_name}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">
                      投递时间：{new Date(app.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="ml-4 shrink-0">
                    <StatusBadge status={app.status} />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Application detail dialog */}
      <Dialog open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>投递详情</DialogTitle>
            <DialogDescription>查看投递的详细信息</DialogDescription>
          </DialogHeader>
          {detailTarget && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold">
                  {detailTarget.job_title || "未知岗位"}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <StatusBadge status={detailTarget.status} />
                  {detailTarget.company_name && (
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {detailTarget.company_name}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">投递时间</h4>
                <p className="text-sm text-muted-foreground">
                  {new Date(detailTarget.created_at).toLocaleString()}
                </p>
              </div>

              {detailTarget.resume_text && (
                <div>
                  <h4 className="text-sm font-medium mb-1">简历摘要</h4>
                  <p className="text-sm text-muted-foreground line-clamp-6 whitespace-pre-line">
                    {detailTarget.resume_text}
                  </p>
                </div>
              )}

              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setDetailTarget(null);
                  navigate(`/jobs/${detailTarget.job_id}`);
                }}
              >
                查看岗位详情
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
