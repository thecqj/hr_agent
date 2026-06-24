import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Briefcase } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRegisterMutation } from "@/features/auth/hooks/useAuthMutations";
import type { UserRole } from "@/features/auth/types/auth";
import { getApiErrorMessage } from "@/shared/api/error";

const registerSchema = z
  .object({
    email: z.string().email("请输入有效的邮箱地址"),
    password: z.string().min(6, "密码至少6个字符"),
    confirmPassword: z.string().min(1, "请确认密码"),
    name: z.string().min(1, "请输入姓名"),
    role: z.enum(["job_seeker", "recruiter"], { message: "请选择角色" }),
    phone: z.string().optional(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "两次输入的密码不一致",
    path: ["confirmPassword"],
  });

type RegisterForm = z.infer<typeof registerSchema>;

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: "job_seeker", label: "求职者" },
  { value: "recruiter", label: "招聘方" },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegisterMutation();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      role: "job_seeker",
    },
  });

  const onSubmit = async (data: RegisterForm) => {
    try {
      const { confirmPassword, ...registerData } = data;
      const res = await registerMutation.mutateAsync(registerData);
      navigate(res.user.role === "recruiter" ? "/dashboard" : "/jobs");
    } catch (err) {
      toast.error(getApiErrorMessage(err as AxiosError, "注册失败"));
    }
  };

  return (
    <div className="h-screen flex">
      {/* Left panel — brand illustration */}
      <div className="flex w-1/2 bg-gradient-to-br from-blue-600 to-blue-800 items-center justify-center p-12">
        <div className="max-w-md text-center text-white">
          <div className="mb-8 flex justify-center relative">
            <svg
              width="120"
              height="120"
              viewBox="0 0 120 120"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="opacity-90"
            >
              <rect x="20" y="30" width="80" height="60" rx="8" fill="white" fillOpacity="0.2" stroke="white" strokeOpacity="0.4" strokeWidth="2" />
              <rect x="30" y="40" width="60" height="8" rx="4" fill="white" fillOpacity="0.3" />
              <rect x="30" y="54" width="40" height="4" rx="2" fill="white" fillOpacity="0.2" />
              <rect x="30" y="64" width="50" height="4" rx="2" fill="white" fillOpacity="0.2" />
              <rect x="30" y="74" width="30" height="4" rx="2" fill="white" fillOpacity="0.2" />
            </svg>
            <Briefcase className="absolute top-0 right-0 text-white/80 w-6 h-6" />
          </div>
          <h1 className="text-3xl font-bold mb-3">智能简历投递系统</h1>
          <p className="text-blue-100 text-lg">让求职更高效</p>
        </div>
      </div>

      {/* Right panel — register form */}
      <div className="flex-1 flex items-center justify-center bg-background p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-bold">创建账户</h2>
            <p className="text-muted-foreground mt-1">注册以开始使用</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                placeholder="请输入邮箱"
                {...register("email")}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="至少6个字符"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">确认密码</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="请再次输入密码"
                {...register("confirmPassword")}
              />
              {errors.confirmPassword && (
                <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">姓名</Label>
              <Input
                id="name"
                placeholder="请输入姓名"
                {...register("name")}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>角色</Label>
              <Select
                onValueChange={(value) => setValue("role", value as UserRole)}
                defaultValue="job_seeker"
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.role && (
                <p className="text-sm text-destructive">{errors.role.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">
                手机号 <span className="text-muted-foreground text-xs">(选填)</span>
              </Label>
              <Input
                id="phone"
                placeholder="请输入手机号"
                {...register("phone")}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={registerMutation.isPending}
            >
              {registerMutation.isPending ? "注册中..." : "注册"}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-4">
            已有账号？{" "}
            <a href="/login" className="text-primary hover:underline">
              立即登录
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
