import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
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
              className="hover:shadow-md transition-shadow duration-200"
            >
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3
                      className="text-lg font-semibold cursor-pointer hover:text-primary transition-colors truncate"
                      onClick={() => navigate(`/jobs/${app.job_id}`)}
                    >
                      {app.job_title}
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
    </div>
  );
}
