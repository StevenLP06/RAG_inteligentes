import type { ApiInfo, AskResult } from './types'

export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    throw new ApiError('No se pudo contactar el servidor. ¿Está corriendo la API (uvicorn api.server:app)?', 0)
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* cuerpo no JSON */ }
    throw new ApiError(detail || `Error HTTP ${res.status}`, res.status)
  }
  return res.json() as Promise<T>
}

export const getInfo = (signal?: AbortSignal) => request<ApiInfo>('/api/info', { signal })

export const getHealth = (signal?: AbortSignal) =>
  request<{ ok: boolean; listas: string[]; errores: Record<string, string> }>('/api/health', { signal })

/** Consulta el RAG. Se descartan campos pesados que la interfaz no necesita guardar en el historial. */
export async function ask(pregunta: string, config: string, signal?: AbortSignal): Promise<AskResult> {
  const raw = await request<AskResult & Record<string, unknown>>('/api/ask', {
    method: 'POST',
    body: JSON.stringify({ pregunta, config }),
    signal,
  })
  const { uso_tokens: _u, intentos_llm: _i, ...rest } = raw
  return {
    ...rest,
    contexto_estado: (rest.contexto_estado ?? []).map(({ texto_enviado, ...e }) =>
      e.estado === 'recortado' ? { ...e, texto_enviado } : e,
    ),
  } as AskResult
}

export const corpusUrl = (archivo: string) => `/api/corpus/${encodeURIComponent(archivo)}`
