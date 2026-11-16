import { AlertTriangle, ChevronDown, Clock, Cpu, ExternalLink, Layers, Quote, Scissors, X } from 'lucide-react'
import { m } from 'motion/react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { corpusUrl } from '@/lib/api'
import type { AskResult, ContextoEstado, Recuperado } from '@/lib/types'
import { cn, trackPointer } from '@/lib/utils'
import { FileBadge } from './FileBadge'

interface Props {
  result: AskResult
  focus?: string
  onClose: () => void
}

/** Panel lateral con los fragmentos recuperados, su puntaje, estado en el contexto y citas. */
export default function SourcesPanel({ result, focus, onClose }: Props) {
  const estado = useMemo(() => new Map(result.contexto_estado.map((e) => [e.etiqueta, e])), [result.contexto_estado])
  const cited = useMemo(() => new Set(result.citas.filter((c) => c.valida).map((c) => c.etiqueta)), [result.citas])
  const invalid = result.citas.filter((c) => !c.valida)
  const hybrid = result.recuperados.some((r) => r.score_bm25 !== undefined)
  const maxScore = Math.max(...result.recuperados.map((r) => r.score), 1e-9)
  const docs = useMemo(() => [...new Set(result.recuperados.map((r) => r.archivo))], [result.recuperados])
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeRef.current?.focus({ preventScroll: true })
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    if (!focus) return
    const id = window.setTimeout(() => document.getElementById(`frag-${focus}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 280)
    return () => window.clearTimeout(id)
  }, [focus])

  return (
    <>
      <m.div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />
      <m.aside
        role="dialog"
        aria-modal="true"
        aria-label="Documentos consultados"
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[34rem] flex-col border-l border-white/10 bg-ink-900/95 shadow-2xl shadow-black backdrop-blur-xl"
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 320, damping: 34 }}
      >
        <header className="border-b border-white/5 px-5 pt-5 pb-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs font-medium tracking-wider text-violet-300/80 uppercase">Documentos consultados</p>
              <h2 className="mt-1 line-clamp-2 text-[0.95rem] font-medium text-zinc-100">{result.pregunta}</h2>
            </div>
            <button ref={closeRef} type="button" onClick={onClose} className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/5 hover:text-zinc-200" aria-label="Cerrar panel">
              <X className="size-5" />
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {docs.map((d) => (
              <a key={d} href={corpusUrl(d)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] py-1 pr-2 pl-1 text-xs text-zinc-300 transition hover:border-white/20 hover:text-white">
                <FileBadge archivo={d} small />
                <span className="max-w-[14rem] truncate">{d}</span>
                <ExternalLink className="size-3 text-zinc-500" />
              </a>
            ))}
          </div>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {result.contexto_recortado && (
            <Notice icon={<Scissors className="size-4" />} tone="amber">
              El límite de contexto obligó a recortar u omitir fragmentos antes de enviarlos al modelo.
            </Notice>
          )}
          {invalid.length > 0 && (
            <Notice icon={<AlertTriangle className="size-4" />} tone="rose">
              La respuesta contiene citas que no corresponden a ningún fragmento recuperado: {invalid.map((c) => c.etiqueta).join(', ')}.
            </Notice>
          )}
          {result.recuperados.map((r, i) => (
            <FragmentCard
              key={r.chunk_id + r.etiqueta}
              frag={r}
              index={i}
              estado={estado.get(r.etiqueta)}
              cited={cited.has(r.etiqueta)}
              focused={focus === r.etiqueta}
              hybrid={hybrid}
              relative={r.score / maxScore}
            />
          ))}
        </div>

        <footer className="grid grid-cols-3 gap-2 border-t border-white/5 px-5 py-3 text-[0.7rem] text-zinc-500">
          <Stat icon={<Clock className="size-3.5" />} label="Tiempo" value={`${result.tiempo_total_s.toFixed(2)} s`} hint={`Recuperación ${result.tiempo_recuperacion_s}s · LLM ${result.tiempo_llm_s}s`} />
          <Stat icon={<Layers className="size-3.5" />} label="Contexto" value={result.tokens_contexto != null ? `${result.tokens_contexto} tok` : '—'} hint={`Configuración ${result.configuracion}`} />
          <Stat icon={<Cpu className="size-3.5" />} label="Modelo" value={(result.modelo_servido ?? result.modelo_llm).split('/').pop() ?? '—'} hint={result.modelo_servido ?? result.modelo_llm} />
        </footer>
      </m.aside>
    </>
  )
}

// ------------------------------------------------------------------------------------------------

const ESTADO_STYLE: Record<ContextoEstado['estado'], string> = {
  completo: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300',
  recortado: 'border-amber-400/20 bg-amber-400/10 text-amber-300',
  omitido: 'border-zinc-500/20 bg-zinc-500/10 text-zinc-400',
}

function FragmentCard({ frag, index, estado, cited, focused, hybrid, relative }: {
  frag: Recuperado
  index: number
  estado?: ContextoEstado
  cited: boolean
  focused: boolean
  hybrid: boolean
  relative: number
}) {
  const [open, setOpen] = useState(focused || index === 0)
  useEffect(() => {
    if (focused) setOpen(true)
  }, [focused])

  const shown = estado?.estado === 'recortado' && estado.texto_enviado ? estado.texto_enviado : frag.texto

  return (
    <m.article
      id={`frag-${frag.etiqueta}`}
      onPointerMove={trackPointer}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.08 + index * 0.05, type: 'spring', stiffness: 260, damping: 26 }}
      className={cn(
        'card-spotlight overflow-hidden rounded-2xl border bg-ink-850/80 transition-colors',
        focused ? 'border-violet-400/50 ring-2 ring-violet-400/20' : 'border-white/[0.07] hover:border-white/15',
      )}
    >
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full items-start gap-3 p-4 text-left">
        <span className={cn('mt-0.5 flex h-6 min-w-8 items-center justify-center rounded-lg font-mono text-xs font-semibold', cited ? 'bg-gradient-to-br from-violet-500 to-cyan-500 text-white' : 'bg-ink-700 text-zinc-400')}>
          {frag.etiqueta}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <FileBadge archivo={frag.archivo} small />
            <span className="truncate text-sm font-medium text-zinc-200">{frag.archivo}</span>
          </span>
          <span className="mt-1 block text-xs leading-snug text-zinc-500">{frag.localizador}</span>
          <span className="mt-2.5 flex flex-wrap items-center gap-1.5 text-[0.68rem]">
            {cited && (
              <span className="inline-flex items-center gap-1 rounded-md border border-violet-400/25 bg-violet-400/10 px-1.5 py-px font-medium text-violet-200">
                <Quote className="size-2.5" /> Citado
              </span>
            )}
            {estado && <span className={cn('rounded-md border px-1.5 py-px font-medium', ESTADO_STYLE[estado.estado])}>{estado.estado}</span>}
            <span className="font-mono text-zinc-500">{frag.n_tokens} tok</span>
          </span>
        </span>
        <ChevronDown className={cn('mt-1 size-4 shrink-0 text-zinc-500 transition-transform', open && 'rotate-180')} />
      </button>

      <div className="px-4 pb-1">
        <div className="flex items-center gap-2 text-[0.68rem] text-zinc-500">
          <span className="w-16 shrink-0">{hybrid ? 'RRF' : 'Coseno'}</span>
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/5">
            <m.div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" initial={{ width: 0 }} animate={{ width: `${Math.max(4, relative * 100)}%` }} transition={{ delay: 0.2 + index * 0.05, duration: 0.6, ease: 'easeOut' }} />
          </div>
          <span className="w-14 text-right font-mono tabular-nums">{frag.score.toFixed(hybrid ? 4 : 3)}</span>
        </div>
        {hybrid && (
          <p className="mt-1 pl-[4.5rem] font-mono text-[0.65rem] text-zinc-600">
            denso #{frag.rank_denso} ({frag.score_denso?.toFixed(3)}) · BM25 #{frag.rank_bm25} ({frag.score_bm25?.toFixed(2)})
          </p>
        )}
      </div>

      {open && (
        <div className="px-4 pt-2 pb-4">
          <p className="max-h-72 overflow-y-auto rounded-xl border border-white/5 bg-black/30 p-3 font-mono text-[0.74rem] leading-relaxed whitespace-pre-wrap text-zinc-400">{shown}</p>
          {estado?.estado === 'omitido' && <p className="mt-2 text-xs text-zinc-500">Este fragmento no se envió al modelo por el límite de contexto.</p>}
        </div>
      )}
    </m.article>
  )
}

function Notice({ icon, tone, children }: { icon: React.ReactNode; tone: 'amber' | 'rose'; children: React.ReactNode }) {
  return (
    <div className={cn('flex items-start gap-2 rounded-xl border px-3 py-2.5 text-xs', tone === 'amber' ? 'border-amber-400/20 bg-amber-400/5 text-amber-200' : 'border-rose-400/20 bg-rose-400/5 text-rose-200')}>
      <span className="mt-px shrink-0">{icon}</span>
      <p>{children}</p>
    </div>
  )
}

function Stat({ icon, label, value, hint }: { icon: React.ReactNode; label: string; value: string; hint: string }) {
  return (
    <div title={hint} className="min-w-0">
      <span className="flex items-center gap-1">{icon} {label}</span>
      <span className="mt-0.5 block truncate font-mono text-zinc-300">{value}</span>
    </div>
  )
}
