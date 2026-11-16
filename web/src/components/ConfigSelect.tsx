import { Check, ChevronDown, Settings2 } from 'lucide-react'
import { AnimatePresence, m } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import type { ConfigInfo } from '@/lib/types'
import { cn } from '@/lib/utils'

const GROUP_LABEL = { A: 'Parte A', B: 'Experimento B', extra: 'Opcional' } as const

function tag(c: ConfigInfo) {
  if (!c.usa_rag) return 'Sin documentos'
  return `${c.fragmentacion === 'structural' ? 'Estructural' : 'Fija'} · ${c.recuperacion === 'hybrid' ? 'Híbrida' : 'Densa'} · k=${c.k}`
}

export function ConfigSelect({ configs, value, ready, onChange }: {
  configs: ConfigInfo[]
  value: string
  ready: string[]
  onChange: (name: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => !ref.current?.contains(e.target as Node) && setOpen(false)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-zinc-300 transition hover:border-white/20"
        title="Configuración del RAG"
      >
        <Settings2 className="size-3.5 text-violet-300" />
        <span className="font-mono font-semibold">{value}</span>
        <ChevronDown className={cn('size-3.5 text-zinc-500 transition-transform', open && 'rotate-180')} />
      </button>
      <AnimatePresence>
        {open && (
          <m.ul
            role="listbox"
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-50 mt-2 max-h-[70vh] w-[min(22rem,calc(100vw-2rem))] origin-top-right overflow-y-auto rounded-2xl border border-white/10 bg-ink-850/95 p-1.5 shadow-2xl shadow-black/60 backdrop-blur-xl"
          >
            {configs.map((c, i) => (
              <li key={c.nombre}>
                {(i === 0 || configs[i - 1].grupo !== c.grupo) && (
                  <p className="px-2.5 pt-2 pb-1 text-[0.62rem] font-medium tracking-wider text-zinc-600 uppercase">{GROUP_LABEL[c.grupo]}</p>
                )}
                <button
                  type="button"
                  role="option"
                  aria-selected={c.nombre === value}
                  onClick={() => {
                    onChange(c.nombre)
                    setOpen(false)
                  }}
                  title={c.descripcion}
                  className={cn('flex w-full items-start gap-2.5 rounded-xl px-2.5 py-2 text-left transition', c.nombre === value ? 'bg-white/[0.06]' : 'hover:bg-white/[0.04]')}
                >
                  <span className="mt-px w-10 font-mono text-xs font-semibold text-zinc-200">{c.nombre}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-xs text-zinc-300">{tag(c)}</span>
                    <span className="line-clamp-2 text-[0.68rem] leading-snug text-zinc-500">{c.descripcion}</span>
                  </span>
                  <span className="mt-1 flex items-center gap-1.5">
                    <span className={cn('size-1.5 rounded-full', ready.includes(c.nombre) ? 'bg-emerald-400' : 'bg-zinc-600')} title={ready.includes(c.nombre) ? 'Índice listo' : 'Se construirá en la primera pregunta'} />
                    {c.nombre === value && <Check className="size-3.5 text-violet-300" />}
                  </span>
                </button>
              </li>
            ))}
          </m.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
