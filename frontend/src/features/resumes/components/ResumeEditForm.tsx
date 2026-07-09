import { useCallback, useMemo } from "react";
import { useFieldArray, useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, AlertCircle, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { StructuredResume } from "@/features/applications/types/application";

const contactSchema = z.object({
  phone: z.string().optional(),
  email: z.string().optional(),
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

const formSchema = z.object({
  name: z.string().min(1, "姓名必填"),
  work_experience_years: z.number().min(0, "请输入有效的工作年限"),
  education_level: z.string().optional(),
  contact: contactSchema,
  work_experience: z.array(workExpSchema),
  project_experience: z.array(projectSchema),
  education: z.array(educationSchema),
  certificates: z.array(certificateSchema),
  skills: z.array(z.string()),
  self_evaluation: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

interface ResumeEditFormProps {
  /** 解析后的结构化简历数据 */
  data: StructuredResume;
  /** 数据变更回调 */
  onChange: (data: StructuredResume) => void;
}

/** 将 StructuredResume 转为表单默认值 */
function toFormDefaults(data: StructuredResume): FormData {
  return {
    name: data.name || "",
    work_experience_years: data.work_experience_years || 0,
    education_level: data.education_level || "",
    contact: {
      phone: data.contact?.phone || "",
      email: data.contact?.email || "",
      wechat: data.contact?.wechat || "",
      other: data.contact?.other || "",
    },
    work_experience: data.work_experience || [],
    project_experience: data.project_experience || [],
    education: data.education || [],
    certificates: data.certificates || [],
    skills: data.skills || [],
    self_evaluation: data.self_evaluation || "",
  };
}

/** 检测缺失字段，返回字段路径数组 */
export function getMissingFields(data: StructuredResume): string[] {
  const missing: string[] = [];
  if (!data.name) missing.push("姓名");
  if (!data.work_experience_years && data.work_experience_years !== 0) missing.push("工作年限");
  if (!data.education_level) missing.push("最高学历");
  if (!data.contact?.phone && !data.contact?.email) missing.push("联系方式");
  if (!data.work_experience || data.work_experience.length === 0) missing.push("工作经历");
  if (!data.project_experience || data.project_experience.length === 0) missing.push("项目经历");
  if (!data.education || data.education.length === 0) missing.push("教育经历");
  if (!data.skills || data.skills.length === 0) missing.push("专业技能");
  return missing;
}

function SectionBadge({ hasData, label }: { hasData: boolean; label: string }) {
  if (hasData) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
        <CheckCircle2 className="h-3.5 w-3.5" />
        已提取
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
      <AlertCircle className="h-3.5 w-3.5" />
      未提取到，请补充
    </span>
  );
}

function FieldHighlight({ hasData, children }: { hasData: boolean; children: React.ReactNode }) {
  if (hasData) return <>{children}</>;
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/10 p-3">
      {children}
    </div>
  );
}

export default function ResumeEditForm({ data, onChange }: ResumeEditFormProps) {
  const defaults = useMemo(() => toFormDefaults(data), [data]);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: defaults,
  });

  const {
    fields: workFields,
    append: addWork,
    remove: removeWork,
  } = useFieldArray({ control: form.control, name: "work_experience" });
  const {
    fields: projFields,
    append: addProj,
    remove: removeProj,
  } = useFieldArray({ control: form.control, name: "project_experience" });
  const {
    fields: eduFields,
    append: addEdu,
    remove: removeEdu,
  } = useFieldArray({ control: form.control, name: "education" });
  const {
    fields: certFields,
    append: addCert,
    remove: removeCert,
  } = useFieldArray({ control: form.control, name: "certificates" });

  const handleFieldChange = useCallback(() => {
    const values = form.getValues();
    onChange(values as StructuredResume);
  }, [form, onChange]);

  const missingFields = useMemo(() => getMissingFields(data), [data]);

  return (
    <div className="space-y-6 max-h-[70vh] overflow-y-auto px-1">
      {/* Missing fields summary */}
      {missingFields.length > 0 && (
        <Card className="border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20">
          <CardContent className="p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                  以下信息未能从简历中完整提取，请补充：
                </p>
                <ul className="mt-1 text-xs text-amber-700 dark:text-amber-400 list-disc list-inside">
                  {missingFields.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Basic Info */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">基本信息</h3>
          <SectionBadge hasData={Boolean(data.name && data.education_level)} label="基本信息" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <FieldHighlight hasData={Boolean(data.name)}>
            <div className="space-y-2">
              <Label>
                姓名 <span className="text-destructive">*</span>
              </Label>
              <Input
                {...form.register("name")}
                placeholder="请输入姓名"
                onChange={(e) => {
                  form.register("name").onChange(e);
                  handleFieldChange();
                }}
              />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>
          </FieldHighlight>
          <FieldHighlight hasData={Boolean(data.work_experience_years)}>
            <div className="space-y-2">
              <Label>
                工作年限 <span className="text-destructive">*</span>
              </Label>
              <Input
                type="number"
                {...form.register("work_experience_years", { valueAsNumber: true })}
                placeholder="0"
                onChange={(e) => {
                  form.register("work_experience_years", { valueAsNumber: true }).onChange(e);
                  handleFieldChange();
                }}
              />
            </div>
          </FieldHighlight>
        </div>
        <div className="mt-4">
          <FieldHighlight hasData={Boolean(data.education_level)}>
            <div className="space-y-2">
              <Label>最高学历</Label>
              <Input
                {...form.register("education_level")}
                placeholder="如：本科、硕士"
                onChange={(e) => {
                  form.register("education_level").onChange(e);
                  handleFieldChange();
                }}
              />
            </div>
          </FieldHighlight>
        </div>
      </div>

      <Separator />

      {/* Contact */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">联系方式</h3>
          <SectionBadge hasData={Boolean(data.contact?.phone || data.contact?.email)} label="联系方式" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <FieldHighlight hasData={Boolean(data.contact?.phone)}>
            <div className="space-y-2">
              <Label>手机</Label>
              <Input
                {...form.register("contact.phone")}
                placeholder="手机号码"
                onChange={(e) => {
                  form.register("contact.phone").onChange(e);
                  handleFieldChange();
                }}
              />
            </div>
          </FieldHighlight>
          <FieldHighlight hasData={Boolean(data.contact?.email)}>
            <div className="space-y-2">
              <Label>邮箱</Label>
              <Input
                {...form.register("contact.email")}
                placeholder="邮箱地址"
                onChange={(e) => {
                  form.register("contact.email").onChange(e);
                  handleFieldChange();
                }}
              />
            </div>
          </FieldHighlight>
          <div className="space-y-2">
            <Label>微信</Label>
            <Input
              {...form.register("contact.wechat")}
              placeholder="微信号"
              onChange={(e) => {
                form.register("contact.wechat").onChange(e);
                handleFieldChange();
              }}
            />
          </div>
          <div className="space-y-2">
            <Label>其他</Label>
            <Input
              {...form.register("contact.other")}
              placeholder="其他联系方式"
              onChange={(e) => {
                form.register("contact.other").onChange(e);
                handleFieldChange();
              }}
            />
          </div>
        </div>
      </div>

      <Separator />

      {/* Work Experience */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">工作经历</h3>
          <SectionBadge hasData={(data.work_experience?.length ?? 0) > 0} label="工作经历" />
        </div>
        {workFields.length === 0 && (
          <p className="text-sm text-muted-foreground py-4 text-center">暂无工作经历</p>
        )}
        {workFields.map((field, index) => (
          <Card key={field.id} className="border-dashed mb-3">
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
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addWork({ company: "", position: "", start_date: "", description: "" })}
        >
          <Plus className="h-4 w-4 mr-1" /> 添加工作经历
        </Button>
      </div>

      <Separator />

      {/* Project Experience */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">项目经历</h3>
          <SectionBadge hasData={(data.project_experience?.length ?? 0) > 0} label="项目经历" />
        </div>
        {projFields.map((field, index) => (
          <Card key={field.id} className="border-dashed mb-3">
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
                  <Input {...form.register(`project_experience.${index}.role`)} placeholder="您的角色" />
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
                  render={({ field: f }) => (
                    <Input
                      placeholder="React, TypeScript, Node.js"
                      value={f.value?.join(", ") ?? ""}
                      onBlur={f.onBlur}
                      onChange={(e) => {
                        f.onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean));
                      }}
                    />
                  )}
                />
              </div>
            </CardContent>
          </Card>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addProj({ name: "", role: "", start_date: "", description: "", technologies: [] })}
        >
          <Plus className="h-4 w-4 mr-1" /> 添加项目经历
        </Button>
      </div>

      <Separator />

      {/* Education */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">教育经历</h3>
          <SectionBadge hasData={(data.education?.length ?? 0) > 0} label="教育经历" />
        </div>
        {eduFields.map((field, index) => (
          <Card key={field.id} className="border-dashed mb-3">
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
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addEdu({ school: "", major: "", degree: "", start_date: "", end_date: "" })}
        >
          <Plus className="h-4 w-4 mr-1" /> 添加教育经历
        </Button>
      </div>

      <Separator />

      {/* Certificates */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">资格证书</h3>
          <SectionBadge hasData={(data.certificates?.length ?? 0) > 0} label="资格证书" />
        </div>
        {certFields.map((field, index) => (
          <div key={field.id} className="flex gap-4 items-end mb-3">
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
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addCert({ name: "", date: "" })}
        >
          <Plus className="h-4 w-4 mr-1" /> 添加证书
        </Button>
      </div>

      <Separator />

      {/* Skills */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">专业技能</h3>
          <SectionBadge hasData={(data.skills?.length ?? 0) > 0} label="专业技能" />
        </div>
        <FieldHighlight hasData={(data.skills?.length ?? 0) > 0}>
          <div className="space-y-2">
            <Label>专业技能（逗号分隔）</Label>
            <Controller
              control={form.control}
              name="skills"
              render={({ field: f }) => (
                <Input
                  placeholder="JavaScript, Python, 项目管理"
                  value={f.value?.join(", ") ?? ""}
                  onBlur={f.onBlur}
                  onChange={(e) => {
                    f.onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean));
                  }}
                />
              )}
            />
          </div>
        </FieldHighlight>
      </div>

      <Separator />

      {/* Self Evaluation */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">自我评价</h3>
          <SectionBadge hasData={Boolean(data.self_evaluation)} label="自我评价" />
        </div>
        <Textarea {...form.register("self_evaluation")} rows={4} placeholder="简要介绍自己的优势和职业目标" />
      </div>
    </div>
  );
}
