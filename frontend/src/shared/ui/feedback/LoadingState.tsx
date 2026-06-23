import { Skeleton } from "@/components/ui/skeleton";

interface LoadingStateProps {
  message?: string;
  rows?: number;
}

export default function LoadingState({ rows = 3 }: LoadingStateProps) {
  return (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-24 w-full rounded-lg" />
      ))}
    </div>
  );
}
