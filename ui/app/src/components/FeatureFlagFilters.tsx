import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'

interface FilterState {
  sport: string
  site: string
  enabled: 'all' | 'enabled' | 'disabled'
  sortBy: 'updated_at' | 'sport' | 'site' | 'created_at'
  sortOrder: 'asc' | 'desc'
}

interface FeatureFlagFiltersProps {
  filters: FilterState
  onFiltersChange: (filters: FilterState) => void
  onReset: () => void
}

export function FeatureFlagFilters({ filters, onFiltersChange, onReset }: FeatureFlagFiltersProps) {
  const handleSportChange = (sport: string) => {
    onFiltersChange({ ...filters, sport })
  }

  const handleSiteChange = (site: string) => {
    onFiltersChange({ ...filters, site })
  }

  const handleEnabledChange = (enabled: FilterState['enabled']) => {
    onFiltersChange({ ...filters, enabled })
  }

  const handleSortChange = (sortBy: FilterState['sortBy']) => {
    onFiltersChange({ ...filters, sortBy })
  }

  const handleSortOrderChange = (sortOrder: FilterState['sortOrder']) => {
    onFiltersChange({ ...filters, sortOrder })
  }

  const hasActiveFilters = useMemo(() => {
    return filters.sport !== '' || filters.site !== '' || filters.enabled !== 'all'
  }, [filters.sport, filters.site, filters.enabled])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Filters</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Sport Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sport
            </label>
            <input
              type="text"
              value={filters.sport}
              onChange={(e) => handleSportChange(e.target.value)}
              placeholder="Filter by sport..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Site Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Site
            </label>
            <input
              type="text"
              value={filters.site}
              onChange={(e) => handleSiteChange(e.target.value)}
              placeholder="Filter by site..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filters.enabled}
              onChange={(e) => handleEnabledChange(e.target.value as FilterState['enabled'])}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>

          {/* Sort Options */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sort By
              </label>
              <select
                value={filters.sortBy}
                onChange={(e) => handleSortChange(e.target.value as FilterState['sortBy'])}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="updated_at">Last Updated</option>
                <option value="sport">Sport</option>
                <option value="site">Site</option>
                <option value="created_at">Created</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Order
              </label>
              <select
                value={filters.sortOrder}
                onChange={(e) => handleSortOrderChange(e.target.value as FilterState['sortOrder'])}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </div>
          </div>

          {/* Reset Button */}
          <div className="flex justify-end">
            <Button
              variant="outline"
              onClick={onReset}
              disabled={!hasActiveFilters}
            >
              Reset Filters
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
