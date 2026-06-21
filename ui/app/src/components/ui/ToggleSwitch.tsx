import * as React from 'react'
import * as SwitchPrimitives from '@radix-ui/react-switch'

export interface ToggleSwitchProps
  extends React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root> {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  disabled?: boolean
  id?: string
  'aria-label'?: string
  'data-testid'?: string
}

const ToggleSwitch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  ToggleSwitchProps
>(({ className, checked, onCheckedChange, disabled = false, id, 'aria-label': ariaLabel, 'data-testid': dataTestId, ...props }, ref) => {
  return (
    <SwitchPrimitives.Root
      className={`
        peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors 
        focus-visible:outline-none focus-visible:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background 
        disabled:pointer-events-none disabled:opacity-50 
        data-[state=checked]:bg-primary data-[state=unchecked]:bg-input
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        ${className || ''}
      `}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      id={id}
      aria-label={ariaLabel}
      data-testid={dataTestId}
      {...props}
      ref={ref}
    >
      <SwitchPrimitives.Thumb
        className={`
          pointer-events-none block w-5 h-5 rounded-full bg-background shadow-lg ring-0 transition-transform duration-200
          translate-x-0 transition-transform duration-200
          group-data-[state=checked]:translate-x-5 group-data-[state=unchecked]:translate-x-0
          ${disabled ? 'cursor-not-allowed' : ''}
          data-[state=checked]:bg-primary data-[state=unchecked]:bg-gray-200
        `}
      />
    </SwitchPrimitives.Root>
  )
})

ToggleSwitch.displayName = 'ToggleSwitch'

export { ToggleSwitch }
