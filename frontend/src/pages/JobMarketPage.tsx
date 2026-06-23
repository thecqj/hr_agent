import { useEffect, useState } from "react";
import { Briefcase } from "lucide-react";

import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import type { WorkType } from "@/features/jobs/types/job";
import { useJobsQuery } from "@/features/jobs/hooks/useJobs";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { CategoryTabs } from "@/shared/ui/CategoryTabs";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { JobCard } from "@/shared/ui/JobCard";
import { SearchBar } from "@/shared/ui/SearchBar";

const WORK_TYPE_CATEGORIES: { key: string; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "remote", label: "远程" },
  { key: "onsite", label: "现场" },
  { key: "hybrid", label: "混合" },
];

const PAGE_SIZE = 9;

export default function JobMarketPage() {
  const [keyword, setKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [workType, setWorkType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbItems([{ label: "岗位市场" }]);
  }, [setBreadcrumbItems]);

  const params = {
    ...(keyword ? { keyword } : {}),
    ...(workType !== "all" ? { work_type: workType as WorkType } : {}),
    page,
    page_size: PAGE_SIZE,
  };

  const { data, isLoading, isError, refetch } = useJobsQuery(params);
  const jobs = data?.items ?? [];
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleSearch = () => {
    setKeyword(searchInput);
    setPage(1);
  };

  const handleWorkTypeChange = (key: string) => {
    setWorkType(key);
    setPage(1);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">岗位市场</h1>

      {/* Search bar */}
      <div className="mb-4">
        <SearchBar
          value={searchInput}
          onChange={setSearchInput}
          onSearch={handleSearch}
          placeholder="搜索岗位名称或描述..."
        />
      </div>

      {/* Category filter tabs */}
      <div className="mb-6">
        <CategoryTabs
          categories={WORK_TYPE_CATEGORIES}
          activeKey={workType}
          onSelect={handleWorkTypeChange}
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-40 w-full rounded-lg" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <ErrorState message="获取岗位列表失败" onRetry={refetch} />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          message="暂无匹配岗位"
          action={{ label: "清除筛选", onClick: () => { setWorkType("all"); setKeyword(""); setSearchInput(""); setPage(1); } }}
        />
      ) : (
        <>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8">
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      text="上一页"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
                    .map((p, i, arr) => (
                      <PaginationItem key={p}>
                        {i > 0 && arr[i - 1] < p - 1 && (
                          <span className="px-1 text-muted-foreground">...</span>
                        )}
                        <PaginationLink
                          isActive={p === page}
                          onClick={() => setPage(p)}
                          className="cursor-pointer"
                        >
                          {p}
                        </PaginationLink>
                      </PaginationItem>
                    ))}
                  <PaginationItem>
                    <PaginationNext
                      text="下一页"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      className={page >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </>
      )}
    </div>
  );
}
