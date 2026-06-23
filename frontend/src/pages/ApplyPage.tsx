import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import axios from "axios";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import { useCreateApplicationMutation } from "@/features/applications/hooks/useApplications";
import type { StructuredResume } from "@/features/applications/types/application";
import { getApiErrorMessage } from "@/shared/api/error";

const contactSchema = z.object({
  phone: z.string().optional(),
  email: z.string().email().optional(),
  wechat: z.string().optional(),
  other: z.string().optional(),
});

const workExpSchema = z.object({
  company: z.string().min(1, "公司必填"),
  position: z.string().min(1, "职位必填"),
  start_date: z.string().min(1, "开始日期必填"),
  end_date: z.string().optional(),
  description: z.string().min(1, "描述必填"),
});

const projectSchema = z.object({
  name: z.string().min(1, "项目名称必填"),
  role: z.string().min(1, "角色必填"),
  start_date: z.string().min(1),
  end_date: z.string().optional(),
  description: z.string().min(1),
  technologies: z.array(z.string()),
});

const educationSchema = z.object({
  school: z.string().min(1, "学校必填"),
  major: z.string().min(1, "专业必填"),
  degree: z.string().min(1, "学位必填"),
  start_date: z.string().min(1),
  end_date: z.string().optional(),
});

const certificateSchema = z.object({
  name: z.string().min(1, "证书名称必填"),
  date: z.string().optional(),
});

const structuredResumeSchema = z.object({
  name: z.string().min(1, "姓名必填"),
  work_experience_years: z.number().min(0),
  education_level: z.string().optional(),
  contact: contactSchema,
  work_experience: z.array(workExpSchema),
  project_experience: z.array(projectSchema),
  education: z.array(educationSchema),
  certificates: z.array(certificateSchema),
  skills: z.array(z.string()),
  self_evaluation: z.string().optional(),
});

type StructuredResumeForm = z.infer<typeof structuredResumeSchema>;

export default function ApplyPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [step, setStep] = useState<"form" | "cover" | "confirm">("form");
  const [coverLetter, setCoverLetter] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const createApplicationMutation = useCreateApplicationMutation();

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
    const formData = form.getValues();
    const fullResumeText = buildFullResumeText(formData);

    try {
      await createApplicationMutation.mutateAsync({
        payload: {
          job_id: jobId,
          resume_text: fullResumeText,
          structured_resume: formData,
          cover_letter: coverLetter || undefined,
        },
        force,
      });
      setShowSuccess(true);
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        setShowConfirm(true);
      } else {
        toast.error(getApiErrorMessage(error, "投递失败"));
      }
    }
  };

  const handleForceSubmit = async () => {
    setShowConfirm(false);
    await handleFinalSubmit(true);
  };

  return (
    <main className="max-w-4xl">
      <Card>
          <CardHeader>
            <CardTitle>投递岗位</CardTitle>
          </CardHeader>
          <CardContent>
            {step === "form" && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>姓名</Label>
                    <Input {...form.register("name")} />
                  </div>
                  <div>
                    <Label>工作年限</Label>
                    <Input type="number" {...form.register("work_experience_years", { valueAsNumber: true })} />
                  </div>
                </div>
                <div>
                  <Label>最高学历</Label>
                  <Input {...form.register("education_level")} />
                </div>

                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">联系方式</legend>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                    <div>
                      <Label>手机</Label>
                      <Input {...form.register("contact.phone")} />
                    </div>
                    <div>
                      <Label>邮箱</Label>
                      <Input {...form.register("contact.email")} />
                    </div>
                    <div>
                      <Label>微信</Label>
                      <Input {...form.register("contact.wechat")} />
                    </div>
                    <div>
                      <Label>其他</Label>
                      <Input {...form.register("contact.other")} />
                    </div>
                  </div>
                </fieldset>

                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">工作经历</legend>
                  {workFields.map((field, index) => (
                    <div key={field.id} className="border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>公司</Label>
                          <Input {...form.register(`work_experience.${index}.company`)} />
                        </div>
                        <div>
                          <Label>职位</Label>
                          <Input {...form.register(`work_experience.${index}.position`)} />
                        </div>
                        <div>
                          <Label>开始日期</Label>
                          <Input type="date" {...form.register(`work_experience.${index}.start_date`)} />
                        </div>
                        <div>
                          <Label>结束日期（留空表示至今）</Label>
                          <Input type="date" {...form.register(`work_experience.${index}.end_date`)} />
                        </div>
                      </div>
                      <div className="mt-2">
                        <Label>工作描述</Label>
                        <Textarea {...form.register(`work_experience.${index}.description`)} rows={2} />
                      </div>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        className="mt-2"
                        onClick={() => removeWork(index)}
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => addWork({ company: "", position: "", start_date: "", description: "" })}
                  >
                    添加工作经历
                  </Button>
                </fieldset>

                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">项目经历</legend>
                  {projFields.map((field, index) => (
                    <div key={field.id} className="border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>项目名称</Label>
                          <Input {...form.register(`project_experience.${index}.name`)} />
                        </div>
                        <div>
                          <Label>角色</Label>
                          <Input {...form.register(`project_experience.${index}.role`)} />
                        </div>
                        <div>
                          <Label>开始日期</Label>
                          <Input type="date" {...form.register(`project_experience.${index}.start_date`)} />
                        </div>
                        <div>
                          <Label>结束日期</Label>
                          <Input type="date" {...form.register(`project_experience.${index}.end_date`)} />
                        </div>
                      </div>
                      <div className="mt-2">
                        <Label>项目描述</Label>
                        <Textarea {...form.register(`project_experience.${index}.description`)} rows={2} />
                      </div>
                      <div className="mt-2">
                        <Label>技术栈（逗号分隔）</Label>
                        <Input
                          onChange={(e) => {
                            const val = e.target.value
                              .split(",")
                              .map((s) => s.trim())
                              .filter(Boolean);
                            form.setValue(`project_experience.${index}.technologies`, val);
                          }}
                        />
                      </div>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        className="mt-2"
                        onClick={() => removeProj(index)}
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      addProj({ name: "", role: "", start_date: "", description: "", technologies: [] })
                    }
                  >
                    添加项目经历
                  </Button>
                </fieldset>

                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">教育经历</legend>
                  {eduFields.map((field, index) => (
                    <div key={field.id} className="flex gap-4 items-end border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
                      <div className="grid grid-cols-2 gap-4 flex-1">
                        <div>
                          <Label>学校</Label>
                          <Input {...form.register(`education.${index}.school`)} />
                        </div>
                        <div>
                          <Label>专业</Label>
                          <Input {...form.register(`education.${index}.major`)} />
                        </div>
                        <div>
                          <Label>学位</Label>
                          <Input {...form.register(`education.${index}.degree`)} />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label>开始日期</Label>
                            <Input type="date" {...form.register(`education.${index}.start_date`)} />
                          </div>
                          <div>
                            <Label>结束日期</Label>
                            <Input type="date" {...form.register(`education.${index}.end_date`)} />
                          </div>
                        </div>
                      </div>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => removeEdu(index)}
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => addEdu({ school: "", major: "", degree: "", start_date: "" })}
                  >
                    添加教育经历
                  </Button>
                </fieldset>

                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">资格证书</legend>
                  {certFields.map((field, index) => (
                    <div
                      key={field.id}
                      className="flex gap-4 items-end border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0"
                    >
                      <div className="flex-1">
                        <Label>证书名称</Label>
                        <Input {...form.register(`certificates.${index}.name`)} />
                      </div>
                      <div className="w-40">
                        <Label>获得日期</Label>
                        <Input type="date" {...form.register(`certificates.${index}.date`)} />
                      </div>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => removeCert(index)}
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => addCert({ name: "", date: "" })}
                  >
                    添加证书
                  </Button>
                </fieldset>

                <div>
                  <Label>专业技能（逗号分隔）</Label>
                  <Input
                    onChange={(e) => {
                      const val = e.target.value
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean);
                      form.setValue("skills", val);
                    }}
                  />
                </div>
                <div>
                  <Label>自我评价</Label>
                  <Textarea {...form.register("self_evaluation")} rows={4} />
                </div>

                <div className="flex justify-end gap-4 mt-4">
                  <Button type="button" variant="outline" onClick={() => setStep("cover")}>
                    下一步：求职信
                  </Button>
                </div>
              </div>
            )}

            {step === "cover" && (
              <div className="space-y-4">
                <Label>求职信（选填）</Label>
                <Textarea rows={6} value={coverLetter} onChange={(e) => setCoverLetter(e.target.value)} />
                <div className="flex justify-between">
                  <Button type="button" variant="outline" onClick={() => setStep("form")}>
                    上一步
                  </Button>
                  <Button type="button" onClick={() => setStep("confirm")}>
                    预览并提交
                  </Button>
                </div>
              </div>
            )}

            {step === "confirm" && (
              <div className="space-y-4">
                <p className="font-semibold">确认投递信息</p>
                <pre className="text-sm bg-gray-100 p-4 rounded overflow-auto max-h-96">
                  {buildFullResumeText(form.getValues())}
                </pre>
                <div className="flex justify-between">
                  <Button type="button" variant="outline" onClick={() => setStep("cover")}>
                    上一步
                  </Button>
                  <Button
                    type="button"
                    onClick={() => handleFinalSubmit(false)}
                    disabled={createApplicationMutation.isPending}
                  >
                    {createApplicationMutation.isPending ? "提交中..." : "提交投递"}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

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
    </main>
  );
}
