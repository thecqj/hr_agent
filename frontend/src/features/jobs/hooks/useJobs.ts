import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createJob, deleteJob, evaluateJob, getJobById, getJobs, updateJobStatus } from "@/features/jobs/api/jobs";
import type { CreateJobPayload, Job, JobListParams, JobStatus } from "@/features/jobs/types/job";
import { queryKeys } from "@/shared/constants/queryKeys";

export function useJobsQuery(params: JobListParams = {}) {
  return useQuery({
    queryKey: queryKeys.jobs.list(params),
    queryFn: () => getJobs(params),
  });
}

export function useJobDetailQuery(jobId?: string) {
  return useQuery({
    queryKey: jobId ? queryKeys.jobs.detail(jobId) : ["jobs", "detail", "missing-id"],
    queryFn: () => getJobById(jobId!),
    enabled: Boolean(jobId),
  });
}

export function useRecruiterJobsQuery(recruiterId?: string) {
  return useQuery({
    queryKey: queryKeys.jobs.recruiterList(recruiterId),
    queryFn: async () => {
      const data = await getJobs({ status: "all" });
      if (!recruiterId) return [] as Job[];
      return data.items.filter((job) => job.recruiter_id === recruiterId);
    },
    enabled: Boolean(recruiterId),
  });
}

export function useUpdateJobStatusMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ jobId, status }: { jobId: string; status: JobStatus }) => updateJobStatus(jobId, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.detail(variables.jobId) });
    },
  });
}

export function useCreateJobMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateJobPayload) => createJob(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
    },
  });
}

export function useDeleteJobMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => deleteJob(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
      queryClient.removeQueries({ queryKey: queryKeys.jobs.detail(jobId) });
    },
  });
}

export function useEvaluateJobMutation() {
  return useMutation({
    mutationFn: (jobId: string) => evaluateJob(jobId),
  });
}
