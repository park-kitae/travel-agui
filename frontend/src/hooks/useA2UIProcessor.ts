import { useCallback, useEffect, useState } from 'react'
import { MessageProcessor } from '@a2ui/web_core/v0_9'
import { basicCatalog, type ReactComponentImplementation } from '@a2ui/react/v0_9'
import type { SurfaceModel } from '@a2ui/web_core/v0_9'
import type { A2uiMessage, A2uiMessageListWrapper } from '@a2ui/web_core/v0_9'

export function useA2UIProcessor() {
  const [processor] = useState(() => new MessageProcessor<ReactComponentImplementation>([basicCatalog]))
  const [surfaces, setSurfaces] = useState<Array<SurfaceModel<ReactComponentImplementation>>>(
    () => Array.from(processor.model.surfacesMap.values()),
  )

  useEffect(() => {
    const sync = () => {
      setSurfaces(Array.from(processor.model.surfacesMap.values()))
    }

    const createdSub = processor.onSurfaceCreated(sync)
    const deletedSub = processor.onSurfaceDeleted(sync)

    return () => {
      createdSub.unsubscribe()
      deletedSub.unsubscribe()
    }
  }, [processor])

  const processMessages = useCallback(
    (messages: A2uiMessage[] | A2uiMessageListWrapper) => {
      processor.processMessages(messages)
      setSurfaces(Array.from(processor.model.surfacesMap.values()))
    },
    [processor],
  )

  const getSurface = useCallback(
    (surfaceId: string) => processor.model.surfacesMap.get(surfaceId),
    [processor],
  )

  return {
    processor,
    surfaces,
    processMessages,
    getSurface,
  }
}
