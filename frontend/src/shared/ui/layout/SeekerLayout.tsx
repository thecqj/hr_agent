import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Briefcase } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useLogout } from "@/features/auth/hooks/useLogout";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "岗位市场", path: "/jobs" },
  { label: "我的投递", path: "/my-applications" },
] as const;

export default function SeekerLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useLogout();
  const user = useAuthStore((s) => s.user);

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  return (
    <div className="min-h-screen bg-background">
      <header className="h-16 bg-card border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => navigate("/jobs")}
            >
              <Briefcase className="h-5 w-5 text-primary" />
              <span className="font-bold text-primary text-lg">智能投递</span>
            </div>
            <Separator orientation="vertical" className="h-6" />
            <nav className="flex items-center gap-1">
              {NAV_ITEMS.map((item) => (
                <Button
                  key={item.path}
                  variant="ghost"
                  onClick={() => navigate(item.path)}
                  className={cn(isActive(item.path) && "text-primary font-medium")}
                >
                  {item.label}
                </Button>
              ))}
            </nav>
          </div>
          <div>
            {user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="text-xs">
                        {user.name.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem className="text-muted-foreground text-xs cursor-default">
                    {user.name}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={logout}>退出登录</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Button variant="outline" size="sm" onClick={() => navigate("/login")}>
                登录
              </Button>
            )}
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-8 px-6">
        <Outlet />
      </main>
    </div>
  );
}
