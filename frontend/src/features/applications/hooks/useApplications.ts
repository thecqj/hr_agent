import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createApplication,
  getApplicationsByJob,
  getMyApplications,
  updateApplicationStatus,
} from "@/features/applications/api/applications";
import type { CreateApplicationPayload } from "@/features/applications/types/application";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";
import { queryKeys } from "@/shared/constants/queryKeys";

export function useMyApplicationsQuery() {
  return useQuery({
    queryKey: queryKeys.applications.mine,
    queryFn: getMyApplications,
  });
}

export function useApplicantsByJobQuery(jobId?: string) {
  return useQuery({
    queryKey: jobId ? queryKeys.applications.byJob(jobId) : ["applications", "job", "missing-id"],
    queryFn: () => getApplicationsByJob(jobId!),
    enabled: Boolean(jobId),
  });
}

export function useCreateApplicationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ payload, force }: { payload: CreateApplicationPayload; force?: boolean }) =>
      createApplication(payload, force),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications.mine });
      if (variables.payload.job_id) {
        queryClient.invalidateQueries({ queryKey: queryKeys.applications.byJob(variables.payload.job_id) });
      }
    },
  });
}

export function useUpdateApplicationStatusMutation(jobId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ applicantId, status }: { applicantId: string; status: ApplicationStatus }) =>
      updateApplicationStatus(applicantId, status),
    onSuccess: () => {
      if (jobId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.applications.byJob(jobId) });
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.applications.mine });
    },
  });
}
