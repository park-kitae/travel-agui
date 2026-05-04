import { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'success' | 'warning'
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return <span className={cn('ui-badge', `ui-badge--${variant}`, className)} {...props} />
}
