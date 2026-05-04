import { ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '../../lib/utils'

type Variant = 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive'
type Size = 'default' | 'sm' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', type = 'button', ...props }, ref) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn('ui-button', `ui-button--${variant}`, `ui-button--${size}`, className)}
        {...props}
      />
    )
  }
)

Button.displayName = 'Button'
