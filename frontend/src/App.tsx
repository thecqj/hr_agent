import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { useAuthStore } from "@/features/auth/store/authStore";
import ApplicantsPage from "@/pages/ApplicantsPage";
import ApplyPage from "@/pages/ApplyPage";
import JobDashboardPage from "@/pages/JobDashboardPage";
import JobDetailPage from "@/pages/JobDetailPage";
import JobMarketPage from "@/pages/JobMarketPage";
import LoginPage from "@/pages/LoginPage";
import MyApplicationsPage from "@/pages/MyApplicationsPage";
import PostJobPage from "@/pages/PostJobPage";

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

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
