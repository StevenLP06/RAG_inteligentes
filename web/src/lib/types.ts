/** Tipos que reflejan la salida de `RAGSystem.ask()` (rag/pipeline.py) expuesta por api/server.py. */

export interface Recuperado {
  rank: number
  etiqueta: string
  chunk_id: string
  archivo: string
  formato: string
  localizador: string
  n_tokens: number
  texto: string
  score: number
  score_denso?: number
  rank_denso?: number
  score_bm25?: number
  rank_bm25?: number
}

export type EstadoContexto = 'completo' | 'recortado' | 'omitido'

export interface ContextoEstado {
  etiqueta: string
  chunk_id: string
  estado: EstadoContexto
  tokens: number
  /** Solo se conserva cuando el fragmento se recortó (en los demás casos coincide con `texto`). */
  texto_enviado?: string
}

export interface Cita {
  etiqueta: string
  valida: boolean
  archivo: string | null
  localizador: string | null
  chunk_id: string | null
}

export type TipoRespuesta = 'total' | 'parcial' | 'sustantiva'

export interface AskResult {
  pregunta: string
  configuracion: string
  recuperados: Recuperado[]
  contexto_estado: ContextoEstado[]
  contexto_recortado: boolean | null
  tokens_contexto?: number
  respuesta: string
  modelo_llm: string
  modelo_servido: string | null
  proveedor_servido: string | null
  abstencion: boolean
  tipo: TipoRespuesta
  citas: Cita[]
  tiempo_recuperacion_s: number
  tiempo_llm_s: number
  tiempo_total_s: number
}

export interface ConfigInfo {
  nombre: string
  descripcion: string
  usa_rag: boolean
  recuperacion: 'dense' | 'hybrid' | null
  fragmentacion: 'fixed' | 'structural' | null
  k: number | null
  llm: string
  embeddings: string | null
  grupo: 'A' | 'B' | 'extra'
  lista: boolean
}

export interface CorpusDoc {
  archivo: string
  formato: string
  bytes: number
}

export interface ApiInfo {
  configuraciones: ConfigInfo[]
  por_defecto: string
  corpus: CorpusDoc[]
  sugerencias: string[]
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: number
  config: string
  status: 'pending' | 'done' | 'error'
  result?: AskResult
  error?: string
  /** Pregunta original (en mensajes del asistente) para poder reintentar. */
  question?: string
}

export interface Conversation {
  id: string
  title: string
  createdAt: number
  updatedAt: number
  messages: Message[]
}
