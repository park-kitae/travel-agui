import { A2uiSurface } from '@a2ui/react/v0_9'
import type { ReactComponentImplementation } from '@a2ui/react/v0_9'
import type { SurfaceModel } from '@a2ui/web_core/v0_9'

interface Props {
  surface: SurfaceModel<ReactComponentImplementation>
}

export function A2uiSurfaceView({ surface }: Props) {
  return (
    <div className="ui-a2ui-surface">
      <A2uiSurface surface={surface} />
    </div>
  )
}
