import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

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
import { Textarea } from "@/components/ui/textarea";
import { useCreateJobMutation } from "@/features/jobs/hooks/useJobs";
import { getApiErrorMessage } from "@/shared/api/error";

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
  const createJobMutation = useCreateJobMutation();

  const { register, handleSubmit, formState, setValue } = useForm<JobForm>({
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
      await createJobMutation.mutateAsync(payload);
      toast.success("岗位发布成功");
      navigate("/dashboard");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "发布失败"));
    }
  };

  return (
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
                    onValueChange={(value) =>
                      setValue("work_type", value as "remote" | "onsite" | "hybrid")
                    }
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
              <Button
                type="submit"
                className="w-full"
                disabled={formState.isSubmitting || createJobMutation.isPending}
              >
                {createJobMutation.isPending ? "发布中..." : "发布"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
  );
}
