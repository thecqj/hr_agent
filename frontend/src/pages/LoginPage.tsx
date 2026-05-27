import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { loginUser, registerUser } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'
import { AxiosError } from 'axios'

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
})

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  name: z.string().min(1),
  role: z.enum(['job_seeker', 'recruiter']),
  phone: z.string().optional(),
})

type LoginForm = z.infer<typeof loginSchema>
type RegisterForm = z.infer<typeof registerSchema>

export default function LoginPage() {
  const [activeTab, setActiveTab] = useState('login')
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const loginForm = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })
  const registerForm = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) })

  // 使用 useWatch 监听 role 字段的变化
  const role = useWatch({ control: registerForm.control, name: 'role' })

  const onLogin = async (data: LoginForm) => {
    try {
      const res = await loginUser(data)
      setAuth(res.data.access_token, res.data.refresh_token, res.data.user)
      // 修复点：res.user → res.data.user
      navigate(res.data.user.role === 'recruiter' ? '/dashboard' : '/jobs')
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>
      alert(error.response?.data?.detail || '登录失败')
    }
  }

  const onRegister = async (data: RegisterForm) => {
    try {
      const res = await registerUser(data)
      setAuth(res.data.access_token, res.data.refresh_token, res.data.user)
      // 修复点：res.user → res.data.user
      navigate(res.data.user.role === 'recruiter' ? '/dashboard' : '/jobs')
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>
      alert(error.response?.data?.detail || '注册失败')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-lg">
        <h1 className="text-2xl font-bold text-center mb-6">智能简历投递系统</h1>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">登录</TabsTrigger>
            <TabsTrigger value="register">注册</TabsTrigger>
          </TabsList>

          <TabsContent value="login">
            <form onSubmit={loginForm.handleSubmit(onLogin)} className="space-y-4">
              <div>
                <Label htmlFor="email">邮箱</Label>
                <Input id="email" type="email" {...loginForm.register('email')} />
              </div>
              <div>
                <Label htmlFor="password">密码</Label>
                <Input id="password" type="password" {...loginForm.register('password')} />
              </div>
              <Button type="submit" className="w-full">登录</Button>
            </form>
          </TabsContent>

          <TabsContent value="register">
            <form onSubmit={registerForm.handleSubmit(onRegister)} className="space-y-4">
              <div>
                <Label>角色</Label>
                <div className="flex gap-4 mt-2">
                  <label className="flex items-center gap-2">
                    <Checkbox
                      checked={role === 'job_seeker'}
                      onCheckedChange={() => registerForm.setValue('role', 'job_seeker')}
                    />
                    求职者
                  </label>
                  <label className="flex items-center gap-2">
                    <Checkbox
                      checked={role === 'recruiter'}
                      onCheckedChange={() => registerForm.setValue('role', 'recruiter')}
                    />
                    招聘者
                  </label>
                </div>
                {registerForm.formState.errors.role && (
                  <p className="text-red-500 text-sm">请选择角色</p>
                )}
              </div>
              <div>
                <Label htmlFor="name">姓名</Label>
                <Input id="name" {...registerForm.register('name')} />
              </div>
              <div>
                <Label htmlFor="email">邮箱</Label>
                <Input id="email" type="email" {...registerForm.register('email')} />
              </div>
              <div>
                <Label htmlFor="password">密码</Label>
                <Input id="password" type="password" {...registerForm.register('password')} />
              </div>
              <div>
                <Label htmlFor="phone">手机号 (可选)</Label>
                <Input id="phone" {...registerForm.register('phone')} />
              </div>
              <Button type="submit" className="w-full">注册</Button>
            </form>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}