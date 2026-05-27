import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { LogOut, Briefcase } from "lucide-react";
import axios from "axios";

// ---------- 结构化简历类型定义 ----------
interface Contact {
  phone?: string;
  email?: string;
  wechat?: string;
  other?: string;
}

interface WorkExperience {
  company: string;
  position: string;
  start_date: string;
  end_date?: string;
  description: string;
}

interface ProjectExperience {
  name: string;
  role: string;
  start_date: string;
  end_date?: string;
  description: string;
  technologies: string[];
}

interface Education {
  school: string;
  major: string;
  degree: string;
  start_date: string;
  end_date?: string;
}

interface Certificate {
  name: string;
  date?: string;
}

interface StructuredResume {
  name: string;
  work_experience_years: number;
  education_level?: string;
  contact: Contact;
  work_experience: WorkExperience[];
  project_experience: ProjectExperience[];
  education: Education[];
  certificates: Certificate[];
  skills: string[];
  self_evaluation?: string;
}

// ---------- 投递者类型定义 ----------
interface Applicant {
  id: string;
  applicant_name: string;
  resume_text: string;
  cover_letter?: string;
  structured_resume?: StructuredResume;
  match_score: number | null;
  status: string;
}

const STATUS_MAP: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "待查看", variant: "outline" },
  reviewed: { label: "已查看", variant: "secondary" },
  interview: { label: "面试中", variant: "default" },
  rejected: { label: "不合适", variant: "destructive" },
  hired: { label: "已录用", variant: "default" },
};

export default function ApplicantsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { clearAuth } = useAuthStore();
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [selectedApplicant, setSelectedApplicant] = useState<Applicant | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ignore = false;
    const fetchApplicants = async () => {
      try {
        const res = await apiClient.get(`/applications/job/${jobId}`);
        if (!ignore) setApplicants(res.data.items);
      } catch {
        if (!ignore) toast.error("获取投递列表失败");
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    fetchApplicants();
    return () => { ignore = true; };
  }, [jobId]);

  const updateStatus = async (applicantId: string, newStatus: string) => {
    try {
      await apiClient.patch(`/applications/${applicantId}/status`, { status: newStatus });
      setApplicants((prev) =>
        prev.map((a) => (a.id === applicantId ? { ...a, status: newStatus } : a))
      );
      toast.success("状态已更新");
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail || "状态更新失败"
        : "状态更新失败";
      toast.error(msg);
    }
  };

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  // 格式化日期显示
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "至今";
    return new Date(dateStr).toLocaleDateString();
  };

  if (loading) return <div className="text-center py-8">加载中...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 招聘者导航栏 */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-6 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-primary" />
            <h1 className="text-xl font-bold text-primary">招聘仪表盘</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate("/dashboard")}>我的岗位</Button>
            <Button variant="ghost" onClick={() => navigate("/dashboard/post")}>发布新岗位</Button>
            <Button variant="ghost" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />退出
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">投递列表</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {applicants.map((app) => (
            <Card key={app.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg cursor-pointer hover:underline" onClick={() => setSelectedApplicant(app)}>
                    {app.applicant_name}
                  </CardTitle>
                  <Badge variant={STATUS_MAP[app.status]?.variant || "outline"}>
                    {STATUS_MAP[app.status]?.label || app.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">匹配度</span>
                  <span className="font-semibold">
                    {app.match_score != null ? `${Math.round(app.match_score * 100)}%` : "未评估"}
                  </span>
                </div>
                <Separator className="my-2" />
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

        {/* 简历详情弹窗 */}
        <Dialog open={!!selectedApplicant} onOpenChange={() => setSelectedApplicant(null)}>
          <DialogContent className="!max-w-6xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{selectedApplicant?.applicant_name} 的简历</DialogTitle>
              <DialogDescription>
                匹配度：{selectedApplicant?.match_score != null ? `${Math.round(selectedApplicant.match_score * 100)}%` : "未评估"}
                &nbsp;|&nbsp;状态：{STATUS_MAP[selectedApplicant?.status || "pending"]?.label}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 text-sm">
              {selectedApplicant?.structured_resume ? (
                <>
                  {/* 一、基本信息 */}
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-semibold mb-3 text-base border-b pb-2">基本信息</h4>
                    <div className="grid grid-cols-2 gap-y-2 gap-x-6">
                      <div><span className="font-medium">姓名：</span>{selectedApplicant.structured_resume.name}</div>
                      <div><span className="font-medium">工作年限：</span>{selectedApplicant.structured_resume.work_experience_years}年</div>
                      {selectedApplicant.structured_resume.education_level && (
                        <div><span className="font-medium">最高学历：</span>{selectedApplicant.structured_resume.education_level}</div>
                      )}
                    </div>
                  </div>

                  {/* 二、联系方式 */}
                  {selectedApplicant.structured_resume.contact &&
                    Object.values(selectedApplicant.structured_resume.contact).some(Boolean) && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-base border-b pb-2">联系方式</h4>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                        {selectedApplicant.structured_resume.contact.phone && <div><span className="font-medium">📞 电话：</span>{selectedApplicant.structured_resume.contact.phone}</div>}
                        {selectedApplicant.structured_resume.contact.email && <div><span className="font-medium">✉️ 邮箱：</span>{selectedApplicant.structured_resume.contact.email}</div>}
                        {selectedApplicant.structured_resume.contact.wechat && <div><span className="font-medium">💬 微信：</span>{selectedApplicant.structured_resume.contact.wechat}</div>}
                        {selectedApplicant.structured_resume.contact.other && <div><span className="font-medium">🔗 其他：</span>{selectedApplicant.structured_resume.contact.other}</div>}
                      </div>
                    </div>
                  )}

                  {/* 三、工作经历 */}
                  {selectedApplicant.structured_resume.work_experience?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-base border-b pb-2">工作经历</h4>
                      {selectedApplicant.structured_resume.work_experience.map((exp, idx) => (
                        <div key={idx} className="mb-3 border-l-4 border-primary/30 pl-4">
                          <p className="font-semibold">{exp.company}</p>
                          <p className="text-sm text-muted-foreground">{exp.position} &nbsp;|&nbsp; {formatDate(exp.start_date)} ~ {formatDate(exp.end_date)}</p>
                          <p className="mt-1 text-gray-700">{exp.description}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 四、项目经历 */}
                  {selectedApplicant.structured_resume.project_experience?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-base border-b pb-2">项目经历</h4>
                      {selectedApplicant.structured_resume.project_experience.map((proj, idx) => (
                        <div key={idx} className="mb-3 border-l-4 border-primary/30 pl-4">
                          <p className="font-semibold">{proj.name}</p>
                          <p className="text-sm text-muted-foreground">{proj.role} &nbsp;|&nbsp; {formatDate(proj.start_date)} ~ {formatDate(proj.end_date)}</p>
                          <p className="mt-1 text-gray-700">{proj.description}</p>
                          {proj.technologies?.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {proj.technologies.map((tech) => (
                                <Badge key={tech} variant="secondary" className="text-xs">{tech}</Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 五、教育经历 */}
                  {selectedApplicant.structured_resume.education?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-base border-b pb-2">教育经历</h4>
                      {selectedApplicant.structured_resume.education.map((edu, idx) => (
                        <div key={idx} className="flex justify-between items-center mb-2 border-b border-dashed pb-1">
                          <span><span className="font-medium">{edu.school}</span> · {edu.major} · {edu.degree}</span>
                          <span className="text-xs text-muted-foreground">{formatDate(edu.start_date)} ~ {formatDate(edu.end_date)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 六、资格证书 */}
                  {selectedApplicant.structured_resume.certificates?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-base border-b pb-2">资格证书</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedApplicant.structured_resume.certificates.map((cert, idx) => (
                          <Badge key={idx} variant="outline" className="text-sm py-1 px-3">
                            {cert.name}{cert.date ? ` (${cert.date})` : ''}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 七、专业技能 */}
                  {selectedApplicant.structured_resume.skills?.length > 0 && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-base border-b pb-2">专业技能</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedApplicant.structured_resume.skills.map((skill, idx) => (
                          <Badge key={idx} variant="default" className="bg-primary/20 text-primary-foreground hover:bg-primary/30 text-sm py-1 px-3">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 八、自我评价 */}
                  {selectedApplicant.structured_resume.self_evaluation && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-semibold mb-3 text-base border-b pb-2">自我评价</h4>
                      <p className="whitespace-pre-wrap text-gray-700 leading-relaxed">{selectedApplicant.structured_resume.self_evaluation}</p>
                    </div>
                  )}
                </>
              ) : (
                <div>
                  <h4 className="font-semibold mb-2">简历内容（纯文本）</h4>
                  <p className="whitespace-pre-wrap text-sm">{selectedApplicant?.resume_text || "无简历内容"}</p>
                </div>
              )}

              {selectedApplicant?.cover_letter && (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2 text-base border-b pb-2">求职信</h4>
                  <p className="whitespace-pre-wrap text-sm">{selectedApplicant.cover_letter}</p>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}