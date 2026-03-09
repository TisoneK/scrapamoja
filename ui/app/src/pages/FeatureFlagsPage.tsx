import { useState } from "react";
import { Flag, CheckCircle2, XCircle, Plus } from "lucide-react";
import { FeatureFlagList } from "@/components/FeatureFlagList";
import { FeatureFlagFilters } from "@/components/FeatureFlagFilters";
import { useFeatureFlagStats } from "@/hooks/useFeatureFlags";

interface FilterState {
  sport: string;
  site: string;
  enabled: "all" | "enabled" | "disabled";
  sortBy: "updated_at" | "sport" | "site" | "created_at";
  sortOrder: "asc" | "desc";
}

const DEFAULT_FILTERS: FilterState = {
  sport: "",
  site: "",
  enabled: "all",
  sortBy: "updated_at",
  sortOrder: "desc",
};

export function FeatureFlagsPage() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const { data: stats, isLoading: statsLoading } = useFeatureFlagStats();

  const statCards = [
    {
      label: "Total Flags",
      value: statsLoading ? null : (stats?.total_flags ?? 0),
      icon: Flag,
      iconBg: "bg-slate-100",
      iconColor: "text-slate-600",
      valueColor: "text-slate-900",
    },
    {
      label: "Enabled",
      value: statsLoading ? null : (stats?.enabled_flags ?? 0),
      icon: CheckCircle2,
      iconBg: "bg-emerald-50",
      iconColor: "text-emerald-600",
      valueColor: "text-emerald-600",
    },
    {
      label: "Disabled",
      value: statsLoading ? null : (stats?.disabled_flags ?? 0),
      icon: XCircle,
      iconBg: "bg-red-50",
      iconColor: "text-red-500",
      valueColor: "text-red-500",
    },
  ];

  return (
    <div className="flex flex-col flex-1 space-y-3">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-base font-semibold text-slate-900 tracking-tight">
          Feature Flags
        </h1>
        <button className="inline-flex items-center gap-1.5 bg-indigo-600 text-white text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-indigo-700 active:bg-indigo-800 transition-colors duration-150 shadow-sm">
          <Plus className="w-3 h-3" />
          Add Flag
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.label}
              className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex items-center gap-3 hover:shadow-sm transition-shadow duration-200"
            >
              <div
                className={`w-8 h-8 ${card.iconBg} rounded-lg flex items-center justify-center flex-shrink-0`}
              >
                <Icon className={`w-4 h-4 ${card.iconColor}`} />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide leading-none">
                  {card.label}
                </p>
                {statsLoading ? (
                  <div className="mt-1 h-5 w-10 bg-slate-100 rounded animate-pulse" />
                ) : (
                  <p
                    className={`text-xl font-bold mt-0.5 leading-none ${card.valueColor}`}
                  >
                    {card.value}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <FeatureFlagFilters
        filters={filters}
        onFiltersChange={setFilters}
        onReset={() => setFilters(DEFAULT_FILTERS)}
      />

      {/* Flag list — flex-1 so it fills remaining height */}
      <div className="flex flex-col flex-1 min-h-0">
        <FeatureFlagList
          sport={filters.sport || undefined}
          site={filters.site || undefined}
        />
      </div>
    </div>
  );
}
