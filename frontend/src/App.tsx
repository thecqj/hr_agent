import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { useAuthStore } from "@/features/auth/store/authStore";
import ApplicantsPage from "@/pages/ApplicantsPage";
import ApplyPage from "@/pages/ApplyPage";
import JobDashboardPage from "@/pages/JobDashboardPage";
import JobDetailPage from "@/pages/JobDetailPage";
import JobMarketPage from "@/pages/JobMarketPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import MyApplicationsPage from "@/pages/MyApplicationsPage";
import PostJobPage from "@/pages/PostJobPage";
import RecruiterLayout from "@/shared/ui/layout/RecruiterLayout";
import SeekerLayout from "@/shared/ui/layout/SeekerLayout";

function ProtectedRoute({
  children,
  role,
}: {
  children: React.ReactNode;
  role?: "job_seeker" | "recruiter";
}) {
  const hydrated = useAuthStore.persist.hasHydrated();
  const user = useAuthStore((s) => s.user);

  if (!hydrated) {
    return <div className="flex justify-center py-20 text-muted-foreground">加载中...</div>;
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
        <Route path="/register" element={<RegisterPage />} />

        {/* Seeker routes — top-bar layout */}
        <Route element={<SeekerLayout />}>
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
        </Route>

        {/* Recruiter routes — sidebar layout */}
        <Route element={<RecruiterLayout />}>
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
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
