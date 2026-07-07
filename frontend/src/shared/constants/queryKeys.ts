export const queryKeys = {
  jobs: {
    all: ["jobs"] as const,
    list: (params?: object) => ["jobs", "list", params ?? {}] as const,
    detail: (id: string) => ["jobs", "detail", id] as const,
    recruiterList: (recruiterId?: string) => ["jobs", "recruiter", recruiterId ?? ""] as const,
  },
  applications: {
    mine: (params?: object) => ["applications", "mine", params ?? {}] as const,
    byJob: (jobId: string) => ["applications", "job", jobId] as const,
  },
  resumes: {
    all: ["resumes"] as const,
    list: (params?: object) => ["resumes", "list", params ?? {}] as const,
    detail: (id: string) => ["resumes", "detail", id] as const,
    mine: (params?: object) => ["resumes", "mine", params ?? {}] as const,
  },
  evaluation: {
    task: (taskId: string) => ["evaluation", "task", taskId] as const,
  },
} as const;
