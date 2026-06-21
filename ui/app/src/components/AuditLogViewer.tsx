import { useState } from "react";
import { Download, Search, FileText } from "lucide-react";

interface AuditLogEntry {
  id: number;
  action: "create" | "update" | "toggle" | "delete";
  sport: string;
  site?: string;
  old_value?: boolean;
  new_value?: boolean;
  user: string;
  timestamp: string;
  description?: string;
}

interface AuditLogResponse {
  data: AuditLogEntry[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface AuditLogFilters {
  sport?: string;
  site?: string;
  action?: "all" | "create" | "update" | "toggle" | "delete";
  user?: string;
}

const MOCK_DATA: AuditLogResponse = {
  data: [
    {
      id: 1,
      action: "create",
      sport: "football",
      site: "flashscore",
      new_value: true,
      user: "admin",
      timestamp: "2026-03-06T13:30:00Z",
      description: "Created new feature flag for football adaptive selectors",
    },
    {
      id: 2,
      action: "toggle",
      sport: "football",
      site: "flashscore",
      old_value: true,
      new_value: false,
      user: "operator",
      timestamp: "2026-03-06T14:15:00Z",
      description:
        "Disabled football adaptive selectors due to scheduled maintenance window",
    },
    {
      id: 3,
      action: "update",
      sport: "tennis",
      site: "flashscore",
      old_value: false,
      new_value: true,
      user: "admin",
      timestamp: "2026-03-06T15:00:00Z",
      description:
        "Updated tennis feature flag configuration and enabled it for production",
    },
  ],
  count: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const ACTION_BADGE: Record<
  AuditLogEntry["action"],
  { label: string; className: string }
> = {
  create: { label: "CREATE", className: "badge badge-green" },
  toggle: { label: "TOGGLE", className: "badge badge-yellow" },
  update: { label: "UPDATE", className: "badge badge-blue" },
  delete: { label: "DELETE", className: "badge badge-red" },
};

function formatTimestamp(ts: string) {
  const d = new Date(ts);
  const date = d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const time = d.toLocaleString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return { date, time };
}

function UserAvatar({ name }: { name: string }) {
  return (
    <span
      title={name}
      className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold flex items-center justify-center uppercase flex-shrink-0 cursor-default"
    >
      {name[0]}
    </span>
  );
}

export function AuditLogViewer() {
  const [filters, setFilters] = useState<AuditLogFilters>({});
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const set = <K extends keyof AuditLogFilters>(
    key: K,
    value: AuditLogFilters[K],
  ) => setFilters((prev) => ({ ...prev, [key]: value }));

  const filtered = MOCK_DATA.data.filter((entry) => {
    if (
      filters.sport &&
      !entry.sport.toLowerCase().includes(filters.sport.toLowerCase())
    )
      return false;
    if (
      filters.site &&
      !entry.site?.toLowerCase().includes(filters.site.toLowerCase())
    )
      return false;
    if (
      filters.action &&
      filters.action !== "all" &&
      entry.action !== filters.action
    )
      return false;
    if (
      filters.user &&
      !entry.user.toLowerCase().includes(filters.user.toLowerCase())
    )
      return false;
    return true;
  });

  const handleExport = () => {
    const rows = [
      ["Timestamp", "Action", "Sport", "Site", "User", "Description"],
      ...filtered.map((e) => [
        e.timestamp,
        e.action,
        e.sport,
        e.site ?? "",
        e.user,
        e.description ?? "",
      ]),
    ];
    const csv = rows.map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col flex-1 space-y-3">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold text-slate-900 tracking-tight">
          Audit Log
        </h1>
        <button
          onClick={handleExport}
          className="inline-flex items-center gap-2 bg-slate-900 text-white text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-slate-800 active:bg-slate-950 transition-colors duration-150 shadow-sm"
        >
          <Download className="w-3.5 h-3.5" />
          Export CSV
        </button>
      </div>

      {/* Filter bar — no header row, inputs only */}
      <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Sport */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              Sport
            </label>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={filters.sport ?? ""}
                onChange={(e) => set("sport", e.target.value)}
                placeholder="Filter by sport…"
                className="select pl-8 h-8 text-xs"
              />
            </div>
          </div>

          {/* Site */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              Site
            </label>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={filters.site ?? ""}
                onChange={(e) => set("site", e.target.value)}
                placeholder="Filter by site…"
                className="select pl-8 h-8 text-xs"
              />
            </div>
          </div>

          {/* Action */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              Action
            </label>
            <select
              value={filters.action ?? "all"}
              onChange={(e) =>
                set("action", e.target.value as AuditLogFilters["action"])
              }
              className="select h-8 text-xs"
            >
              <option value="all">All actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="toggle">Toggle</option>
              <option value="delete">Delete</option>
            </select>
          </div>

          {/* User */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              User
            </label>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={filters.user ?? ""}
                onChange={(e) => set("user", e.target.value)}
                placeholder="Filter by user…"
                className="select pl-8 h-8 text-xs"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Table card */}
      <div className="flex flex-col flex-1 bg-white rounded-xl border border-slate-200 overflow-hidden">
        {/* Card header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Entries
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-medium">
            {filtered.length} {filtered.length === 1 ? "entry" : "entries"}
          </span>
        </div>

        {filtered.length === 0 ? (
          <div className="flex flex-col flex-1 items-center justify-center py-12 text-slate-400">
            <FileText className="w-7 h-7 mb-2 text-slate-300" />
            <p className="text-sm font-medium text-slate-500">
              No entries match your filters
            </p>
            <p className="text-xs mt-0.5">
              Try adjusting or clearing the filters above
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full data-table">
              <thead>
                <tr>
                  <th className="w-28">Timestamp</th>
                  <th className="w-24">Action</th>
                  <th className="w-28">Sport</th>
                  <th className="w-28">Site</th>
                  <th className="w-10 text-center">By</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((entry) => {
                  const badge = ACTION_BADGE[entry.action];
                  const isExpanded = expandedRow === entry.id;
                  const isLong = (entry.description?.length ?? 0) > 60;
                  const { date, time } = formatTimestamp(entry.timestamp);

                  return (
                    <>
                      <tr key={entry.id}>
                        {/* Stacked timestamp */}
                        <td className="whitespace-nowrap">
                          <span className="block text-xs text-slate-500">
                            {date}
                          </span>
                          <span className="block font-mono text-xs text-slate-700 mt-0.5">
                            {time}
                          </span>
                        </td>

                        <td className="whitespace-nowrap">
                          <span className={badge.className}>{badge.label}</span>
                        </td>

                        <td className="whitespace-nowrap font-medium text-slate-800 capitalize">
                          {entry.sport}
                        </td>

                        <td className="whitespace-nowrap">
                          {entry.site ? (
                            <span className="badge badge-slate">
                              {entry.site}
                            </span>
                          ) : (
                            <span className="text-slate-300 text-xs italic">
                              Global
                            </span>
                          )}
                        </td>

                        {/* Avatar only — name on hover */}
                        <td className="text-center">
                          <UserAvatar name={entry.user} />
                        </td>

                        {/* Description with expand toggle */}
                        <td>
                          <div className="flex items-start gap-1.5">
                            <span
                              className={
                                isLong && !isExpanded
                                  ? "truncate block max-w-xs"
                                  : "block whitespace-normal"
                              }
                              title={
                                !isExpanded ? entry.description : undefined
                              }
                            >
                              {entry.description ?? "—"}
                            </span>
                            {isLong && (
                              <button
                                onClick={() =>
                                  setExpandedRow(isExpanded ? null : entry.id)
                                }
                                className="flex-shrink-0 text-xs text-indigo-500 hover:text-indigo-700 font-medium whitespace-nowrap mt-0.5"
                              >
                                {isExpanded ? "less" : "more"}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr
                          key={`${entry.id}-expanded`}
                          className="!bg-indigo-50/40"
                        >
                          <td colSpan={6} className="px-4 pb-3 pt-0">
                            <p className="text-sm text-slate-600 leading-relaxed border-l-2 border-indigo-300 ml-1 pl-3">
                              {entry.description}
                            </p>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
