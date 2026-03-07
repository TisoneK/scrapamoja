import * as React from 'react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'

interface ConfirmationDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'info'
}

export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'warning'
}: ConfirmationDialogProps) {
  if (!isOpen) return null

  const handleConfirm = () => {
    onConfirm()
    onClose()
  }

  const getVariantClasses = () => {
    switch (variant) {
      case 'danger':
        return 'border-red-200 bg-red-50'
      case 'warning':
        return 'border-yellow-200 bg-yellow-50'
      case 'info':
        return 'border-blue-200 bg-blue-50'
      default:
        return 'border-gray-200 bg-gray-50'
    }
  }

  const getIconClasses = () => {
    switch (variant) {
      case 'danger':
        return 'text-red-600'
      case 'warning':
        return 'text-yellow-600'
      case 'info':
        return 'text-blue-600'
      default:
        return 'text-gray-600'
    }
  }

  const getConfirmButtonVariant = () => {
    switch (variant) {
      case 'danger':
        return 'destructive' as const
      case 'warning':
        return 'outline' as const
      case 'info':
        return 'default' as const
      default:
        return 'outline' as const
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <Card className={getVariantClasses()}>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <span className={`w-6 h-6 ${getIconClasses()}`}>
                {variant === 'danger' && '⚠️'}
                {variant === 'warning' && '⚠️'}
                {variant === 'info' && 'ℹ️'}
              </span>
              {title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700 mb-6">{message}</p>
            <div className="flex justify-end space-x-3">
              <Button
                variant="outline"
                onClick={onClose}
              >
                {cancelText}
              </Button>
              <Button
                variant={getConfirmButtonVariant()}
                onClick={handleConfirm}
              >
                {confirmText}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
