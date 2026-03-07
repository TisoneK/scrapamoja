import { useState } from 'react'
import { FeatureFlagList } from '@/components/FeatureFlagList'
import { FeatureFlagFilters } from '@/components/FeatureFlagFilters'
import { useFeatureFlagStats, useFeatureFlags, FilterOptions } from '@/hooks/useFeatureFlags'

export function FeatureFlagsPage() {
  const [filters, setFilters] = useState<FilterOptions>({
    sport: '',
    site: '',
    enabled: 'all',
    sortBy: 'updated_at',
    sortOrder: 'desc',
  })

  const { data: stats, isLoading: statsLoading } = useFeatureFlagStats()
  const { data: flagsData, isLoading: flagsLoading, error } = useFeatureFlags(filters)

  const handleFiltersChange = (newFilters: FilterOptions) => {
    setFilters(newFilters)
  }

  const handleResetFilters = () => {
    setFilters({
      sport: '',
      site: '',
      enabled: 'all',
      sortBy: 'updated_at',
      sortOrder: 'desc',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">
          Feature Flags
        </h1>
        <div className="flex space-x-3">
          <button className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
            Add Flag
          </button>
        </div>
      </div>

      {/* Filters */}
      <FeatureFlagFilters
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onReset={handleResetFilters}
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Total Flags</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            {statsLoading ? '--' : stats?.total_flags || 0}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Enabled</h3>
          <p className="mt-2 text-3xl font-bold text-green-600">
            {statsLoading ? '--' : stats?.enabled_flags || 0}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Disabled</h3>
          <p className="mt-2 text-3xl font-bold text-red-600">
            {statsLoading ? '--' : stats?.disabled_flags || 0}
          </p>
        </div>
      </div>

      {/* Feature Flags List */}
      <FeatureFlagList />
    </div>
  )
}
