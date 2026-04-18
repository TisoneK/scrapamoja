import { Link, useLocation } from "react-router-dom";
import { Flag, AlertTriangle, ScrollText, Zap, User, LayoutGrid, Play, BarChart2 } from "lucide-react";
import { cn } from "@/utils";

interface LayoutProps {
  children: React.ReactNode;
}

const workbenchNav = [
  { name: "Studio",  href: "/studio",  icon: LayoutGrid, match: ["/studio","/"] },
  { name: "Runs",    href: "/runs",    icon: Play,        match: ["/runs"] },
  { name: "Results", href: "/results", icon: BarChart2,   match: ["/results"] },
];

const adminNav = [
  { name: "Feature Flags", href: "/feature-flags", icon: Flag,          match: ["/feature-flags"] },
  { name: "Escalation",    href: "/escalation",    icon: AlertTriangle, match: ["/escalation"] },
  { name: "Audit Log",     href: "/audit-log",     icon: ScrollText,    match: ["/audit-log"] },
];

// Pages that should render full-bleed (no padding wrapper)
const FULLBLEED = ["/studio", "/", "/runs", "/results"];

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const allNav = [...workbenchNav, ...adminNav];
  const currentPage = allNav.find((n) => n.match.includes(location.pathname));
  const isFullBleed = FULLBLEED.includes(location.pathname);

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* ── Sidebar ── */}
      <aside className="w-60 flex-shrink-0 bg-slate-950 flex flex-col">
        <div className="flex items-center gap-3 px-5 h-14 border-b border-slate-800">
          <div className="w-7 h-7 bg-indigo-500 rounded-md flex items-center justify-center flex-shrink-0">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-white font-semibold text-sm leading-tight">Scrapamoja</p>
            <p className="text-slate-500 text-xs">Desktop</p>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <p className="px-3 mb-2 text-xs font-semibold text-slate-600 uppercase tracking-wider">Workbench</p>
          {workbenchNav.map((item) => {
            const active = item.match.includes(location.pathname);
            const Icon = item.icon;
            return (
              <Link key={item.name} to={item.href} className="block no-underline">
                <div className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                  active ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}>
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {item.name}
                </div>
              </Link>
            );
          })}

          <div className="my-3 border-t border-slate-800" />
          <p className="px-3 mb-2 text-xs font-semibold text-slate-600 uppercase tracking-wider">System</p>
          {adminNav.map((item) => {
            const active = item.match.includes(location.pathname);
            const Icon = item.icon;
            return (
              <Link key={item.name} to={item.href} className="block no-underline">
                <div className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                  active ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}>
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {item.name}
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="px-3 pb-4 pt-3 border-t border-slate-800">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-7 h-7 bg-indigo-700 rounded-full flex items-center justify-center flex-shrink-0">
              <User className="w-3.5 h-3.5 text-indigo-200" />
            </div>
            <div className="min-w-0">
              <p className="text-slate-200 text-sm font-medium truncate leading-tight">System Admin</p>
              <p className="text-slate-500 text-xs truncate">Administrator</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar — only show for non-fullbleed pages */}
        {!isFullBleed && (
          <header className="h-14 bg-white border-b border-slate-200 px-8 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-400">Scrapamoja</span>
              <span className="text-slate-300">/</span>
              <span className="text-slate-700 font-medium">{currentPage?.name ?? "Dashboard"}</span>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-full px-3 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              API Offline
            </span>
          </header>
        )}

        {/* Page content */}
        <main className={cn("flex-1 overflow-hidden", !isFullBleed && "overflow-y-auto")}>
          {isFullBleed ? (
            <div className="h-full flex flex-col">{children}</div>
          ) : (
            <div className="min-h-full p-6 flex flex-col">{children}</div>
          )}
        </main>
      </div>
    </div>
  );
}
