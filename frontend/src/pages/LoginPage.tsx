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
import { useLoginMutation } from "@/features/auth/hooks/useAuthMutations";
import { getApiErrorMessage } from "@/shared/api/error";

const loginSchema = z.object({
  email: z.string().email("请输入有效的邮箱地址"),
  password: z.string().min(6, "密码至少6个字符"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const loginMutation = useLoginMutation();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    try {
      const res = await loginMutation.mutateAsync(data);
      navigate(res.user.role === "recruiter" ? "/dashboard" : "/jobs");
    } catch (err) {
      toast.error(getApiErrorMessage(err as AxiosError, "登录失败"));
    }
  };

  return (
    <div className="h-screen flex">
      {/* Left panel — brand illustration */}
      <div className="flex w-1/2 bg-gradient-to-br from-blue-600 to-blue-800 items-center justify-center p-12">
        <div className="max-w-md text-center text-white">
          {/* SVG brand illustration placeholder */}
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

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center bg-background p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-bold">欢迎回来</h2>
            <p className="text-muted-foreground mt-1">登录您的账户</p>
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
                placeholder="请输入密码"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? "登录中..." : "登录"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
