import { AnimatePresence, m } from 'motion/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

/**
 * Aceternity UI — Placeholders And Vanish Input (adaptado).
 * Rota los placeholders y, al enviar, el texto se desintegra en partículas dibujadas en un canvas.
 * Cambios: tipado estricto, estado deshabilitado, el canvas solo trabaja durante la animación
 * y se respeta `prefers-reduced-motion`.
 */
interface Props {
  placeholders: string[]
  onSubmit: (value: string) => void
  disabled?: boolean
  /** Permite precargar texto desde fuera (p. ej., al elegir una sugerencia). */
  injected?: { value: string; nonce: number } | null
}

interface Particle {
  x: number
  y: number
  r: number
  color: string
}

export function PlaceholdersAndVanishInput({ placeholders, onSubmit, disabled, injected }: Props) {
  const [current, setCurrent] = useState(0)
  const [value, setValue] = useState('')
  const [animating, setAnimating] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const particles = useRef<Particle[]>([])

  // Rotación de placeholders; se pausa cuando la pestaña no es visible.
  useEffect(() => {
    if (placeholders.length < 2) return
    let id: number | undefined
    const start = () => (id = window.setInterval(() => setCurrent((p) => (p + 1) % placeholders.length), 3500))
    const onVis = () => {
      window.clearInterval(id)
      if (document.visibilityState === 'visible') start()
    }
    start()
    document.addEventListener('visibilitychange', onVis)
    return () => {
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [placeholders.length])

  useEffect(() => {
    if (!injected) return
    setValue(injected.value)
    inputRef.current?.focus()
  }, [injected])

  const draw = useCallback(() => {
    const input = inputRef.current
    const canvas = canvasRef.current
    if (!input || !canvas) return
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return
    canvas.width = 800
    canvas.height = 800
    ctx.clearRect(0, 0, 800, 800)
    const cs = getComputedStyle(input)
    const fontSize = parseFloat(cs.getPropertyValue('font-size'))
    ctx.font = `${fontSize * 2}px ${cs.fontFamily}`
    ctx.fillStyle = '#FFF'
    ctx.fillText(value, 16, 40)

    const { data } = ctx.getImageData(0, 0, 800, 800)
    const out: Particle[] = []
    for (let y = 0; y < 800; y += 2) {
      const row = 4 * y * 800
      for (let x = 0; x < 800; x += 2) {
        const e = row + 4 * x
        if (data[e] !== 0 && data[e + 1] !== 0 && data[e + 2] !== 0) {
          out.push({ x, y, r: 1, color: `rgba(${data[e]}, ${data[e + 1]}, ${data[e + 2]}, ${data[e + 3] / 255})` })
        }
      }
    }
    particles.current = out
  }, [value])

  const animate = (start: number) => {
    const frame = (pos: number) => {
      requestAnimationFrame(() => {
        const next: Particle[] = []
        for (const p of particles.current) {
          if (p.x < pos) next.push(p)
          else {
            if (p.r <= 0) continue
            p.x += Math.random() > 0.5 ? 1 : -1
            p.y += Math.random() > 0.5 ? 1 : -1
            p.r -= 0.05 * Math.random()
            next.push(p)
          }
        }
        particles.current = next
        const ctx = canvasRef.current?.getContext('2d')
        if (ctx) {
          ctx.clearRect(pos, 0, 800, 800)
          for (const { x, y, r, color } of next) {
            if (x > pos) {
              ctx.beginPath()
              ctx.rect(x, y, r, r)
              ctx.fillStyle = color
              ctx.strokeStyle = color
              ctx.stroke()
            }
          }
        }
        if (next.length > 0) frame(pos - 8)
        else {
          setValue('')
          setAnimating(false)
        }
      })
    }
    frame(start)
  }

  const vanishAndSubmit = () => {
    const text = value.trim()
    if (!text || disabled || animating) return
    onSubmit(text)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setValue('')
      return
    }
    setAnimating(true)
    draw()
    const maxX = particles.current.reduce((acc, p) => (p.x > acc ? p.x : acc), 0)
    animate(maxX)
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        vanishAndSubmit()
      }}
      className={cn(
        'relative mx-auto h-14 w-full overflow-hidden rounded-2xl border border-white/10 bg-ink-850/90 shadow-[0_8px_40px_-12px_rgb(139_92_246/0.35)] backdrop-blur-xl transition duration-200 focus-within:border-violet-400/40',
        value && 'bg-ink-800/90',
      )}
    >
      <canvas
        ref={canvasRef}
        className={cn(
          'pointer-events-none absolute top-[20%] left-2 origin-top-left scale-50 pr-20 invert-0 sm:left-4',
          animating ? 'opacity-100' : 'opacity-0',
        )}
      />
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => !animating && setValue(e.target.value)}
        disabled={disabled && !value}
        maxLength={2000}
        aria-label="Escribe tu pregunta"
        autoComplete="off"
        type="text"
        className={cn(
          'relative z-10 h-full w-full rounded-2xl border-none bg-transparent pr-16 pl-4 text-[0.95rem] text-zinc-100 focus:ring-0 focus:outline-none sm:pl-6',
          animating && 'text-transparent',
        )}
      />
      <button
        type="submit"
        disabled={!value || disabled || animating}
        aria-label="Enviar pregunta"
        className="absolute top-1/2 right-2.5 z-20 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 text-white shadow-lg shadow-violet-500/20 transition duration-200 hover:brightness-110 disabled:from-ink-700 disabled:to-ink-700 disabled:text-zinc-500 disabled:shadow-none"
      >
        <m.svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
          <m.path d="M5 12l14 0" initial={{ strokeDasharray: '50%', strokeDashoffset: '50%' }} animate={{ strokeDashoffset: value ? 0 : '50%' }} transition={{ duration: 0.3, ease: 'linear' }} />
          <path d="M13 18l6 -6" />
          <path d="M13 6l6 6" />
        </m.svg>
      </button>

      <div className="pointer-events-none absolute inset-0 flex items-center rounded-2xl">
        <AnimatePresence mode="wait">
          {!value && (
            <m.p
              key={`ph-${current}`}
              initial={{ y: 5, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -15, opacity: 0 }}
              transition={{ duration: 0.3, ease: 'linear' }}
              className="w-[calc(100%-4.5rem)] truncate pl-4 text-left text-[0.95rem] text-zinc-500 sm:pl-6"
            >
              {placeholders[current] ?? 'Escribe tu pregunta…'}
            </m.p>
          )}
        </AnimatePresence>
      </div>
    </form>
  )
}
