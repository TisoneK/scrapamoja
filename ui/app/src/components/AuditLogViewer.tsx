import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { SkeletonTable } from '@/components/ui/Skeleton'

// Mock audit log data - replace with actual API call
interface AuditLogEntry {
  id: number
  action: 'create' | 'update' | 'toggle' | 'delete'
  sport: string
  site?: string
  old_value?: boolean
  new_value?: boolean
  user: string
  timestamp: string
  description?: string
}

interface AuditLogResponse {
  data: AuditLogEntry[]
  count: number
  page: number
  page_size: number
  total_pages: number
}

interface AuditLogFilters {
  sport?: string
  site?: string
  action?: 'all' | 'create' | 'update' | 'toggle' | 'delete'
  date_from?: string
  date_to?: string
  user?: string
}

export function AuditLogViewer() {
  const [filters, setFilters] = useState<AuditLogFilters>({})
  const [currentPage, setCurrentPage] = useState(1)
  const [isLoading, setIsLoading] = useState(false)

  // Mock data - replace with actual API call
  const mockData: AuditLogResponse = {
    data: [
      {
        id: 1,
        action: 'create',
        sport: 'football',
        site: 'flashscore',
        new_value: true,
        user: 'admin',
        timestamp: '2026-03-06T10:30:00Z',
        description: 'Created new feature flag for football adaptive selectors'
      },
      {
        id: 2,
        action: 'toggle',
        sport: 'football',
        site: 'flashscore',
        old_value: true,
        new_value: false,
        user: 'operator',
        timestamp: '2026-03-06T11:15:00Z',
        description: 'Disabled football adaptive selectors due to maintenance'
      },
      {
        id: 3,
        action: 'update',
        sport: 'tennis',
        site: 'flashscore',
        old_value: false,
        new_value: true,
        user: 'admin',
        timestamp: '2026-03-06T12:00:00Z',
        description: 'Updated tennis feature flag configuration'
      },
    ],
    count: 3,
    page: 1,
    page_size: 20,
    total_pages: 1,
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'create': return 'text-green-600 bg-green-100'
      case 'update': return 'text-blue-600 bg-blue-100'
      case 'toggle': return 'text-yellow-600 bg-yellow-100'
      case 'delete': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const handleFilterChange = (key: keyof AuditLogFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1) // Reset to first page when filters change
  }

  const handleExport = () => {
    // Implement export functionality
    const csvContent = [
      'Action,Sport,Site,User,Timestamp,Description',
      ...mockData.data.map(entry => [
        entry.action,
        entry.sport,
        entry.site || '',
        entry.user,
        entry.timestamp,
        entry.description || ''
      ])
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-log-${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        <Button onClick={handleExport} className="flex items-center space-x-2">
          <span>📥</span>
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sport
              </label>
              <input
                type="text"
                value={filters.sport || ''}
                onChange={(e) => handleFilterChange('sport', e.target.value)}
                placeholder="Filter by sport..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Site
              </label>
              <input
                type="text"
                value={filters.site || ''}
                onChange={(e) => handleFilterChange('site', e.target.value)}
                placeholder="Filter by site..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Action
              </label>
              <select
                value={filters.action || 'all'}
                onChange={(e) => handleFilterChange('action', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Actions</option>
                <option value="create">Create</option>
                <option value="update">Update</option>
                <option value="toggle">Toggle</option>
                <option value="delete">Delete</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                User
              </label>
              <input
                type="text"
                value={filters.user || ''}
                onChange={(e) => handleFilterChange('user', e.target.value)}
                placeholder="Filter by user..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex justify-between items-center">
            <span>Audit Log Entries</span>
            <span className="text-sm font-normal text-gray-500">
              {mockData.count} total entries
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sport
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Site
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {mockData.data.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatTimestamp(entry.timestamp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getActionColor(entry.action)}`}>
                        {entry.action.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {entry.sport}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {entry.site || 'Global'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {entry.user}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                      {entry.description || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
