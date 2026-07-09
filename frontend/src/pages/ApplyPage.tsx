import { useEffect, useState } from "react";
import { useFieldArray, useForm, Controller } from "react-hook-form";
import ResumeUploader from "@/features/resumes/components/ResumeUploader";
import type { ParseResumeResponse } from "@/features/resumes/api/resumes";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import axios from "axios";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { useJobDetailQuery } from "@/features/jobs/hooks/useJobs";
import { useCreateApplicationMutation } from "@/features/applications/hooks/useApplications";
import { getApiErrorMessage } from "@/shared/api/error";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { StepForm } from "@/shared/ui/StepForm";

const STEPS = [
  { label: "基本信息" },
  { label: "工作经历" },
  { label: "项目经历" },
  { label: "教育与技能" },
];

const contactSchema = z.object({
  phone: z.string().optional(),
  email: z.string().email("请输入有效的邮箱地址").optional().or(z.literal("")),
  wechat: z.string().optional(),
  other: z.string().optional(),
});

const workExpSchema = z.object({
  company: z.string().min(1, "公司必填"),
  position: z.string().min(1, "职位必填"),
  start_date: z.string().min(1, "开始日期必填"),
  end_date: z.string().optional().nullable(),
  description: z.string().min(1, "描述必填"),
});

const projectSchema = z.object({
  name: z.string().min(1, "项目名称必填"),
  role: z.string().min(1, "角色必填"),
  start_date: z.string().min(1),
  end_date: z.string().optional().nullable(),
  description: z.string().min(1),
  technologies: z.array(z.string()),
});

const educationSchema = z.object({
  school: z.string().min(1, "学校必填"),
  major: z.string().min(1, "专业必填"),
  degree: z.string().min(1, "学位必填"),
  start_date: z.string().min(1),
  end_date: z.string().optional().nullable(),
});

const certificateSchema = z.object({
  name: z.string().min(1, "证书名称必填"),
  date: z.string().optional().nullable(),
});

const structuredResumeSchema = z.object({
  name: z.string().min(1, "姓名必填"),
  work_experience_years: z.number().min(0, "请输入有效的工作年限"),
  education_level: z.string().optional(),
  contact: contactSchema,
  work_experience: z.array(workExpSchema),
  project_experience: z.array(projectSchema),
  education: z.array(educationSchema).min(1, "请至少添加一条教育经历"),
  certificates: z.array(certificateSchema),
  skills: z.array(z.string()),
  self_evaluation: z.string().optional(),
});

type StructuredResumeForm = z.infer<typeof structuredResumeSchema>;

export default function ApplyPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [currentStep, setCurrentStep] = useState(0);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [resumeParsed, setResumeParsed] = useState(false);

  const createApplicationMutation = useCreateApplicationMutation();
  const { data: job } = useJobDetailQuery(jobId);
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    if (job) {
      setBreadcrumbItems([
        { label: "岗位市场", href: "/jobs" },
        { label: job.title, href: `/jobs/${jobId}` },
        { label: "投递简历" },
      ]);
    } else {
      setBreadcrumbItems([
        { label: "岗位市场", href: "/jobs" },
        { label: "投递简历" },
      ]);
    }
  }, [job, jobId, setBreadcrumbItems]);

  const form = useForm<StructuredResumeForm>({
    resolver: zodResolver(structuredResumeSchema),
    defaultValues: {
      contact: {},
      work_experience: [],
      project_experience: [],
      education: [],
      certificates: [],
      skills: [],
    },
  });

  const { fields: workFields, append: addWork, remove: removeWork } = useFieldArray({
    control: form.control,
    name: "work_experience",
  });
  const { fields: projFields, append: addProj, remove: removeProj } = useFieldArray({
    control: form.control,
    name: "project_experience",
  });
  const { fields: eduFields, append: addEdu, remove: removeEdu } = useFieldArray({
    control: form.control,
    name: "education",
  });
  const { fields: certFields, append: addCert, remove: removeCert } = useFieldArray({
    control: form.control,
    name: "certificates",
  });

  const buildFullResumeText = (data: StructuredResumeForm): string => {
    const lines: string[] = [];
    lines.push(`姓名：${data.name}`);
    lines.push(`工作年限：${data.work_experience_years}年`);
    if (data.education_level) lines.push(`最高学历：${data.education_level}`);

    const contact = data.contact;
    if (contact.phone || contact.email || contact.wechat || contact.other) {
      lines.push("\n联系方式：");
      if (contact.phone) lines.push(`  手机：${contact.phone}`);
      if (contact.email) lines.push(`  邮箱：${contact.email}`);
      if (contact.wechat) lines.push(`  微信：${contact.wechat}`);
      if (contact.other) lines.push(`  其他：${contact.other}`);
    }

    if (data.work_experience.length > 0) {
      lines.push("\n工作经历：");
      data.work_experience.forEach((exp, index) => {
        lines.push(
          `  ${index + 1}. ${exp.company} - ${exp.position} (${exp.start_date} ~ ${exp.end_date || "至今"})`
        );
        lines.push(`     ${exp.description}`);
      });
    }

    if (data.project_experience.length > 0) {
      lines.push("\n项目经历：");
      data.project_experience.forEach((proj, index) => {
        lines.push(
          `  ${index + 1}. ${proj.name} (${proj.role}) (${proj.start_date} ~ ${proj.end_date || "至今"})`
        );
        lines.push(`     ${proj.description}`);
        if (proj.technologies.length > 0) lines.push(`     技术栈：${proj.technologies.join(", ")}`);
      });
    }

    if (data.education.length > 0) {
      lines.push("\n教育经历：");
      data.education.forEach((edu, index) => {
        lines.push(
          `  ${index + 1}. ${edu.school} - ${edu.major} (${edu.degree}) (${edu.start_date} ~ ${edu.end_date || "至今"})`
        );
      });
    }

    if (data.certificates.length > 0) {
      lines.push("\n资格证书：");
      data.certificates.forEach((cert, index) => {
        lines.push(`  ${index + 1}. ${cert.name}${cert.date ? ` (${cert.date})` : ""}`);
      });
    }

    if (data.skills.length > 0) {
      lines.push("\n专业技能：");
      lines.push(`  ${data.skills.join(", ")}`);
    }

    if (data.self_evaluation) {
      lines.push("\n自我评价：");
      lines.push(`  ${data.self_evaluation}`);
    }

    return lines.join("\n");
  };

  const handleFinalSubmit = async (force = false) => {
    if (!jobId) {
      toast.error("岗位信息缺失");
      return;
    }
    const formData = form.getValues();
    const fullResumeText = buildFullResumeText(formData);

    try {
      await createApplicationMutation.mutateAsync({
        payload: {
          job_id: jobId,
          resume_text: fullResumeText,
          structured_resume: formData,
        },
        force,
      });
      setShowSuccess(true);
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        setShowConfirm(true);
      } else if (axios.isAxiosError(error) && error.response?.status === 403) {
        toast.error(error.response.data?.detail || "该岗位已拒绝您的投递，无法再次申请");
      } else {
        toast.error(getApiErrorMessage(error, "投递失败"));
      }
    }
  };

  const handleForceSubmit = async () => {
    setShowConfirm(false);
    await handleFinalSubmit(true);
  };

  const handleNext = async () => {
    // Validate only the fields relevant to current step before advancing
    let valid = true;
    if (currentStep === 0) {
      valid = await form.trigger(["name", "work_experience_years", "contact"]);
    } else if (currentStep === 1) {
      valid = await form.trigger("work_experience");
    } else if (currentStep === 2) {
      valid = await form.trigger("project_experience");
    }
    if (valid) {
      setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
    }
  };

  const handlePrev = () => {
    setCurrentStep((s) => Math.max(s - 1, 0));
  };

  const handleSubmit = async () => {
    const valid = await form.trigger();
    if (valid) {
      await handleFinalSubmit(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Job title header */}
      {job && (
        <div className="mb-6">
          <h1 className="text-2xl font-bold">投递简历</h1>
          <p className="text-muted-foreground mt-1">
            应聘岗位：<span className="text-foreground font-medium">{job.title}</span>
          </p>
        </div>
      )}

      {/* Resume uploader */}
      <ResumeUploader
        onParsed={(data: ParseResumeResponse) => {
          setResumeParsed(true);
          form.reset({
            name: data.structured_data.name || "",
            work_experience_years: data.structured_data.work_experience_years || 0,
            education_level: data.structured_data.education_level || "",
            contact: {
              phone: data.structured_data.contact?.phone || "",
              email: data.structured_data.contact?.email || "",
              wechat: data.structured_data.contact?.wechat || "",
              other: data.structured_data.contact?.other || "",
            },
            work_experience: data.structured_data.work_experience || [],
            project_experience: data.structured_data.project_experience || [],
            education: data.structured_data.education || [],
            certificates: data.structured_data.certificates || [],
            skills: data.structured_data.skills || [],
            self_evaluation: data.structured_data.self_evaluation || "",
          });
          toast.success("简历已自动填充");
        }}
        onReset={() => setResumeParsed(false)}
      />
      {resumeParsed && (
        <p className="text-xs text-green-600 dark:text-green-400 text-center -mt-2 mb-2">
          已自动填充表单，请检查并补充完整后提交
        </p>
      )}
      <Separator className="my-4" />

      {/* Step indicator */}
      <StepForm steps={STEPS} currentStep={currentStep} />

      {/* Step content */}
      <Card className="shadow-sm hover:shadow-md transition-shadow duration-200">
        <CardContent className="p-6">
          {/* Step 0: Basic Info */}
          {currentStep === 0 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4">基本信息</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>姓名 <span className="text-destructive">*</span></Label>
                    <Input {...form.register("name")} placeholder="请输入姓名" />
                    {form.formState.errors.name && (
                      <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>工作年限 <span className="text-destructive">*</span></Label>
                    <Input type="number" {...form.register("work_experience_years", { valueAsNumber: true })} placeholder="请输入工作年限" />
                    {form.formState.errors.work_experience_years && (
                      <p className="text-xs text-destructive">{form.formState.errors.work_experience_years.message}</p>
                    )}
                  </div>
                </div>
                <div className="space-y-2 mt-4">
                  <Label>最高学历</Label>
                  <Input {...form.register("education_level")} placeholder="如：本科、硕士" />
                </div>
              </div>

              <Separator />

              <div>
                <h2 className="text-lg font-semibold mb-4">联系方式</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>手机</Label>
                    <Input {...form.register("contact.phone")} placeholder="手机号码" />
                  </div>
                  <div className="space-y-2">
                    <Label>邮箱</Label>
                    <Input {...form.register("contact.email")} placeholder="邮箱地址" />
                  </div>
                  <div className="space-y-2">
                    <Label>微信</Label>
                    <Input {...form.register("contact.wechat")} placeholder="微信号" />
                  </div>
                  <div className="space-y-2">
                    <Label>其他</Label>
                    <Input {...form.register("contact.other")} placeholder="其他联系方式" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Work Experience */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">工作经历</h2>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addWork({ company: "", position: "", start_date: "", description: "" })}
                >
                  <Plus className="h-4 w-4 mr-1" /> 添加
                </Button>
              </div>
              {workFields.length === 0 && (
                <p className="text-sm text-muted-foreground py-8 text-center">暂无工作经历，点击上方按钮添加</p>
              )}
              {workFields.map((field, index) => (
                <Card key={field.id} className="border-dashed">
                  <CardContent className="p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">工作经历 {index + 1}</span>
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeWork(index)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>公司</Label>
                        <Input {...form.register(`work_experience.${index}.company`)} placeholder="公司名称" />
                      </div>
                      <div className="space-y-2">
                        <Label>职位</Label>
                        <Input {...form.register(`work_experience.${index}.position`)} placeholder="职位名称" />
                      </div>
                      <div className="space-y-2">
                        <Label>开始日期</Label>
                        <Input type="date" {...form.register(`work_experience.${index}.start_date`)} />
                      </div>
                      <div className="space-y-2">
                        <Label>结束日期</Label>
                        <Input type="date" {...form.register(`work_experience.${index}.end_date`)} placeholder="留空表示至今" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>工作描述</Label>
                      <Textarea {...form.register(`work_experience.${index}.description`)} rows={2} placeholder="描述您的工作内容和成果" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Step 2: Project Experience */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">项目经历</h2>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addProj({ name: "", role: "", start_date: "", description: "", technologies: [] })}
                >
                  <Plus className="h-4 w-4 mr-1" /> 添加
                </Button>
              </div>
              {projFields.length === 0 && (
                <p className="text-sm text-muted-foreground py-8 text-center">暂无项目经历，点击上方按钮添加</p>
              )}
              {projFields.map((field, index) => (
                <Card key={field.id} className="border-dashed">
                  <CardContent className="p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">项目经历 {index + 1}</span>
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeProj(index)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>项目名称</Label>
                        <Input {...form.register(`project_experience.${index}.name`)} placeholder="项目名称" />
                      </div>
                      <div className="space-y-2">
                        <Label>角色</Label>
                        <Input {...form.register(`project_experience.${index}.role`)} placeholder="您在项目中的角色" />
                      </div>
                      <div className="space-y-2">
                        <Label>开始日期</Label>
                        <Input type="date" {...form.register(`project_experience.${index}.start_date`)} />
                      </div>
                      <div className="space-y-2">
                        <Label>结束日期</Label>
                        <Input type="date" {...form.register(`project_experience.${index}.end_date`)} placeholder="留空表示至今" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>项目描述</Label>
                      <Textarea {...form.register(`project_experience.${index}.description`)} rows={2} placeholder="描述项目内容和您的贡献" />
                    </div>
                    <div className="space-y-2">
                      <Label>技术栈（逗号分隔）</Label>
                      <Controller
                        control={form.control}
                        name={`project_experience.${index}.technologies`}
                        render={({ field }) => (
                          <Input
                            placeholder="React, TypeScript, Node.js"
                            value={field.value?.join(", ") ?? ""}
                            onBlur={field.onBlur}
                            onChange={(e) => {
                              field.onChange(
                                e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                              );
                            }}
                          />
                        )}
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Step 3: Education & Skills */}
          {currentStep === 3 && (
            <div className="space-y-6">
              {/* Education */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">教育经历 <span className="text-destructive text-sm">*</span></h2>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => addEdu({ school: "", major: "", degree: "", start_date: "", end_date: "" })}
                  >
                    <Plus className="h-4 w-4 mr-1" /> 添加
                  </Button>
                </div>
                {eduFields.map((field, index) => (
                  <Card key={field.id} className="border-dashed mb-4">
                    <CardContent className="p-4 space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">教育经历 {index + 1}</span>
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeEdu(index)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>学校</Label>
                          <Input {...form.register(`education.${index}.school`)} placeholder="学校名称" />
                        </div>
                        <div className="space-y-2">
                          <Label>专业</Label>
                          <Input {...form.register(`education.${index}.major`)} placeholder="专业名称" />
                        </div>
                        <div className="space-y-2">
                          <Label>学位</Label>
                          <Input {...form.register(`education.${index}.degree`)} placeholder="如：学士、硕士" />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>开始日期</Label>
                            <Input type="date" {...form.register(`education.${index}.start_date`)} />
                          </div>
                          <div className="space-y-2">
                            <Label>结束日期</Label>
                            <Input type="date" {...form.register(`education.${index}.end_date`)} />
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {form.formState.errors.education && (
                  <p className="text-sm text-destructive mt-2">{form.formState.errors.education.message}</p>
                )}
              </div>

              <Separator />

              {/* Certificates */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">资格证书</h2>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => addCert({ name: "", date: "" })}
                  >
                    <Plus className="h-4 w-4 mr-1" /> 添加
                  </Button>
                </div>
                {certFields.map((field, index) => (
                  <div key={field.id} className="flex gap-4 items-end mb-4">
                    <div className="flex-1 space-y-2">
                      <Label>证书名称</Label>
                      <Input {...form.register(`certificates.${index}.name`)} placeholder="证书名称" />
                    </div>
                    <div className="w-40 space-y-2">
                      <Label>获得日期</Label>
                      <Input type="date" {...form.register(`certificates.${index}.date`)} />
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeCert(index)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>

              <Separator />

              {/* Skills */}
              <div className="space-y-2">
                <Label>专业技能（逗号分隔）</Label>
                <Controller
                  control={form.control}
                  name="skills"
                  render={({ field }) => (
                    <Input
                      placeholder="JavaScript, Python, 项目管理"
                      value={field.value?.join(", ") ?? ""}
                      onBlur={field.onBlur}
                      onChange={(e) => {
                        field.onChange(
                          e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                        );
                      }}
                    />
                  )}
                />
              </div>

              <div className="space-y-2">
                <Label>自我评价</Label>
                <Textarea {...form.register("self_evaluation")} rows={4} placeholder="简要介绍自己的优势和职业目标" />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation buttons */}
      <div className="flex justify-between mt-6">
        <Button
          type="button"
          variant="outline"
          onClick={handlePrev}
          disabled={currentStep === 0}
        >
          上一步
        </Button>
        {currentStep < STEPS.length - 1 ? (
          <Button type="button" onClick={handleNext}>
            下一步
          </Button>
        ) : (
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={createApplicationMutation.isPending}
          >
            {createApplicationMutation.isPending ? "提交中..." : "提交投递"}
          </Button>
        )}
      </div>

      {/* 409 Conflict dialog */}
      <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>您已投递过该岗位</DialogTitle>
            <DialogDescription>是否使用当前简历覆盖原投递？</DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setShowConfirm(false)}>
              取消
            </Button>
            <Button type="button" onClick={handleForceSubmit} disabled={createApplicationMutation.isPending}>
              覆盖提交
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Success dialog */}
      <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>简历提交成功</DialogTitle>
            <DialogDescription>您的简历已成功提交，招聘方将尽快查看。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              onClick={() => {
                setShowSuccess(false);
                navigate(`/jobs/${jobId}`);
              }}
              className="w-full"
            >
              确定
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
