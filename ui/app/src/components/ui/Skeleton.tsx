import { cn } from '@/utils'

interface SkeletonProps {
  className?: string
  children?: React.ReactNode
}

export function Skeleton({ className, children }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-gray-200',
        className
      )}
    >
      {children}
    </div>
  )
}

interface SkeletonCardProps {
  className?: string
}

export function SkeletonCard({ className }: SkeletonCardProps) {
  return (
    <div className={cn('bg-white rounded-lg shadow-sm p-6', className)}>
      <div className="space-y-4">
        {/* Header skeleton */}
        <div className="flex justify-between items-start">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-6 w-20" />
        </div>
        
        {/* Content skeleton */}
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-20" />
        </div>
        
        {/* Actions skeleton */}
        <div className="flex items-center space-x-3">
          <Skeleton className="h-6 w-11" />
          <Skeleton className="h-8 w-16" />
        </div>
      </div>
    </div>
  )
}

interface SkeletonTableProps {
  rows?: number
  className?: string
}

export function SkeletonTable({ rows = 5, className }: SkeletonTableProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {[...Array(rows)].map((_, index) => (
        <SkeletonCard key={index} />
      ))}
    </div>
  )
}

interface SkeletonStatsProps {
  className?: string
}

export function SkeletonStats({ className }: SkeletonStatsProps) {
  return (
    <div className={cn('grid grid-cols-1 md:grid-cols-3 gap-6', className)}>
      {[...Array(3)].map((_, index) => (
        <div key={index} className="bg-white p-6 rounded-lg shadow">
          <Skeleton className="h-3 w-20 mb-2" />
          <Skeleton className="h-8 w-12" />
        </div>
      ))}
    </div>
  )
}
