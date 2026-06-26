import { Fragment } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Briefcase, LogOut, PlusCircle } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useLogout } from "@/features/auth/hooks/useLogout";
import { ChatBubble } from "@/features/chat/components/ChatBubble";
import { cn } from "@/lib/utils";
import { BreadcrumbProvider, useBreadcrumb } from "./breadcrumb-context";

const SIDEBAR_ITEMS = [
  { label: "我的岗位", icon: Briefcase, path: "/dashboard" },
  { label: "发布新岗位", icon: PlusCircle, path: "/dashboard/post" },
] as const;

function RecruiterLayoutInner() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useLogout();
  const user = useAuthStore((s) => s.user);
  const { items: breadcrumbItems } = useBreadcrumb();

  const isActive = (path: string) => {
    if (path === "/dashboard") {
      // "我的岗位" is active for /dashboard and /dashboard/applicants/*
      return (
        location.pathname === "/dashboard" ||
        location.pathname.startsWith("/dashboard/applicants/")
      );
    }
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className="w-60 bg-card border-r flex flex-col shrink-0">
        <div
          className="h-16 flex items-center justify-center border-b cursor-pointer"
          onClick={() => navigate("/dashboard")}
        >
          <Briefcase className="h-5 w-5 text-primary mr-2" />
          <span className="font-bold text-primary text-lg">招聘管理</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {SIDEBAR_ITEMS.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                isActive(item.path)
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="p-4">
          <Separator className="mb-4" />
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-muted transition-colors"
          >
            <LogOut className="h-4 w-4" />
            退出登录
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-muted/50 border-b flex items-center justify-between px-6 shrink-0">
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbItems.map((item, i) => (
                <Fragment key={i}>
                  {i > 0 && <BreadcrumbSeparator />}
                  <BreadcrumbItem>
                    {item.href ? (
                      <BreadcrumbLink
                        onClick={() => navigate(item.href!)}
                        className="cursor-pointer"
                      >
                        {item.label}
                      </BreadcrumbLink>
                    ) : (
                      <BreadcrumbPage>{item.label}</BreadcrumbPage>
                    )}
                  </BreadcrumbItem>
                </Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">
              {user?.name.charAt(0) ?? ""}
            </AvatarFallback>
          </Avatar>
        </header>

        {/* Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
      <ChatBubble />
    </div>
  );
}

export default function RecruiterLayout() {
  return (
    <BreadcrumbProvider>
      <RecruiterLayoutInner />
    </BreadcrumbProvider>
  );
}
