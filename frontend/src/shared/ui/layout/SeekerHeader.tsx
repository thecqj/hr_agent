import { Briefcase } from "lucide-react";

import AppHeader from "@/shared/ui/layout/AppHeader";

export default function SeekerHeader({
  onNavigate,
  onLogout,
}: {
  onNavigate: (to: string) => void;
  onLogout: () => void;
}) {
  return (
    <AppHeader
      brand="智能投递"
      brandIcon={<Briefcase className="w-6 h-6 text-primary" />}
      items={[
        { label: "岗位市场", to: "/jobs" },
        { label: "我的投递", to: "/my-applications" },
      ]}
      onNavigate={onNavigate}
      onLogout={onLogout}
    />
  );
}
