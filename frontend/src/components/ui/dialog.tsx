import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { ReactNode } from 'react'
import { cn } from '../../lib/utils'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogPortal = DialogPrimitive.Portal
export const DialogClose = DialogPrimitive.Close

export function DialogContent({
  className,
  children,
  hideClose = false,
  closeLabel = '닫기',
}: {
  className?: string
  children: ReactNode
  hideClose?: boolean
  closeLabel?: string
}) {
  return (
    <DialogPortal>
      <DialogPrimitive.Overlay className="ui-dialog-overlay" />
      <DialogPrimitive.Content className={cn('ui-dialog-content', className)}>
        {children}
        {!hideClose && (
          <DialogPrimitive.Close className="ui-dialog-close" aria-label={closeLabel}>
            <X size={18} />
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </DialogPortal>
  )
}

export function DialogHeader({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('ui-dialog-header', className)}>{children}</div>
}

export function DialogTitle({ className, children }: { className?: string; children: ReactNode }) {
  return <DialogPrimitive.Title className={cn('ui-dialog-title', className)}>{children}</DialogPrimitive.Title>
}

export function DialogDescription({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <DialogPrimitive.Description className={cn('ui-dialog-description', className)}>
      {children}
    </DialogPrimitive.Description>
  )
}
