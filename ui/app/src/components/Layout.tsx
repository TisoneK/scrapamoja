import { Link, useLocation } from "react-router-dom";
import { Flag, AlertTriangle, ScrollText, Zap, User } from "lucide-react";
import { cn } from "@/utils";

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  {
    name: "Feature Flags",
    href: "/feature-flags",
    icon: Flag,
    match: ["/", "/feature-flags"],
  },
  {
    name: "Escalation",
    href: "/escalation",
    icon: AlertTriangle,
    match: ["/escalation"],
  },
  {
    name: "Audit Log",
    href: "/audit-log",
    icon: ScrollText,
    match: ["/audit-log"],
  },
];

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const currentPage = navigation.find((n) =>
    n.match.includes(location.pathname),
  );

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* ── Sidebar ── */}
      <aside className="w-60 flex-shrink-0 bg-slate-950 flex flex-col">
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-slate-800">
          <div className="w-7 h-7 bg-indigo-500 rounded-md flex items-center justify-center flex-shrink-0">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-white font-semibold text-sm leading-tight">
              Scrapamoja
            </p>
            <p className="text-slate-500 text-xs">Admin Console</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-5 space-y-0.5">
          <p className="px-3 mb-2 text-xs font-semibold text-slate-600 uppercase tracking-wider">
            Navigation
          </p>
          {navigation.map((item) => {
            const active = item.match.includes(location.pathname);
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                  active
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100",
                )}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="px-3 pb-4 pt-4 border-t border-slate-800">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-7 h-7 bg-indigo-700 rounded-full flex items-center justify-center flex-shrink-0">
              <User className="w-3.5 h-3.5 text-indigo-200" />
            </div>
            <div className="min-w-0">
              <p className="text-slate-200 text-sm font-medium truncate leading-tight">
                System Admin
              </p>
              <p className="text-slate-500 text-xs truncate">Administrator</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-400">Scrapamoja</span>
            <span className="text-slate-300">/</span>
            <span className="text-slate-700 font-medium">
              {currentPage?.name ?? "Dashboard"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-full px-3 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              API Offline
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="min-h-full p-6 flex flex-col">{children}</div>
        </main>
      </div>
    </div>
  );
}
