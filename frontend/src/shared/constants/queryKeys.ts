export const queryKeys = {
  jobs: {
    all: ["jobs"] as const,
    list: (params?: object) => ["jobs", "list", params ?? {}] as const,
    detail: (id: string) => ["jobs", "detail", id] as const,
    recruiterList: (recruiterId?: string) => ["jobs", "recruiter", recruiterId ?? ""] as const,
  },
  applications: {
    mine: ["applications", "mine"] as const,
    byJob: (jobId: string) => ["applications", "job", jobId] as const,
  },
};
