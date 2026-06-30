import { useState } from "react";
import { ChevronDown, ChevronRight, FileText, MapPin, DollarSign, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { JobDetailCardData } from "@/features/chat/types/chat";

interface JobDetailCardProps {
  card: JobDetailCardData;
}

function CollapsibleSection({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t first:border-t-0">
      <button
        className="flex items-center gap-1.5 w-full py-2 text-sm font-medium text-left hover:text-primary"
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {title}
      </button>
      {open && <div className="pb-2 pl-5 text-sm text-muted-foreground whitespace-pre-wrap">{children}</div>}
    </div>
  );
}

const workTypeLabels: Record<string, string> = {
  remote: "远程",
  onsite: "坐班",
  hybrid: "混合",
};

export function JobDetailCard({ card }: JobDetailCardProps) {
  const { job } = card;

  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">{job.title}</span>
          <span className="font-mono text-xs text-muted-foreground">{job.job_code}</span>
        </div>

        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground mb-3">
          {job.location && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {job.location}
            </span>
          )}
          {job.salary_min != null && job.salary_max != null && (
            <span className="flex items-center gap-1">
              <DollarSign className="h-3 w-3" />
              {job.salary_min / 1000}k-{job.salary_max / 1000}k
            </span>
          )}
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            编制 {job.head_count} / 进面 {job.interview_quota}
          </span>
          <span>{workTypeLabels[job.work_type] || job.work_type}</span>
        </div>

        <CollapsibleSection title="岗位职责" defaultOpen>
          {job.description}
        </CollapsibleSection>

        <CollapsibleSection title="任职要求" defaultOpen>
          {job.requirements}
        </CollapsibleSection>

        <CollapsibleSection title="技能要求">
          <div className="flex flex-wrap gap-1.5">
            {job.skills_required.map((skill) => (
              <span key={skill} className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">
                {skill}
              </span>
            ))}
          </div>
        </CollapsibleSection>
      </CardContent>
    </Card>
  );
}
