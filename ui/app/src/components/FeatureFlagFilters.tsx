import { useMemo } from "react";
import { Search, RotateCcw } from "lucide-react";
import { cn } from "@/utils";

interface FilterState {
  sport: string;
  site: string;
  enabled: "all" | "enabled" | "disabled";
  sortBy: "updated_at" | "sport" | "site" | "created_at";
  sortOrder: "asc" | "desc";
}

interface FeatureFlagFiltersProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  onReset: () => void;
}

export function FeatureFlagFilters({
  filters,
  onFiltersChange,
  onReset,
}: FeatureFlagFiltersProps) {
  const hasActiveFilters = useMemo(
    () =>
      filters.sport !== "" || filters.site !== "" || filters.enabled !== "all",
    [filters.sport, filters.site, filters.enabled],
  );

  const set = <K extends keyof FilterState>(key: K, value: FilterState[K]) =>
    onFiltersChange({ ...filters, [key]: value });

  return (
    <div className="bg-white rounded-xl border border-slate-200 px-4 py-3">
      <div className="flex flex-wrap items-end gap-3">
        {/* Sport */}
        <div className="flex-1 min-w-[130px]">
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Sport
          </label>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={filters.sport}
              onChange={(e) => set("sport", e.target.value)}
              placeholder="Filter by sport…"
              className="select pl-7 h-8 text-xs"
            />
          </div>
        </div>

        {/* Site */}
        <div className="flex-1 min-w-[130px]">
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Site
          </label>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={filters.site}
              onChange={(e) => set("site", e.target.value)}
              placeholder="Filter by site…"
              className="select pl-7 h-8 text-xs"
            />
          </div>
        </div>

        {/* Status */}
        <div className="w-34">
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Status
          </label>
          <select
            value={filters.enabled}
            onChange={(e) =>
              set("enabled", e.target.value as FilterState["enabled"])
            }
            className="select h-8 text-xs"
          >
            <option value="all">All statuses</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>

        {/* Sort by */}
        <div className="w-36">
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Sort by
          </label>
          <select
            value={filters.sortBy}
            onChange={(e) =>
              set("sortBy", e.target.value as FilterState["sortBy"])
            }
            className="select h-8 text-xs"
          >
            <option value="updated_at">Last updated</option>
            <option value="sport">Sport</option>
            <option value="site">Site</option>
            <option value="created_at">Created</option>
          </select>
        </div>

        {/* Order */}
        <div className="w-32">
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Order
          </label>
          <select
            value={filters.sortOrder}
            onChange={(e) =>
              set("sortOrder", e.target.value as FilterState["sortOrder"])
            }
            className="select h-8 text-xs"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>

        {/* Reset */}
        <button
          onClick={onReset}
          disabled={!hasActiveFilters}
          className={cn(
            "flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-medium border transition-colors duration-150 mb-0 self-end",
            hasActiveFilters
              ? "border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300"
              : "border-slate-100 text-slate-300 cursor-not-allowed",
          )}
        >
          <RotateCcw className="w-3 h-3" />
          Reset
        </button>
      </div>
    </div>
  );
}
