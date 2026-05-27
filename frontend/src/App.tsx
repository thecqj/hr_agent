import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import JobMarketPage from "@/pages/JobMarketPage";
import JobDetailPage from "@/pages/JobDetailPage";
import ApplyPage from "@/pages/ApplyPage";
import PostJobPage from "@/pages/PostJobPage";
import JobDashboardPage from "@/pages/JobDashboardPage";
import ApplicantsPage from "@/pages/ApplicantsPage";
import MyApplicationsPage from "@/pages/MyApplicationsPage";
import { useAuthStore } from "@/stores/authStore";

function ProtectedRoute({ children, role }: { children: React.ReactNode; role?: string }) {
  // 直接判断是否已水合，无需 useEffect
  const hydrated = useAuthStore.persist.hasHydrated();
  const user = useAuthStore((s) => s.user);

  // 水合未完成，显示加载中
  if (!hydrated) {
    return <div className="flex justify-center py-20 text-gray-500">加载中...</div>;
  }

  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return <>{children}</>;
}
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/jobs" element={<JobMarketPage />} />
        <Route path="/jobs/:id" element={<JobDetailPage />} />
        <Route
          path="/apply/:jobId"
          element={
            <ProtectedRoute role="job_seeker">
              <ApplyPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-applications"
          element={
            <ProtectedRoute role="job_seeker">
              <MyApplicationsPage />
            </ProtectedRoute>
          }
        />

        {/* 招聘者路由 */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute role="recruiter">
              <JobDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard/post"
          element={
            <ProtectedRoute role="recruiter">
              <PostJobPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard/applicants/:jobId"
          element={
            <ProtectedRoute role="recruiter">
              <ApplicantsPage />
            </ProtectedRoute>
          }
        />

        {/* 默认重定向（必须放在最后） */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}