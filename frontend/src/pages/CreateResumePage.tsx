import React, { useEffect } from "react";
import { useFieldArray, useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Plus, Trash2, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { StepForm } from "@/shared/ui/StepForm";
import { uploadResume } from "@/features/resumes/api/resumes";
import { getApiErrorMessage } from "@/shared/api/error";

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

const formSchema = z.object({
  name: z.string().min(1, "姓名必填"),
  resumeName: z.string().min(1, "简历名称必填"),
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

type FormData = z.infer<typeof formSchema>;

export default function CreateResumePage() {
  const navigate = useNavigate();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbItems([
      { label: "个人中心", href: "/profile" },
      { label: "新建简历" },
    ]);
  }, [setBreadcrumbItems]);

  const [currentStep, setCurrentStep] = React.useState(0);
  const [submitting, setSubmitting] = React.useState(false);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      contact: {},
      work_experience: [],
      project_experience: [],
      education: [],
      certificates: [],
      skills: [],
    },
  });

  const { fields: workFields, append: addWork, remove: removeWork } = useFieldArray({ control: form.control, name: "work_experience" });
  const { fields: projFields, append: addProj, remove: removeProj } = useFieldArray({ control: form.control, name: "project_experience" });
  const { fields: eduFields, append: addEdu, remove: removeEdu } = useFieldArray({ control: form.control, name: "education" });
  const { fields: certFields, append: addCert, remove: removeCert } = useFieldArray({ control: form.control, name: "certificates" });

  const handleSubmit = async () => {
    const valid = await form.trigger();
    if (!valid) return;

    const data = form.getValues();
    setSubmitting(true);

    try {
      const resumeText = [
        `姓名：${data.name}`,
        `工作年限：${data.work_experience_years}年`,
        data.education_level && `最高学历：${data.education_level}`,
      ].filter(Boolean).join("\n");

      const blob = new Blob([resumeText], { type: "text/plain" });
      const file = new File([blob], `${data.resumeName}.txt`, { type: "text/plain" });

      await uploadResume(file, data.resumeName);
      toast.success("简历保存成功");
      navigate("/profile");
    } catch (error) {
      toast.error(getApiErrorMessage(error, "保存简历失败"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleNext = async () => {
    let valid = true;
    if (currentStep === 0) valid = await form.trigger(["name", "resumeName", "work_experience_years", "contact"]);
    else if (currentStep === 1) valid = await form.trigger("work_experience");
    else if (currentStep === 2) valid = await form.trigger("project_experience");
    if (valid) setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const handlePrev = () => setCurrentStep((s) => Math.max(s - 1, 0));

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">新建简历</h1>
        <p className="text-muted-foreground mt-1">手动填写您的简历信息</p>
      </div>

      <div className="mb-4">
        <div className="space-y-2">
          <Label>简历名称 <span className="text-destructive">*</span></Label>
          <Input {...form.register("resumeName")} placeholder="例如：通用简历、技术岗简历" />
          {form.formState.errors.resumeName && <p className="text-xs text-destructive">{form.formState.errors.resumeName.message}</p>}
        </div>
      </div>

      <StepForm steps={STEPS} currentStep={currentStep} />

      <Card className="shadow-sm">
        <CardContent className="p-6">
          {currentStep === 0 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4">基本信息</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>姓名 <span className="text-destructive">*</span></Label>
                    <Input {...form.register("name")} placeholder="请输入姓名" />
                    {form.formState.errors.name && <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>工作年限 <span className="text-destructive">*</span></Label>
                    <Input type="number" {...form.register("work_experience_years", { valueAsNumber: true })} placeholder="0" />
                    {form.formState.errors.work_experience_years && <p className="text-xs text-destructive">{form.formState.errors.work_experience_years.message}</p>}
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
                  <div className="space-y-2"><Label>手机</Label><Input {...form.register("contact.phone")} placeholder="手机号码" /></div>
                  <div className="space-y-2"><Label>邮箱</Label><Input {...form.register("contact.email")} placeholder="邮箱地址" /></div>
                  <div className="space-y-2"><Label>微信</Label><Input {...form.register("contact.wechat")} placeholder="微信号" /></div>
                  <div className="space-y-2"><Label>其他</Label><Input {...form.register("contact.other")} placeholder="其他联系方式" /></div>
                </div>
              </div>
            </div>
          )}

          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">工作经历</h2>
                <Button type="button" variant="outline" size="sm" onClick={() => addWork({ company: "", position: "", start_date: "", description: "" })}>
                  <Plus className="h-4 w-4 mr-1" /> 添加
                </Button>
              </div>
              {workFields.length === 0 && <p className="text-sm text-muted-foreground py-8 text-center">暂无工作经历，点击上方按钮添加</p>}
              {workFields.map((field, index) => (
                <Card key={field.id} className="border-dashed">
                  <CardContent className="p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">工作经历 {index + 1}</span>
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeWork(index)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2"><Label>公司</Label><Input {...form.register(`work_experience.${index}.company`)} placeholder="公司名称" /></div>
                      <div className="space-y-2"><Label>职位</Label><Input {...form.register(`work_experience.${index}.position`)} placeholder="职位名称" /></div>
                      <div className="space-y-2"><Label>开始日期</Label><Input type="date" {...form.register(`work_experience.${index}.start_date`)} /></div>
                      <div className="space-y-2"><Label>结束日期</Label><Input type="date" {...form.register(`work_experience.${index}.end_date`)} placeholder="留空表示至今" /></div>
                    </div>
                    <div className="space-y-2"><Label>工作描述</Label><Textarea {...form.register(`work_experience.${index}.description`)} rows={2} placeholder="描述您的工作内容和成果" /></div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">项目经历</h2>
                <Button type="button" variant="outline" size="sm" onClick={() => addProj({ name: "", role: "", start_date: "", description: "", technologies: [] })}>
                  <Plus className="h-4 w-4 mr-1" /> 添加
                </Button>
              </div>
              {projFields.length === 0 && <p className="text-sm text-muted-foreground py-8 text-center">暂无项目经历，点击上方按钮添加</p>}
              {projFields.map((field, index) => (
                <Card key={field.id} className="border-dashed">
                  <CardContent className="p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">项目经历 {index + 1}</span>
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeProj(index)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2"><Label>项目名称</Label><Input {...form.register(`project_experience.${index}.name`)} placeholder="项目名称" /></div>
                      <div className="space-y-2"><Label>角色</Label><Input {...form.register(`project_experience.${index}.role`)} placeholder="您在项目中的角色" /></div>
                      <div className="space-y-2"><Label>开始日期</Label><Input type="date" {...form.register(`project_experience.${index}.start_date`)} /></div>
                      <div className="space-y-2"><Label>结束日期</Label><Input type="date" {...form.register(`project_experience.${index}.end_date`)} placeholder="留空表示至今" /></div>
                    </div>
                    <div className="space-y-2"><Label>项目描述</Label><Textarea {...form.register(`project_experience.${index}.description`)} rows={2} placeholder="描述项目内容和您的贡献" /></div>
                    <div className="space-y-2">
                      <Label>技术栈（逗号分隔）</Label>
                      <Controller control={form.control} name={`project_experience.${index}.technologies`} render={({ field: f }) => (
                        <Input placeholder="React, TypeScript, Node.js" value={f.value?.join(", ") ?? ""} onBlur={f.onBlur} onChange={(e) => f.onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
                      )} />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">教育经历 <span className="text-destructive text-sm">*</span></h2>
                  <Button type="button" variant="outline" size="sm" onClick={() => addEdu({ school: "", major: "", degree: "", start_date: "", end_date: "" })}>
                    <Plus className="h-4 w-4 mr-1" /> 添加
                  </Button>
                </div>
                {eduFields.map((field, index) => (
                  <Card key={field.id} className="border-dashed mb-4">
                    <CardContent className="p-4 space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">教育经历 {index + 1}</span>
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeEdu(index)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2"><Label>学校</Label><Input {...form.register(`education.${index}.school`)} placeholder="学校名称" /></div>
                        <div className="space-y-2"><Label>专业</Label><Input {...form.register(`education.${index}.major`)} placeholder="专业名称" /></div>
                        <div className="space-y-2"><Label>学位</Label><Input {...form.register(`education.${index}.degree`)} placeholder="如：学士、硕士" /></div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2"><Label>开始日期</Label><Input type="date" {...form.register(`education.${index}.start_date`)} /></div>
                          <div className="space-y-2"><Label>结束日期</Label><Input type="date" {...form.register(`education.${index}.end_date`)} /></div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {form.formState.errors.education && <p className="text-sm text-destructive mt-2">{form.formState.errors.education.message}</p>}
              </div>
              <Separator />
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">资格证书</h2>
                  <Button type="button" variant="outline" size="sm" onClick={() => addCert({ name: "", date: "" })}>
                    <Plus className="h-4 w-4 mr-1" /> 添加
                  </Button>
                </div>
                {certFields.map((field, index) => (
                  <div key={field.id} className="flex gap-4 items-end mb-4">
                    <div className="flex-1 space-y-2"><Label>证书名称</Label><Input {...form.register(`certificates.${index}.name`)} placeholder="证书名称" /></div>
                    <div className="w-40 space-y-2"><Label>获得日期</Label><Input type="date" {...form.register(`certificates.${index}.date`)} /></div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeCert(index)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                  </div>
                ))}
              </div>
              <Separator />
              <div className="space-y-2">
                <Label>专业技能（逗号分隔）</Label>
                <Controller control={form.control} name="skills" render={({ field: f }) => (
                  <Input placeholder="JavaScript, Python, 项目管理" value={f.value?.join(", ") ?? ""} onBlur={f.onBlur} onChange={(e) => f.onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
                )} />
              </div>
              <div className="space-y-2">
                <Label>自我评价</Label>
                <Textarea {...form.register("self_evaluation")} rows={4} placeholder="简要介绍自己的优势和职业目标" />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-between mt-6">
        <Button type="button" variant="outline" onClick={handlePrev} disabled={currentStep === 0}>上一步</Button>
        {currentStep < STEPS.length - 1 ? (
          <Button type="button" onClick={handleNext}>下一步</Button>
        ) : (
          <Button type="button" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "保存中..." : <><Save className="h-4 w-4 mr-1" />保存简历</>}
          </Button>
        )}
      </div>
    </div>
  );
}
