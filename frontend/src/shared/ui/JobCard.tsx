import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Job } from "@/features/jobs/types/job";

const WORK_TYPE_LABELS: Record<string, string> = {
  remote: "远程",
  onsite: "现场",
  hybrid: "混合",
};

interface JobCardProps {
  job: Job;
  applied?: boolean;
}

export function JobCard({ job, applied = false }: JobCardProps) {
  const hasSalary = job.salary_min != null || job.salary_max != null;
  const locationParts = [job.recruiter_name, job.location].filter(Boolean);

  return (
    <Card className="h-full shadow-sm hover:shadow-md transition-shadow duration-200 relative">
      {applied && (
        <div className="absolute top-3 right-3">
          <Badge className="bg-green-100 text-green-800 hover:bg-green-100/80">已投递</Badge>
        </div>
      )}
      <Link to={`/jobs/${job.id}`} className="block hover:no-underline">
        <CardContent className="p-6">
          <h3 className="text-lg font-semibold">{job.title}</h3>
          <p className="text-sm text-muted-foreground mt-1">
            {locationParts.join(" · ")}
            {job.work_type && ` · ${WORK_TYPE_LABELS[job.work_type] ?? job.work_type}`}
          </p>
          {hasSalary && (
            <p className="text-primary font-bold mt-2">
              {job.salary_min != null ? `${job.salary_min}k` : ""}
              {job.salary_min != null && job.salary_max != null ? " - " : ""}
              {job.salary_max != null ? `${job.salary_max}k` : ""}
            </p>
          )}
          {job.skills_required.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {job.skills_required.slice(0, 3).map((skill) => (
                <Badge key={skill} variant="secondary">
                  {skill}
                </Badge>
              ))}
              {job.skills_required.length > 3 && (
                <Badge variant="outline">+{job.skills_required.length - 3}</Badge>
              )}
            </div>
          )}
          {job.description && (
            <p className="text-sm text-muted-foreground mt-3 line-clamp-2">
              {job.description}
            </p>
          )}
        </CardContent>
      </Link>
      <div className="px-6 pb-4">
        {applied ? (
          <Button variant="secondary" className="w-full" disabled>
            已投递
          </Button>
        ) : (
          <Button asChild className="w-full">
            <Link to={`/apply/${job.id}`}>
              立即投递
            </Link>
          </Button>
        )}
      </div>
    </Card>
  );
}
