import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { useCreateJobMutation } from "@/features/jobs/hooks/useJobs";
import type { WorkType } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";

const WORK_TYPE_OPTIONS: { value: WorkType; label: string }[] = [
  { value: "onsite", label: "现场" },
  { value: "remote", label: "远程" },
  { value: "hybrid", label: "混合" },
];

const jobSchema = z.object({
  title: z.string().min(1, "岗位名称不能为空"),
  description: z.string().min(10, "岗位描述至少10字"),
  location: z.string().optional(),
  work_type: z.enum(["remote", "onsite", "hybrid"]).optional(),
  salary_min: z.number({ message: "请输入数字" }).optional(),
  salary_max: z.number({ message: "请输入数字" }).optional(),
});

type JobForm = z.infer<typeof jobSchema>;

export default function PostJobPage() {
  const navigate = useNavigate();
  const createJobMutation = useCreateJobMutation();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [skillInput, setSkillInput] = useState("");
  const [skills, setSkills] = useState<string[]>([]);

  useEffect(() => {
    setBreadcrumbItems([
      { label: "首页", href: "/dashboard" },
      { label: "发布新岗位" },
    ]);
  }, [setBreadcrumbItems]);

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

  const addSkill = () => {
    const trimmed = skillInput.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill));
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addSkill();
    }
  };

  const onSubmit = async (data: JobForm) => {
    const payload = {
      ...data,
      skills_required: skills,
    };

    try {
      await createJobMutation.mutateAsync(payload);
      toast.success("岗位发布成功");
      navigate("/dashboard");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "发布失败"));
    }
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">发布新岗位</h1>

      <Card className="shadow-sm hover:shadow-md transition-shadow duration-200">
        <form onSubmit={handleSubmit(onSubmit)}>
          {/* 基本信息 */}
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="title">岗位名称</Label>
              <Input id="title" {...register("title")} className="mt-1.5" />
              {formState.errors.title && (
                <p className="text-sm text-destructive mt-1">{formState.errors.title.message}</p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="location">工作地点</Label>
                <Input id="location" {...register("location")} className="mt-1.5" placeholder="如：北京" />
              </div>
              <div>
                <Label>工作类型</Label>
                <Select
                  onValueChange={(value) => setValue("work_type", value as WorkType)}
                  defaultValue="onsite"
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WORK_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="salary_min">最低薪资 (K)</Label>
                <Input
                  id="salary_min"
                  type="number"
                  {...register("salary_min", { valueAsNumber: true })}
                  className="mt-1.5"
                  placeholder="如：15"
                />
                {formState.errors.salary_min && (
                  <p className="text-sm text-destructive mt-1">{formState.errors.salary_min.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="salary_max">最高薪资 (K)</Label>
                <Input
                  id="salary_max"
                  type="number"
                  {...register("salary_max", { valueAsNumber: true })}
                  className="mt-1.5"
                  placeholder="如：25"
                />
                {formState.errors.salary_max && (
                  <p className="text-sm text-destructive mt-1">{formState.errors.salary_max.message}</p>
                )}
              </div>
            </div>
          </CardContent>

          <Separator />

          {/* 岗位详情 */}
          <CardHeader>
            <CardTitle>岗位详情</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="description">岗位描述</Label>
              <Textarea
                id="description"
                {...register("description")}
                rows={6}
                className="mt-1.5"
                placeholder="请描述该岗位的主要职责和工作内容..."
              />
              {formState.errors.description && (
                <p className="text-sm text-destructive mt-1">{formState.errors.description.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="requirements">任职要求</Label>
              <Textarea
                id="requirements"
                rows={4}
                className="mt-1.5"
                placeholder="请描述该岗位的任职要求..."
                // Note: no register — this field is not in the current API.
                // It is included per spec for future use but not submitted.
              />
            </div>
          </CardContent>

          <Separator />

          {/* 技能标签 */}
          <CardHeader>
            <CardTitle>技能标签</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={handleSkillKeyDown}
                placeholder="输入技能后按回车添加"
                className="flex-1"
              />
              <Button type="button" variant="outline" onClick={addSkill}>
                <Plus className="h-4 w-4 mr-1" />
                添加
              </Button>
            </div>
            {skills.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-3 py-1 text-sm font-medium"
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => removeSkill(skill)}
                      className="text-primary/60 hover:text-primary"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </CardContent>

          <Separator />

          {/* Submit */}
          <CardContent className="pt-6">
            <Button
              type="submit"
              className="w-full"
              disabled={formState.isSubmitting || createJobMutation.isPending}
            >
              {createJobMutation.isPending ? "发布中..." : "发布岗位"}
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  );
}
