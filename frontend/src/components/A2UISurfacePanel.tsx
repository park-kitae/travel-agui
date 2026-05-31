import { A2uiSurface, type ReactComponentImplementation } from '@a2ui/react/v0_9'
import type { SurfaceModel } from '@a2ui/web_core/v0_9'

interface A2UISurfacePanelProps {
  surfaces: Array<SurfaceModel<ReactComponentImplementation>>
}

export function A2UISurfacePanel({ surfaces }: A2UISurfacePanelProps) {
  if (!surfaces.length) {
    return (
      <div className="a2ui-panel empty">
        <div className="a2ui-empty-state">
          <strong>A2UI</strong> 렌더러가 준비되었습니다.
          <p>에이전트가 A2UI 메시지를 보내면 인터랙티브 UI가 이 영역에 표시됩니다.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="a2ui-panel">
      {surfaces.map(surface => (
        <div key={surface.id} className="a2ui-surface-wrapper">
          <A2uiSurface surface={surface} />
        </div>
      ))}
    </div>
  )
}
