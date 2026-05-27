import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { LogOut, Briefcase, Upload } from "lucide-react";
import axios from "axios";

// ---------- 结构化简历 Schema ----------
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
  const { clearAuth } = useAuthStore();

  // 步骤控制
  const [step, setStep] = useState<"form" | "cover" | "confirm">("form");
  const [coverLetter, setCoverLetter] = useState("");
  const [parsing, setParsing] = useState(false);

  // 弹窗状态
  const [showConfirm, setShowConfirm] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

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

  // 动态表单数组
  const { fields: workFields, append: addWork, remove: removeWork } = useFieldArray({ control: form.control, name: "work_experience" });
  const { fields: projFields, append: addProj, remove: removeProj } = useFieldArray({ control: form.control, name: "project_experience" });
  const { fields: eduFields, append: addEdu, remove: removeEdu } = useFieldArray({ control: form.control, name: "education" });
  const { fields: certFields, append: addCert, remove: removeCert } = useFieldArray({ control: form.control, name: "certificates" });

  // 生成完整纯文本简历
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
      data.work_experience.forEach((exp, i) => {
        lines.push(`  ${i + 1}. ${exp.company} - ${exp.position} (${exp.start_date} ~ ${exp.end_date || "至今"})`);
        lines.push(`     ${exp.description}`);
      });
    }

    if (data.project_experience.length > 0) {
      lines.push("\n项目经历：");
      data.project_experience.forEach((proj, i) => {
        lines.push(`  ${i + 1}. ${proj.name} (${proj.role}) (${proj.start_date} ~ ${proj.end_date || "至今"})`);
        lines.push(`     ${proj.description}`);
        if (proj.technologies.length > 0) lines.push(`     技术栈：${proj.technologies.join(", ")}`);
      });
    }

    if (data.education.length > 0) {
      lines.push("\n教育经历：");
      data.education.forEach((edu, i) => {
        lines.push(`  ${i + 1}. ${edu.school} - ${edu.major} (${edu.degree}) (${edu.start_date} ~ ${edu.end_date || "至今"})`);
      });
    }

    if (data.certificates.length > 0) {
      lines.push("\n资格证书：");
      data.certificates.forEach((cert, i) => {
        lines.push(`  ${i + 1}. ${cert.name}${cert.date ? ` (${cert.date})` : ""}`);
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

  // 原生文件上传处理
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setParsing(true);
    try {
      const res = await apiClient.post("/resume/parse", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res.data;
      form.reset({
        name: data.name || "",
        work_experience_years: data.work_experience_years || 0,
        education_level: data.education_level || "",
        contact: data.contact || {},
        work_experience: data.work_experience || [],
        project_experience: data.project_experience || [],
        education: data.education || [],
        certificates: data.certificates || [],
        skills: data.skills || [],
        self_evaluation: data.self_evaluation || "",
      });
      toast.success("简历解析成功，请检查并修改");
    } catch {
      toast.error("简历解析失败，请手动填写");
    } finally {
      setParsing(false);
    }
  };

  const handleFinalSubmit = async (force: boolean = false) => {
    setSubmitting(true);
    const formData = form.getValues();
    const fullResumeText = buildFullResumeText(formData);

    try {
      await apiClient.post("/applications/", {
        job_id: jobId,
        resume_text: fullResumeText,
        structured_resume: formData,
        cover_letter: coverLetter || undefined,
      }, { params: { force } });
      setShowSuccess(true);
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        setShowConfirm(true);
      } else {
        toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || "投递失败" : "投递失败");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleForceSubmit = () => {
    setShowConfirm(false);
    handleFinalSubmit(true);
  };

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 求职者导航栏 */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-6 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-primary" />
            <h1 className="text-xl font-bold text-primary">智能投递</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate("/jobs")}>岗位市场</Button>
            <Button variant="ghost" onClick={() => navigate("/my-applications")}>我的投递</Button>
            <Button variant="ghost" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />退出
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-6 max-w-4xl">
        <Card>
          <CardHeader>
            <CardTitle>投递岗位</CardTitle>
          </CardHeader>
          <CardContent>
            {step === "form" && (
              <div className="space-y-6">
                {/* 上传区域 */}
                <div className="border-2 border-dashed rounded-lg p-8 text-center relative transition-colors border-gray-300 hover:border-primary">
                  <Upload className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">点击或拖拽上传简历文件（PDF、Word），支持 AI 自动解析</p>
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    onChange={handleFileChange}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                    disabled={parsing}
                  />
                  {parsing && <p className="text-sm text-muted-foreground mt-2">正在解析中...</p>}
                </div>

                {/* 基本信息 */}
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>姓名</Label><Input {...form.register("name")} /></div>
                  <div><Label>工作年限</Label><Input type="number" {...form.register("work_experience_years", { valueAsNumber: true })} /></div>
                </div>
                <div><Label>最高学历</Label><Input {...form.register("education_level")} /></div>

                {/* 联系方式 */}
                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">联系方式</legend>
                  <div className="grid grid-cols-2 gap-4">
                    <div><Label>手机</Label><Input {...form.register("contact.phone")} /></div>
                    <div><Label>邮箱</Label><Input {...form.register("contact.email")} /></div>
                    <div><Label>微信</Label><Input {...form.register("contact.wechat")} /></div>
                    <div><Label>其他</Label><Input {...form.register("contact.other")} /></div>
                  </div>
                </fieldset>

                {/* 工作经历 */}
                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">工作经历</legend>
                  {workFields.map((field, index) => (
                    <div key={field.id} className="border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
                      <div className="grid grid-cols-2 gap-4">
                        <div><Label>公司</Label><Input {...form.register(`work_experience.${index}.company`)} /></div>
                        <div><Label>职位</Label><Input {...form.register(`work_experience.${index}.position`)} /></div>
                        <div><Label>开始日期</Label><Input type="date" {...form.register(`work_experience.${index}.start_date`)} /></div>
                        <div><Label>结束日期（留空表示至今）</Label><Input type="date" {...form.register(`work_experience.${index}.end_date`)} /></div>
                      </div>
                      <div className="mt-2"><Label>工作描述</Label><Textarea {...form.register(`work_experience.${index}.description`)} rows={2} /></div>
                      <Button variant="destructive" size="sm" className="mt-2" onClick={() => removeWork(index)}>删除</Button>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" onClick={() => addWork({ company: "", position: "", start_date: "", description: "" })}>添加工作经历</Button>
                </fieldset>

                {/* 项目经历 */}
                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">项目经历</legend>
                  {projFields.map((field, index) => (
                    <div key={field.id} className="border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
                      <div className="grid grid-cols-2 gap-4">
                        <div><Label>项目名称</Label><Input {...form.register(`project_experience.${index}.name`)} /></div>
                        <div><Label>角色</Label><Input {...form.register(`project_experience.${index}.role`)} /></div>
                        <div><Label>开始日期</Label><Input type="date" {...form.register(`project_experience.${index}.start_date`)} /></div>
                        <div><Label>结束日期</Label><Input type="date" {...form.register(`project_experience.${index}.end_date`)} /></div>
                      </div>
                      <div className="mt-2"><Label>项目描述</Label><Textarea {...form.register(`project_experience.${index}.description`)} rows={2} /></div>
                      <div className="mt-2">
                        <Label>技术栈（逗号分隔）</Label>
                        <Input
                          {...form.register(`project_experience.${index}.technologies`)}
                          onChange={(e) => {
                            const val = e.target.value.split(',').map(s => s.trim());
                            form.setValue(`project_experience.${index}.technologies`, val);
                          }}
                        />
                      </div>
                      <Button variant="destructive" size="sm" className="mt-2" onClick={() => removeProj(index)}>删除</Button>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" onClick={() => addProj({ name: "", role: "", start_date: "", description: "", technologies: [] })}>添加项目经历</Button>
                </fieldset>

                {/* 教育经历 */}
                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">教育经历</legend>
                  {eduFields.map((field, index) => (
                    <div key={field.id} className="border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
                      <div className="grid grid-cols-2 gap-4">
                        <div><Label>学校</Label><Input {...form.register(`education.${index}.school`)} /></div>
                        <div><Label>专业</Label><Input {...form.register(`education.${index}.major`)} /></div>
                        <div><Label>学位</Label><Input {...form.register(`education.${index}.degree`)} /></div>
                        <div><Label>开始日期</Label><Input type="date" {...form.register(`education.${index}.start_date`)} /></div>
                        <div><Label>结束日期</Label><Input type="date" {...form.register(`education.${index}.end_date`)} /></div>
                      </div>
                      <Button variant="destructive" size="sm" className="mt-2" onClick={() => removeEdu(index)}>删除</Button>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" onClick={() => addEdu({ school: "", major: "", degree: "", start_date: "" })}>添加教育经历</Button>
                </fieldset>

                {/* 证书 */}
                <fieldset className="border p-4 rounded">
                  <legend className="text-sm font-medium">资格证书</legend>
                  {certFields.map((field, index) => (
                    <div key={field.id} className="flex gap-4 items-end border-b pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
                      <div className="flex-1"><Label>证书名称</Label><Input {...form.register(`certificates.${index}.name`)} /></div>
                      <div className="w-40"><Label>获得日期</Label><Input type="date" {...form.register(`certificates.${index}.date`)} /></div>
                      <Button variant="destructive" size="sm" onClick={() => removeCert(index)}>删除</Button>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" onClick={() => addCert({ name: "", date: "" })}>添加证书</Button>
                </fieldset>

                {/* 技能和自我评价 */}
                <div>
                  <Label>专业技能（逗号分隔）</Label>
                  <Input
                    {...form.register("skills")}
                    onChange={(e) => {
                      const val = e.target.value.split(',').map(s => s.trim());
                      form.setValue("skills", val);
                    }}
                  />
                </div>
                <div>
                  <Label>自我评价</Label>
                  <Textarea {...form.register("self_evaluation")} rows={4} />
                </div>

                <div className="flex justify-end gap-4 mt-4">
                  <Button variant="outline" onClick={() => setStep("cover")}>下一步：求职信</Button>
                </div>
              </div>
            )}

            {step === "cover" && (
              <div className="space-y-4">
                <Label>求职信（选填）</Label>
                <Textarea rows={6} value={coverLetter} onChange={(e) => setCoverLetter(e.target.value)} />
                <div className="flex justify-between">
                  <Button variant="outline" onClick={() => setStep("form")}>上一步</Button>
                  <Button onClick={() => setStep("confirm")}>预览并提交</Button>
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
                  <Button variant="outline" onClick={() => setStep("cover")}>上一步</Button>
                  <Button onClick={() => handleFinalSubmit(false)} disabled={submitting}>提交投递</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 覆盖确认弹窗 */}
        <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>您已投递过该岗位</DialogTitle>
              <DialogDescription>是否使用当前简历覆盖原投递？</DialogDescription>
            </DialogHeader>
            <DialogFooter className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowConfirm(false)}>取消</Button>
              <Button onClick={handleForceSubmit} disabled={submitting}>覆盖提交</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* 成功弹窗 */}
        <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>简历提交成功</DialogTitle>
              <DialogDescription>您的简历已成功提交，招聘方将尽快查看。</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button onClick={() => { setShowSuccess(false); navigate(`/jobs/${jobId}`); }} className="w-full">确定</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}