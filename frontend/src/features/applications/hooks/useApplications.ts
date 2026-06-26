import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  confirmEvaluation,
  createApplication,
  getApplicationsByJob,
  getEvaluationTask,
  getMyApplications,
  updateApplicationStatus,
} from "@/features/applications/api/applications";
import type { ConfirmDecision } from "@/features/applications/api/applications";
import type { CreateApplicationPayload } from "@/features/applications/types/application";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";
import { queryKeys } from "@/shared/constants/queryKeys";

interface MyApplicationsParams {
  page?: number;
  page_size?: number;
  status?: ApplicationStatus;
}

export function useMyApplicationsQuery(params: MyApplicationsParams = {}, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.applications.mine(params),
    queryFn: () => getMyApplications(params),
    enabled: options?.enabled ?? true,
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
      queryClient.invalidateQueries({ queryKey: ["applications", "mine"] });
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
      queryClient.invalidateQueries({ queryKey: ["applications", "mine"] });
    },
  });
}

export function useEvaluationTaskQuery(taskId?: string) {
  return useQuery({
    queryKey: taskId ? queryKeys.evaluation.task(taskId) : ["evaluation", "task", "missing"],
    queryFn: () => getEvaluationTask(taskId!),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "running") return 2000;
      return false;
    },
  });
}

export function useConfirmEvaluationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ taskId, decisions }: { taskId: string; decisions: ConfirmDecision[] }) =>
      confirmEvaluation(taskId, decisions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluation"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}
