import { MessageSquare, Plus, Search, Trash2, X } from 'lucide-react'
import { AnimatePresence, m } from 'motion/react'
import { memo, useMemo, useState } from 'react'
import type { Conversation } from '@/lib/types'
import { cn, dayBucket, relativeTime } from '@/lib/utils'

interface Props {
  open: boolean
  overlay: boolean
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  onClearAll: () => void
  onClose: () => void
}

const WIDTH = 320

/** Columna derecha desplegable con el historial (Aceternity "Sidebar", animada con Motion). */
function HistorySidebarImpl(props: Props) {
  const { open, overlay, onClose } = props
  if (overlay) {
    return (
      <AnimatePresence>
        {open && (
          <>
            <m.div className="fixed inset-0 z-30 bg-black/50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
            <m.aside
              className="fixed inset-y-0 right-0 z-40 w-[min(85vw,20rem)] border-l border-white/10 bg-ink-900"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 320, damping: 34 }}
            >
              <Content {...props} />
            </m.aside>
          </>
        )}
      </AnimatePresence>
    )
  }
  return (
    <m.aside
      aria-hidden={!open}
      className="relative shrink-0 overflow-hidden border-l border-white/[0.06] bg-ink-900/70"
      initial={false}
      animate={{ width: open ? WIDTH : 0, opacity: open ? 1 : 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 34 }}
      inert={!open}
    >
      <div style={{ width: WIDTH }} className="h-full">
        <Content {...props} />
      </div>
    </m.aside>
  )
}

export const HistorySidebar = memo(HistorySidebarImpl)

function Content({ conversations, activeId, onSelect, onNew, onDelete, onClearAll, onClose, overlay }: Props) {
  const [query, setQuery] = useState('')
  const [confirmId, setConfirmId] = useState<string | null>(null)

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = q
      ? conversations.filter((c) => c.title.toLowerCase().includes(q) || c.messages.some((msg) => msg.content.toLowerCase().includes(q)))
      : conversations
    const map = new Map<string, Conversation[]>()
    for (const c of list) {
      const k = dayBucket(c.updatedAt)
      map.set(k, [...(map.get(k) ?? []), c])
    }
    return [...map.entries()]
  }, [conversations, query])

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 pt-4 pb-3">
        <h2 className="text-sm font-semibold text-zinc-200">Historial</h2>
        <div className="flex items-center gap-1">
          <button type="button" onClick={onNew} className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-zinc-300 transition hover:bg-white/10" title="Nueva conversación">
            <Plus className="size-3.5" /> Nueva
          </button>
          {overlay && (
            <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-zinc-500 hover:bg-white/5 hover:text-zinc-200" aria-label="Cerrar historial">
              <X className="size-4" />
            </button>
          )}
        </div>
      </div>

      <label className="mx-4 mb-2 flex items-center gap-2 rounded-xl border border-white/[0.07] bg-ink-850 px-3 py-2 focus-within:border-violet-400/40">
        <Search className="size-3.5 text-zinc-500" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar conversaciones" className="w-full bg-transparent text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none" />
      </label>

      <nav className="flex-1 overflow-y-auto px-2 pb-3">
        {groups.length === 0 && (
          <p className="px-3 py-8 text-center text-xs text-zinc-600">{query ? 'Sin resultados.' : 'Tus conversaciones aparecerán aquí.'}</p>
        )}
        {groups.map(([label, items]) => (
          <section key={label} className="mt-3">
            <h3 className="px-3 pb-1 text-[0.65rem] font-medium tracking-wider text-zinc-600 uppercase">{label}</h3>
            <ul>
              <AnimatePresence initial={false}>
                {items.map((c) => {
                  const active = c.id === activeId
                  const turns = c.messages.filter((x) => x.role === 'user').length
                  return (
                    <m.li key={c.id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 12, height: 0 }} className="group relative">
                      <button
                        type="button"
                        onClick={() => onSelect(c.id)}
                        className={cn('flex w-full items-start gap-2.5 rounded-xl px-3 py-2 text-left transition', active ? 'bg-white/[0.07]' : 'hover:bg-white/[0.04]')}
                      >
                        {active && <m.span layoutId="active-conv" className="absolute top-2 bottom-2 left-0 w-0.5 rounded-full bg-gradient-to-b from-violet-400 to-cyan-400" />}
                        <MessageSquare className={cn('mt-0.5 size-3.5 shrink-0', active ? 'text-violet-300' : 'text-zinc-600')} />
                        <span className="min-w-0 flex-1 pr-6">
                          <span className={cn('block truncate text-[0.8rem]', active ? 'text-zinc-100' : 'text-zinc-400')}>{c.title}</span>
                          <span className="text-[0.68rem] text-zinc-600">
                            {turns} {turns === 1 ? 'pregunta' : 'preguntas'} · {relativeTime(c.updatedAt)}
                          </span>
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => (confirmId === c.id ? onDelete(c.id) : setConfirmId(c.id))}
                        onBlur={() => setConfirmId(null)}
                        className={cn(
                          'absolute top-2 right-2 rounded-lg p-1.5 transition focus-visible:opacity-100',
                          confirmId === c.id ? 'bg-rose-500/15 text-rose-300 opacity-100' : 'text-zinc-600 opacity-0 group-hover:opacity-100 hover:text-zinc-300',
                        )}
                        aria-label={confirmId === c.id ? 'Confirmar eliminación' : 'Eliminar conversación'}
                        title={confirmId === c.id ? 'Clic de nuevo para eliminar' : 'Eliminar'}
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </m.li>
                  )
                })}
              </AnimatePresence>
            </ul>
          </section>
        ))}
      </nav>

      {conversations.length > 0 && (
        <div className="border-t border-white/5 p-3">
          <button
            type="button"
            onClick={() => window.confirm('¿Eliminar todo el historial de conversaciones?') && onClearAll()}
            className="w-full rounded-lg px-3 py-1.5 text-xs text-zinc-600 transition hover:bg-rose-500/10 hover:text-rose-300"
          >
            Borrar historial
          </button>
        </div>
      )}
    </div>
  )
}
