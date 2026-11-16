import { ArrowRight, LifeBuoy, PanelRight, SquarePen, Volume2, VolumeX } from 'lucide-react'
import { AnimatePresence, m } from 'motion/react'
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ChatMessage } from '@/components/ChatMessage'
import { ConfigSelect } from '@/components/ConfigSelect'
import { FileBadge } from '@/components/FileBadge'
import { HistorySidebar } from '@/components/HistorySidebar'
import { PlaceholdersAndVanishInput } from '@/components/ui/placeholders-and-vanish-input'
import { Spotlight } from '@/components/ui/spotlight'
import { useApiInfo, type ServerStatus } from '@/hooks/useApiInfo'
import { useConversations } from '@/hooks/useConversations'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { ask, corpusUrl } from '@/lib/api'
import { setSoundEnabled, sounds } from '@/lib/sound'
import type { Message } from '@/lib/types'
import { cn, formatBytes, readStorage, trackPointer, uid, writeStorage } from '@/lib/utils'

// El panel de fuentes solo se descarga cuando se abre por primera vez.
const SourcesPanel = lazy(() => import('@/components/SourcesPanel'))

const PREFS_KEY = 'rag-mesa:prefs:v1'
interface Prefs { sound: boolean; history: boolean; config: string | null }

export default function App() {
  const [prefs, setPrefs] = useState<Prefs>(() => ({ sound: true, history: true, config: null, ...readStorage<Partial<Prefs>>(PREFS_KEY, {}) }))
  useEffect(() => {
    writeStorage(PREFS_KEY, prefs)
    setSoundEnabled(prefs.sound)
  }, [prefs])

  const isMobile = useMediaQuery('(max-width: 1023px)')
  const [mobileHistory, setMobileHistory] = useState(false)
  const historyOpen = isMobile ? mobileHistory : prefs.history

  const { conversations, active, activeId, setActiveId, append, updateMessage, remove, clearAll } = useConversations()
  const config = prefs.config ?? 'R0'
  const { info, ready, status, buildError, markReady } = useApiInfo(config)

  useEffect(() => {
    if (info && !prefs.config) setPrefs((p) => ({ ...p, config: info.por_defecto }))
  }, [info, prefs.config])

  const [sources, setSources] = useState<{ messageId: string; focus?: string } | null>(null)
  const [injected, setInjected] = useState<{ value: string; nonce: number } | null>(null)
  const freshIds = useRef(new Set<string>())
  const inflight = useRef<{ ctrl: AbortController; convId: string; msgId: string } | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const messages = active?.messages ?? []
  const pending = messages.some((x) => x.status === 'pending')

  // Desplazamiento suave al final cuando llega un mensaje nuevo.
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: messages.length > 2 ? 'smooth' : 'auto' })
  }, [messages.length, activeId, messages[messages.length - 1]?.status])

  const run = useCallback(async (question: string, convId: string | null) => {
    const now = Date.now()
    const userMsg: Message = { id: uid(), role: 'user', content: question, createdAt: now, config, status: 'done' }
    const botMsg: Message = { id: uid(), role: 'assistant', content: '', createdAt: now, config, status: 'pending', question }
    freshIds.current.add(userMsg.id).add(botMsg.id)
    const id = append(convId, [userMsg, botMsg])
    sounds.send()

    const ctrl = new AbortController()
    inflight.current = { ctrl, convId: id, msgId: botMsg.id }
    try {
      const result = await ask(question, config, ctrl.signal)
      updateMessage(id, botMsg.id, { status: 'done', result, content: result.respuesta })
      markReady(config)
      if (result.tipo === 'total') sounds.notice()
      else sounds.receive()
    } catch (e) {
      const err = e as Error
      const aborted = err.name === 'AbortError'
      updateMessage(id, botMsg.id, { status: 'error', error: aborted ? 'Consulta cancelada.' : err.message })
      if (!aborted) sounds.error()
    } finally {
      if (inflight.current?.msgId === botMsg.id) inflight.current = null
    }
  }, [append, config, markReady, updateMessage])

  const submit = useCallback((q: string) => { void run(q, activeId) }, [run, activeId])
  const cancel = useCallback(() => inflight.current?.ctrl.abort(), [])
  const retry = useCallback((msg: Message) => msg.question && void run(msg.question, activeId), [run, activeId])
  const edit = useCallback((text: string) => setInjected({ value: text, nonce: Date.now() }), [])
  const openSources = useCallback((messageId: string, focus?: string) => {
    sounds.open()
    setSources({ messageId, focus })
  }, [])
  const closeSources = useCallback(() => {
    sounds.close()
    setSources(null)
  }, [])

  const newChat = useCallback(() => {
    sounds.tick()
    setActiveId(null)
    setMobileHistory(false)
  }, [setActiveId])
  const selectConv = useCallback((id: string) => {
    sounds.tick()
    setActiveId(id)
    setMobileHistory(false)
  }, [setActiveId])
  const toggleHistory = () => {
    sounds.tick()
    if (isMobile) setMobileHistory((o) => !o)
    else setPrefs((p) => ({ ...p, history: !p.history }))
  }

  const sourcesResult = useMemo(() => messages.find((x) => x.id === sources?.messageId)?.result, [messages, sources])
  const placeholders = useMemo(() => (info?.sugerencias.length ? info.sugerencias : ['Escribe tu pregunta sobre VPN, cuentas, correo, impresión o SLA…']), [info])

  return (
    <div className="flex h-dvh overflow-hidden">
      <main className="relative flex min-w-0 flex-1 flex-col">
        {/* Fondo: cuadrícula + spotlight (CSS/SVG estático, sin coste de JS por fotograma) */}
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="bg-grid absolute inset-0" />
          <Spotlight className="-top-40 left-0 md:-top-20 md:left-60" fill="#a78bfa" />
          <div className="absolute -top-32 right-0 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        </div>

        <header className="relative z-20 flex items-center gap-3 border-b border-white/[0.06] bg-ink-950/60 px-4 py-3 backdrop-blur-xl sm:px-6">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 shadow-lg shadow-violet-500/25">
            <LifeBuoy className="size-5 text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold text-zinc-100">Mesa de Ayuda TI</h1>
            <p className="truncate text-xs text-zinc-500">Andina Tech · Asistente RAG con citas</p>
          </div>
          <StatusPill status={status} error={buildError} />
          {info && <ConfigSelect configs={info.configuraciones} value={config} ready={ready} onChange={(c) => { sounds.tick(); setPrefs((p) => ({ ...p, config: c })) }} />}
          <IconButton label={prefs.sound ? 'Silenciar sonidos' : 'Activar sonidos'} onClick={() => setPrefs((p) => ({ ...p, sound: !p.sound }))}>
            {prefs.sound ? <Volume2 className="size-4" /> : <VolumeX className="size-4" />}
          </IconButton>
          <IconButton label="Nueva conversación" onClick={newChat} className="hidden sm:inline-flex">
            <SquarePen className="size-4" />
          </IconButton>
          <IconButton label={historyOpen ? 'Ocultar historial' : 'Mostrar historial'} onClick={toggleHistory} active={historyOpen}>
            <PanelRight className="size-4" />
          </IconButton>
        </header>

        <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto">
          <AnimatePresence mode="wait" initial={false}>
            {messages.length === 0 ? (
              <EmptyState key="empty" suggestions={info?.sugerencias ?? []} corpus={info?.corpus ?? []} onPick={submit} disabled={pending} />
            ) : (
              <m.div key={activeId} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="mx-auto w-full max-w-3xl space-y-7 px-4 pt-8 pb-6 sm:px-6">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} fresh={freshIds.current.has(msg.id)} onOpenSources={openSources} onRetry={retry} onEdit={edit} onCancel={cancel} />
                ))}
              </m.div>
            )}
          </AnimatePresence>
        </div>

        <div className="relative z-20 px-4 pt-2 pb-4 sm:px-6">
          <div className="mx-auto max-w-3xl">
            <PlaceholdersAndVanishInput placeholders={placeholders} onSubmit={submit} disabled={pending || status === 'offline'} injected={injected} />
            <p className="mt-2 text-center text-[0.68rem] text-zinc-600">
              Responde solo con los documentos del corpus (sintético) y cita la evidencia. Cada pregunta se responde de forma independiente.
            </p>
          </div>
        </div>
      </main>

      <HistorySidebar
        open={historyOpen}
        overlay={isMobile}
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConv}
        onNew={newChat}
        onDelete={remove}
        onClearAll={clearAll}
        onClose={() => setMobileHistory(false)}
      />

      <AnimatePresence>
        {sources && sourcesResult && (
          <Suspense fallback={null}>
            <SourcesPanel key="sources" result={sourcesResult} focus={sources.focus} onClose={closeSources} />
          </Suspense>
        )}
      </AnimatePresence>
    </div>
  )
}

// ------------------------------------------------------------------------------------------------

function IconButton({ label, onClick, children, active, className }: { label: string; onClick: () => void; children: React.ReactNode; active?: boolean; className?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={cn('inline-flex size-8 items-center justify-center rounded-xl text-zinc-400 transition hover:bg-white/5 hover:text-zinc-100', active && 'bg-white/[0.06] text-zinc-100', className)}
    >
      {children}
    </button>
  )
}

const STATUS: Record<ServerStatus, { label: string; dot: string }> = {
  connecting: { label: 'Conectando', dot: 'bg-zinc-500' },
  warming: { label: 'Preparando índice', dot: 'bg-amber-400 animate-pulse' },
  ready: { label: 'Listo', dot: 'bg-emerald-400' },
  offline: { label: 'API sin conexión', dot: 'bg-rose-500' },
}

function StatusPill({ status, error }: { status: ServerStatus; error: string | null }) {
  const s = error ? { label: 'Error al indexar', dot: 'bg-rose-500' } : STATUS[status]
  return (
    <span title={error ?? s.label} className="hidden items-center gap-1.5 rounded-full border border-white/[0.07] px-2.5 py-1 text-[0.68rem] text-zinc-400 md:inline-flex">
      <span className={cn('size-1.5 rounded-full', s.dot)} />
      {s.label}
    </span>
  )
}

function EmptyState({ suggestions, corpus, onPick, disabled }: {
  suggestions: string[]
  corpus: { archivo: string; formato: string; bytes: number }[]
  onPick: (q: string) => void
  disabled: boolean
}) {
  const picks = suggestions.slice(0, 4)
  return (
    <m.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.3 }} className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center px-4 py-10 sm:px-6">
      <m.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="mb-3 inline-flex w-fit items-center gap-2 rounded-full border border-violet-400/20 bg-violet-400/10 px-3 py-1 text-xs text-violet-200">
        <span className="size-1.5 rounded-full bg-violet-300" /> Recuperación aumentada con citas verificables
      </m.p>
      <h2 className="bg-gradient-to-b from-white to-zinc-500 bg-clip-text text-4xl font-semibold tracking-tight text-transparent sm:text-5xl">
        ¿En qué te ayudo hoy?
      </h2>
      <p className="mt-3 max-w-xl text-[0.95rem] text-zinc-400">
        Pregunta sobre VPN, cuentas y contraseñas, correo, impresión, tiempos de atención o seguridad del puesto de trabajo.
        Cada respuesta indica de qué documento sale.
      </p>

      {picks.length > 0 && (
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {picks.map((q, i) => (
            <m.button
              key={q}
              type="button"
              disabled={disabled}
              onClick={() => onPick(q)}
              onPointerMove={trackPointer}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.06, type: 'spring', stiffness: 260, damping: 24 }}
              className="card-spotlight group flex items-start justify-between gap-3 rounded-2xl border border-white/[0.07] bg-ink-850/70 p-4 text-left text-sm text-zinc-300 transition hover:border-white/15 hover:text-zinc-100 disabled:opacity-50"
            >
              <span>{q}</span>
              <ArrowRight className="mt-0.5 size-4 shrink-0 text-zinc-600 transition group-hover:translate-x-0.5 group-hover:text-violet-300" />
            </m.button>
          ))}
        </div>
      )}

      {corpus.length > 0 && (
        <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.45 }} className="mt-8">
          <p className="mb-2 text-[0.68rem] font-medium tracking-wider text-zinc-600 uppercase">Documentos indexados</p>
          <div className="flex flex-wrap gap-2">
            {corpus.map((d) => (
              <a key={d.archivo} href={corpusUrl(d.archivo)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-xl border border-white/[0.07] bg-white/[0.02] py-1.5 pr-3 pl-1.5 text-xs text-zinc-400 transition hover:border-white/15 hover:text-zinc-200">
                <FileBadge archivo={d.archivo} small />
                {d.archivo}
                <span className="text-zinc-600">{formatBytes(d.bytes)}</span>
              </a>
            ))}
          </div>
        </m.div>
      )}
    </m.div>
  )
}
