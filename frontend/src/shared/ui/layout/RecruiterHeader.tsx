import { Briefcase } from "lucide-react";

import AppHeader from "@/shared/ui/layout/AppHeader";

export default function RecruiterHeader({
  onNavigate,
  onLogout,
}: {
  onNavigate: (to: string) => void;
  onLogout: () => void;
}) {
  return (
    <AppHeader
      brand="招聘仪表盘"
      brandIcon={<Briefcase className="w-6 h-6 text-primary" />}
      items={[
        { label: "我的岗位", to: "/dashboard" },
        { label: "发布新岗位", to: "/dashboard/post" },
      ]}
      onNavigate={onNavigate}
      onLogout={onLogout}
    />
  );
}
