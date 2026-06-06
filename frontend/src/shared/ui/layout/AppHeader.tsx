import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

interface HeaderItem {
  label: string;
  to: string;
}

interface AppHeaderProps {
  brand: string;
  brandIcon?: ReactNode;
  items: HeaderItem[];
  onNavigate: (to: string) => void;
  onLogout: () => void;
  logoutLabel?: string;
}

export default function AppHeader({
  brand,
  brandIcon,
  items,
  onNavigate,
  onLogout,
  logoutLabel = "退出登录",
}: AppHeaderProps) {
  return (
    <header className="bg-white border-b sticky top-0 z-10">
      <div className="container mx-auto px-6 py-3 flex justify-between items-center">
        <div className="flex items-center gap-2">
          {brandIcon}
          <h1 className="text-xl font-bold text-primary">{brand}</h1>
        </div>
        <div className="flex items-center gap-4">
          {items.map((item) => (
            <Button key={item.to} variant="ghost" onClick={() => onNavigate(item.to)}>
              {item.label}
            </Button>
          ))}
          <Button variant="ghost" onClick={onLogout}>
            {logoutLabel}
          </Button>
        </div>
      </div>
    </header>
  );
}
