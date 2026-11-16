import { useEffect, useState } from 'react'
import { getHealth, getInfo } from '@/lib/api'
import type { ApiInfo } from '@/lib/types'

export type ServerStatus = 'connecting' | 'warming' | 'ready' | 'offline'

/** Carga la información del servidor y sondea /api/health hasta que el índice por defecto esté listo. */
export function useApiInfo(config: string) {
  const [info, setInfo] = useState<ApiInfo | null>(null)
  const [ready, setReady] = useState<string[]>([])
  const [status, setStatus] = useState<ServerStatus>('connecting')
  const [buildError, setBuildError] = useState<string | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    let retry: number | undefined
    const load = () =>
      getInfo(ctrl.signal)
        .then(setInfo)
        .catch((e) => {
          if (e.name === 'AbortError') return
          setStatus('offline')
          retry = window.setTimeout(load, 4000)
        })
    load()
    return () => {
      ctrl.abort()
      window.clearTimeout(retry)
    }
  }, [])

  useEffect(() => {
    if (!info) return
    const ctrl = new AbortController()
    let timer: number | undefined
    const poll = () =>
      getHealth(ctrl.signal)
        .then((h) => {
          setReady(h.listas)
          setBuildError(h.errores[config] ?? null)
          const isReady = h.listas.includes(config)
          setStatus(isReady ? 'ready' : 'warming')
          if (!isReady) timer = window.setTimeout(poll, 2500)
        })
        .catch((e) => {
          if (e.name === 'AbortError') return
          setStatus('offline')
          timer = window.setTimeout(poll, 4000)
        })
    poll()
    return () => {
      ctrl.abort()
      window.clearTimeout(timer)
    }
  }, [info, config])

  /** Tras una respuesta exitosa la configuración quedó construida. */
  const markReady = (name: string) => {
    setReady((r) => (r.includes(name) ? r : [...r, name]))
    if (name === config) setStatus('ready')
  }

  return { info, ready, status, buildError, markReady }
}
