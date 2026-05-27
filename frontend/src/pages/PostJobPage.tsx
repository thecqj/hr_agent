import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { LogOut, Briefcase } from "lucide-react";
import { AxiosError } from "axios";

const jobSchema = z.object({
  title: z.string().min(1, "标题不能为空"),
  description: z.string().min(10, "描述至少10字"),
  location: z.string().optional(),
  work_type: z.enum(["remote", "onsite", "hybrid"]).optional(),
  salary_min: z.number().optional(),
  salary_max: z.number().optional(),
  skills_required: z.string().optional(),
});

type JobForm = z.infer<typeof jobSchema>;

export default function PostJobPage() {
  const navigate = useNavigate();
  const { clearAuth } = useAuthStore();
  const {
    register,
    handleSubmit,
    formState,
    setValue,
  } = useForm<JobForm>({
    resolver: zodResolver(jobSchema),
    defaultValues: {
      work_type: "onsite",
    },
  });

  const onSubmit = async (data: JobForm) => {
    const payload = {
      ...data,
      skills_required: data.skills_required
        ? data.skills_required.split(",").map((s) => s.trim())
        : [],
    };
    try {
      await apiClient.post("/jobs/", payload);
      toast.success("岗位发布成功");
      navigate("/dashboard");
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>;
      toast.error(error.response?.data?.detail || "发布失败");
    }
  };

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ========== 招聘者导航栏 ========== */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-6 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-primary" />
            <h1 className="text-xl font-bold text-primary">招聘仪表盘</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate("/dashboard")}>
              我的岗位
            </Button>
            <Button variant="ghost" onClick={() => navigate("/dashboard/post")}>
              发布新岗位
            </Button>
            <Button variant="ghost" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              退出登录
            </Button>
          </div>
        </div>
      </header>

      {/* ========== 内容区 ========== */}
      <main className="container mx-auto p-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>发布新岗位</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <Label>标题</Label>
                <Input {...register("title")} />
              </div>
              <div>
                <Label>描述</Label>
                <Textarea {...register("description")} rows={6} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>地点</Label>
                  <Input {...register("location")} />
                </div>
                <div>
                  <Label>工作类型</Label>
                  <Select
                    onValueChange={(value) => setValue("work_type", value as "remote" | "onsite" | "hybrid")}
                    defaultValue="onsite"
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="onsite">现场</SelectItem>
                      <SelectItem value="remote">远程</SelectItem>
                      <SelectItem value="hybrid">混合</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>最低薪资(K)</Label>
                  <Input type="number" {...register("salary_min", { valueAsNumber: true })} />
                </div>
                <div>
                  <Label>最高薪资(K)</Label>
                  <Input type="number" {...register("salary_max", { valueAsNumber: true })} />
                </div>
              </div>
              <div>
                <Label>所需技能（逗号分隔）</Label>
                <Input placeholder="React, TypeScript" {...register("skills_required")} />
              </div>
              <Button type="submit" className="w-full" disabled={formState.isSubmitting}>
                发布
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}