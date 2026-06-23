import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Job } from "@/features/jobs/types/job";

interface JobCardProps {
  job: Job;
  onClick?: () => void;
}

export function JobCard({ job, onClick }: JobCardProps) {
  const hasSalary = job.salary_min != null || job.salary_max != null;
  const locationParts = [job.recruiter_name, job.location].filter(Boolean);

  return (
    <Card
      className="shadow-sm hover:shadow-md transition-shadow duration-200 cursor-pointer"
      onClick={onClick}
    >
      <CardContent className="p-6">
        <h3 className="text-lg font-semibold">{job.title}</h3>
        {locationParts.length > 0 && (
          <p className="text-sm text-muted-foreground mt-1">
            {locationParts.join(" · ")}
          </p>
        )}
        {hasSalary && (
          <p className="text-primary font-bold mt-2">
            {job.salary_min != null ? `${job.salary_min}k` : ""}
            {job.salary_min != null && job.salary_max != null ? " - " : ""}
            {job.salary_max != null ? `${job.salary_max}k` : ""}
          </p>
        )}
        {job.skills_required.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {job.skills_required.map((skill) => (
              <Badge key={skill} variant="secondary">
                {skill}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
