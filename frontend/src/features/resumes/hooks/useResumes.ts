import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  deleteResume,
  getResumeDetail,
  getResumeList,
  parseResume,
  updateResumeName,
  uploadResume,
} from "@/features/resumes/api/resumes";
import { queryKeys } from "@/shared/constants/queryKeys";
import { getApiErrorMessage } from "@/shared/api/error";

export function useResumeListQuery() {
  return useQuery({
    queryKey: queryKeys.resumes.list,
    queryFn: getResumeList,
  });
}

export function useResumeDetailQuery(id?: string) {
  return useQuery({
    queryKey: id ? queryKeys.resumes.detail(id) : ["resumes", "detail", "missing"],
    queryFn: () => getResumeDetail(id!),
    enabled: Boolean(id),
  });
}

export function useParseResumeMutation() {
  return useMutation({
    mutationFn: (file: File) => parseResume(file),
  });
}

export function useUploadResumeMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, name }: { file: File; name: string }) => uploadResume(file, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.list });
      toast.success("简历上传成功");
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, "简历上传失败"));
    },
  });
}

export function useUpdateResumeMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => updateResumeName(id, name),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.list });
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.detail(variables.id) });
      toast.success("简历名称已更新");
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, "更新失败"));
    },
  });
}

export function useDeleteResumeMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteResume(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.resumes.list });
      toast.success("简历已删除");
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, "删除失败"));
    },
  });
}
