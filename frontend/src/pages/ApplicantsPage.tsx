import { useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useUpdateApplicationStatusMutation, useApplicantsByJobQuery } from "@/features/applications/hooks/useApplications";
import type { Applicant } from "@/features/applications/types/application";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
import { getApiErrorMessage } from "@/shared/api/error";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import LoadingState from "@/shared/ui/feedback/LoadingState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export default function ApplicantsPage() {
  const { jobId } = useParams<{ jobId: string }>();

  const [selectedApplicant, setSelectedApplicant] = useState<Applicant | null>(null);

  const { data, isLoading, isError, refetch } = useApplicantsByJobQuery(jobId);
  const updateStatusMutation = useUpdateApplicationStatusMutation(jobId);
  const applicants = data?.items ?? [];

  const updateStatus = async (applicantId: string, newStatus: string) => {
    try {
      await updateStatusMutation.mutateAsync({
        applicantId,
        status: newStatus as any,
      });
      toast.success("状态已更新");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "状态更新失败"));
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "至今";
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <main>
      <h2 className="text-3xl font-bold mb-6">投递列表</h2>

        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState message="获取投递列表失败" onRetry={refetch} />
        ) : applicants.length === 0 ? (
          <EmptyState message="暂无投递记录" />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {applicants.map((app) => (
              <Card key={app.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle
                      className="text-lg cursor-pointer hover:underline"
                      onClick={() => setSelectedApplicant(app)}
                    >
                      {app.applicant_name}
                    </CardTitle>
                    <StatusBadge status={app.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <Select value={app.status} onValueChange={(v) => updateStatus(app.id, v)}>
                      <SelectTrigger className="w-32 h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pending">待查看</SelectItem>
                        <SelectItem value="reviewed">已查看</SelectItem>
                        <SelectItem value="interview">面试</SelectItem>
                        <SelectItem value="rejected">不合适</SelectItem>
                        <SelectItem value="hired">录用</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button variant="outline" size="sm" onClick={() => setSelectedApplicant(app)}>
                      查看简历
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Dialog open={!!selectedApplicant} onOpenChange={() => setSelectedApplicant(null)}>
          <DialogContent className="!max-w-6xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{selectedApplicant?.applicant_name} 的简历</DialogTitle>
              <DialogDescription>
                状态：{selectedApplicant ? APPLICATION_STATUS_MAP[selectedApplicant.status].label : "待查看"}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 text-sm">
              {selectedApplicant?.structured_resume ? (
                <>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">基本信息</h3>
                    <div className="grid grid-cols-2 gap-y-2 gap-x-6">
                      <div>
                        <span className="font-medium">姓名：</span>
                        {selectedApplicant.structured_resume.name}
                      </div>
                      <div>
                        <span className="font-medium">工作年限：</span>
                        {selectedApplicant.structured_resume.work_experience_years}年
                      </div>
                      {selectedApplicant.structured_resume.education_level && (
                        <div>
                          <span className="font-medium">最高学历：</span>
                          {selectedApplicant.structured_resume.education_level}
                        </div>
                      )}
                    </div>
                  </div>

                  {selectedApplicant.structured_resume.contact &&
                    Object.values(selectedApplicant.structured_resume.contact).some(Boolean) && (
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <h3 className="font-semibold mb-3 text-base border-b pb-2">联系方式</h3>
                        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                          {selectedApplicant.structured_resume.contact.phone && (
                            <div>
                              <span className="font-medium">📱 手机：</span>
                              {selectedApplicant.structured_resume.contact.phone}
                            </div>
                          )}
                          {selectedApplicant.structured_resume.contact.email && (
                            <div>
                              <span className="font-medium">✉️ 邮箱：</span>
                              {selectedApplicant.structured_resume.contact.email}
                            </div>
                          )}
                          {selectedApplicant.structured_resume.contact.wechat && (
                            <div>
                              <span className="font-medium">💬 微信：</span>
                              {selectedApplicant.structured_resume.contact.wechat}
                            </div>
                          )}
                          {selectedApplicant.structured_resume.contact.other && (
                            <div>
                              <span className="font-medium">🔗 其他：</span>
                              {selectedApplicant.structured_resume.contact.other}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                  {selectedApplicant.structured_resume.work_experience?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h3 className="font-semibold mb-3 text-base border-b pb-2">工作经历</h3>
                      {selectedApplicant.structured_resume.work_experience.map((exp, index) => (
                        <div key={index} className="mb-3 border-l-4 border-primary/30 pl-4">
                          <p className="font-semibold">{exp.company}</p>
                          <p className="text-sm text-muted-foreground">
                            {exp.position} &nbsp;|&nbsp; {formatDate(exp.start_date)} ~
                            {formatDate(exp.end_date)}
                          </p>
                          <p className="mt-1 text-gray-700">{exp.description}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedApplicant.structured_resume.project_experience?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h3 className="font-semibold mb-3 text-base border-b pb-2">项目经历</h3>
                      {selectedApplicant.structured_resume.project_experience.map((proj, index) => (
                        <div key={index} className="mb-3 border-l-4 border-primary/30 pl-4">
                          <p className="font-semibold">{proj.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {proj.role} &nbsp;|&nbsp; {formatDate(proj.start_date)} ~
                            {formatDate(proj.end_date)}
                          </p>
                          <p className="mt-1 text-gray-700">{proj.description}</p>
                          {proj.technologies?.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {proj.technologies.map((tech) => (
                                <Badge key={tech} variant="secondary" className="text-xs">
                                  {tech}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedApplicant.structured_resume.education?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h3 className="font-semibold mb-3 text-base border-b pb-2">教育经历</h3>
                      {selectedApplicant.structured_resume.education.map((edu, index) => (
                        <div key={index} className="flex justify-between items-center mb-2 border-b border-dashed pb-1">
                          <span>
                            <span className="font-medium">{edu.school}</span> · {edu.major} · {edu.degree}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(edu.start_date)} ~ {formatDate(edu.end_date)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedApplicant.structured_resume.certificates?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h3 className="font-semibold mb-3 text-base border-b pb-2">资格证书</h3>
                      <div className="flex flex-wrap gap-2">
                        {selectedApplicant.structured_resume.certificates.map((cert, index) => (
                          <Badge key={index} variant="outline" className="text-sm py-1 px-3">
                            {cert.name}
                            {cert.date ? ` (${cert.date})` : ""}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedApplicant.structured_resume.skills?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h3 className="font-semibold mb-3 text-base border-b pb-2">专业技能</h3>
                      <div className="flex flex-wrap gap-2">
                        {selectedApplicant.structured_resume.skills.map((skill, index) => (
                          <Badge
                            key={index}
                            variant="default"
                            className="bg-primary/20 text-primary-foreground hover:bg-primary/30 text-sm py-1 px-3"
                          >
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedApplicant.structured_resume.self_evaluation && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h3 className="font-semibold mb-3 text-base border-b pb-2">自我评价</h3>
                      <p className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                        {selectedApplicant.structured_resume.self_evaluation}
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <div>
                  <h3 className="font-semibold mb-2">简历内容（纯文本）</h3>
                  <p className="whitespace-pre-wrap text-sm">
                    {selectedApplicant?.resume_text || "无简历内容"}
                  </p>
                </div>
              )}

              {selectedApplicant?.cover_letter && (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold mb-2 text-base border-b pb-2">求职信</h3>
                  <p className="whitespace-pre-wrap text-sm">{selectedApplicant.cover_letter}</p>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </main>
  );
}
