import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto flex items-center justify-between py-4 px-4">
        <Link to="/jobs" className="text-xl font-bold">JobBoard</Link>
        <div className="flex gap-4 items-center">
          {user ? (
            <>
              <span>{user.name} ({user.role === 'job_seeker' ? '求职者' : '招聘者'})</span>
              {user.role === 'recruiter' && (
                <>
                  <Button variant="ghost" onClick={() => navigate('/dashboard/post')}>发布岗位</Button>
                  <Button variant="ghost" onClick={() => navigate('/dashboard/jobs')}>我的岗位</Button>
                </>
              )}
              <Button variant="outline" onClick={() => { logout(); navigate('/login') }}>退出</Button>
            </>
          ) : (
            <Button onClick={() => navigate('/login')}>登录</Button>
          )}
        </div>
      </div>
    </nav>
  )
}