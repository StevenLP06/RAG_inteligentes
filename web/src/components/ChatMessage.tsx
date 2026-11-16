import { AlertTriangle, Check, Copy, FileSearch, Pencil, RotateCcw, ShieldAlert, Sparkles, X } from 'lucide-react'
import { m } from 'motion/react'
import { memo, useEffect, useMemo, useState } from 'react'
import type { Message } from '@/lib/types'
import { clockTime, cn } from '@/lib/utils'
import { AnswerContent } from './AnswerContent'

interface Props {
  message: Message
  /** Solo las respuestas recién llegadas se animan; las del historial se muestran estáticas. */
  fresh: boolean
  onOpenSources: (messageId: string, label?: string) => void
  onRetry: (message: Message) => void
  onEdit: (text: string) => void
  onCancel: () => void
}

const ABSTAIN_PREFIX = /^\s*(EVIDENCIA INSUFICIENTE|NO TENGO INFORMACIÓN SUFICIENTE)\s*:\s*/i

function ChatMessageImpl({ message, fresh, onOpenSources, onRetry, onEdit, onCancel }: Props) {
  if (message.role === 'user') {
    return (
      <m.div initial={fresh ? { opacity: 0, y: 12 } : false} animate={{ opacity: 1, y: 0 }} transition={{ type: 'spring', stiffness: 380, damping: 30 }} className="group flex justify-end">
        <div className="flex max-w-[85%] items-start gap-2">
          <button
            type="button"
            onClick={() => onEdit(message.content)}
            className="mt-2 rounded-lg p-1.5 text-zinc-600 opacity-0 transition group-hover:opacity-100 hover:bg-white/5 hover:text-zinc-300 focus-visible:opacity-100"
            aria-label="Editar y volver a preguntar"
            title="Editar y volver a preguntar"
          >
            <Pencil className="size-3.5" />
          </button>
          <div className="rounded-2xl rounded-tr-md border border-violet-400/15 bg-gradient-to-br from-violet-500/20 to-cyan-500/10 px-4 py-2.5 text-[0.94rem] leading-relaxed whitespace-pre-wrap text-zinc-100 shadow-lg shadow-violet-950/30">
            {message.content}
          </div>
        </div>
      </m.div>
    )
  }

  return (
    <m.div initial={fresh ? { opacity: 0, y: 12 } : false} animate={{ opacity: 1, y: 0 }} transition={{ type: 'spring', stiffness: 300, damping: 30 }} className="flex gap-3">
      <div className="relative mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-ink-800">
        <Sparkles className="size-4 text-violet-300" />
        {message.status === 'pending' && <span className="absolute inset-0 animate-ping rounded-xl border border-violet-400/40" />}
      </div>
      <div className="min-w-0 flex-1 pt-0.5">
        {message.status === 'pending' && <Pending onCancel={onCancel} since={message.createdAt} config={message.config} />}
        {message.status === 'error' && <ErrorBubble message={message} onRetry={onRetry} />}
        {message.status === 'done' && message.result && <Answer message={message} fresh={fresh} onOpenSources={onOpenSources} />}
      </div>
    </m.div>
  )
}

export const ChatMessage = memo(ChatMessageImpl)

// ------------------------------------------------------------------------------------------------

function Pending({ since, config, onCancel }: { since: number; config: string; onCancel: () => void }) {
  const [elapsed, setElapsed] = useState(() => Math.max(0, (Date.now() - since) / 1000))
  useEffect(() => {
    const id = window.setInterval(() => setElapsed((Date.now() - since) / 1000), 100)
    return () => window.clearInterval(id)
  }, [since])
  const phase = config === 'C0' ? 'Consultando al modelo sin documentos' : elapsed < 1.2 ? 'Buscando fragmentos relevantes' : 'Generando respuesta con evidencia'
  return (
    <div className="flex flex-wrap items-center gap-3 py-1.5">
      <span className="text-shimmer text-[0.94rem] font-medium">{phase}…</span>
      <span className="font-mono text-xs text-zinc-600 tabular-nums">{elapsed.toFixed(1)} s</span>
      <button type="button" onClick={onCancel} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-zinc-500 transition hover:bg-white/5 hover:text-zinc-300">
        <X className="size-3" /> Cancelar
      </button>
    </div>
  )
}

function ErrorBubble({ message, onRetry }: { message: Message; onRetry: (m: Message) => void }) {
  return (
    <div className="rounded-2xl rounded-tl-md border border-rose-500/20 bg-rose-500/5 px-4 py-3">
      <div className="flex items-start gap-2 text-sm text-rose-200">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-rose-400" />
        <p className="break-words">{message.error ?? 'Ocurrió un error inesperado.'}</p>
      </div>
      {message.question && (
        <button type="button" onClick={() => onRetry(message)} className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-zinc-300 transition hover:bg-white/10">
          <RotateCcw className="size-3" /> Reintentar
        </button>
      )}
    </div>
  )
}

function Answer({ message, fresh, onOpenSources }: { message: Message; fresh: boolean; onOpenSources: Props['onOpenSources'] }) {
  const r = message.result!
  const [copied, setCopied] = useState(false)
  const citedValid = useMemo(() => new Set(r.recuperados.map((x) => x.etiqueta)), [r.recuperados])
  const nCited = useMemo(() => new Set(r.citas.filter((c) => c.valida).map((c) => c.etiqueta)).size, [r.citas])
  const isAbstention = r.tipo === 'total'
  const text = isAbstention ? r.respuesta.replace(ABSTAIN_PREFIX, '') : r.respuesta

  const copy = () => {
    void navigator.clipboard?.writeText(r.respuesta).then(() => {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div>
      {isAbstention && (
        <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-amber-400/25 bg-amber-400/10 px-2.5 py-0.5 text-xs font-medium text-amber-200">
          <ShieldAlert className="size-3.5" /> {r.configuracion === 'C0' ? 'Sin información suficiente' : 'Evidencia insuficiente en los documentos'}
        </div>
      )}
      {r.tipo === 'parcial' && (
        <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-sky-400/25 bg-sky-400/10 px-2.5 py-0.5 text-xs font-medium text-sky-200">
          <ShieldAlert className="size-3.5" /> Respuesta parcial: parte de la pregunta no está cubierta
        </div>
      )}

      <AnswerContent text={text} animate={fresh} citedValid={citedValid} onCite={(label) => onOpenSources(message.id, label)} />

      <div className={cn('mt-3 flex flex-wrap items-center gap-2', fresh && 'animate-word-in [animation-delay:0.4s]')}>
        {r.recuperados.length > 0 && (
          <button
            type="button"
            onClick={() => onOpenSources(message.id)}
            className="moving-border group inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-medium text-zinc-200 transition hover:text-white"
          >
            <FileSearch className="size-3.5 text-violet-300 transition group-hover:scale-110" />
            Ver {r.recuperados.length} documentos consultados
            {nCited > 0 && <span className="rounded-md bg-violet-400/15 px-1.5 py-px font-mono text-[0.65rem] text-violet-200">{nCited} citados</span>}
          </button>
        )}
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs text-zinc-500 transition hover:bg-white/5 hover:text-zinc-200"
          aria-label="Copiar respuesta"
        >
          {copied ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
          {copied ? 'Copiado' : 'Copiar'}
        </button>
        <span className="ml-auto flex items-center gap-2 font-mono text-[0.68rem] text-zinc-600">
          <span className="rounded-md border border-white/10 px-1.5 py-px text-zinc-400" title="Configuración usada">{r.configuracion}</span>
          <span title={`Recuperación ${r.tiempo_recuperacion_s}s · LLM ${r.tiempo_llm_s}s`}>{r.tiempo_total_s.toFixed(1)} s</span>
          <span>· {clockTime(message.createdAt)}</span>
        </span>
      </div>
    </div>
  )
}
