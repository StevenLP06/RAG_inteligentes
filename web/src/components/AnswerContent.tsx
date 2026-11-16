import { memo, type ReactNode } from 'react'

/**
 * Renderiza la respuesta del LLM: párrafos, listas, **negritas** y citas [F#] como chips clicables.
 * Con `animate`, las palabras aparecen en cascada (Aceternity "Text Generate Effect") usando una
 * animación CSS por palabra en lugar de un componente de Motion por palabra (más ligero).
 */
interface Props {
  text: string
  animate?: boolean
  citedValid: Set<string>
  onCite: (label: string) => void
}

type Block = { kind: 'p'; text: string } | { kind: 'ul' | 'ol'; items: string[] }

const LIST_UL = /^\s*[-*•]\s+/
const LIST_OL = /^\s*\d+[.)]\s+/

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = []
  for (const chunk of text.replace(/\r/g, '').split(/\n{2,}/)) {
    const lines = chunk.split('\n').filter((l) => l.trim())
    let para: string[] = []
    const flushPara = () => {
      if (para.length) blocks.push({ kind: 'p', text: para.join(' ') })
      para = []
    }
    for (const line of lines) {
      const kind = LIST_UL.test(line) ? 'ul' : LIST_OL.test(line) ? 'ol' : null
      if (!kind) {
        para.push(line.trim())
        continue
      }
      flushPara()
      const item = line.replace(kind === 'ul' ? LIST_UL : LIST_OL, '')
      const last = blocks[blocks.length - 1]
      if (last && last.kind === kind) last.items.push(item)
      else blocks.push({ kind, items: [item] })
    }
    flushPara()
  }
  return blocks
}

const TOKEN = /(\[F\d+\]|\*\*[^*]+\*\*)/g
const WORD_STEP = 0.018 // s entre palabras
const MAX_DELAY = 1.4 // s: el efecto nunca tarda más que esto, aunque la respuesta sea larga

function AnswerContentImpl({ text, animate = false, citedValid, onCite }: Props) {
  let word = 0
  const words = (s: string, keyBase: string, strong = false): ReactNode[] =>
    s.split(/(\s+)/).map((w, i) => {
      if (!w) return null
      if (!animate || /^\s+$/.test(w)) return strong ? <strong key={`${keyBase}-${i}`} className="font-semibold text-zinc-50">{w}</strong> : w
      const delay = Math.min(word++ * WORD_STEP, MAX_DELAY)
      const cls = strong ? 'inline-block animate-word-in font-semibold text-zinc-50' : 'inline-block animate-word-in'
      return (
        <span key={`${keyBase}-${i}`} className={cls} style={{ animationDelay: `${delay}s` }}>
          {w}
        </span>
      )
    })

  const inline = (s: string, keyBase: string): ReactNode[] =>
    s.split(TOKEN).map((part, i) => {
      const key = `${keyBase}-${i}`
      const cite = /^\[(F\d+)\]$/.exec(part)
      if (cite) {
        const label = cite[1]
        const valid = citedValid.has(label)
        const delay = animate ? Math.min(word * WORD_STEP, MAX_DELAY) : 0
        return (
          <button
            key={key}
            type="button"
            onClick={() => onCite(label)}
            title={valid ? `Ver fragmento ${label}` : `${label} no corresponde a un fragmento recuperado`}
            className={animate ? 'cite-chip animate-word-in' : 'cite-chip'}
            style={animate ? { animationDelay: `${delay}s` } : undefined}
            data-invalid={!valid || undefined}
          >
            {label}
          </button>
        )
      }
      if (part.startsWith('**') && part.endsWith('**')) return <span key={key}>{words(part.slice(2, -2), key, true)}</span>
      return <span key={key}>{words(part, key)}</span>
    })

  return (
    <div className="space-y-3 text-[0.94rem] leading-relaxed text-zinc-300">
      {parseBlocks(text).map((b, i) =>
        b.kind === 'p' ? (
          <p key={i}>{inline(b.text, `p${i}`)}</p>
        ) : b.kind === 'ul' ? (
          <ul key={i} className="list-disc space-y-1.5 pl-5 marker:text-violet-400/70">
            {b.items.map((it, j) => <li key={j}>{inline(it, `u${i}-${j}`)}</li>)}
          </ul>
        ) : (
          <ol key={i} className="list-decimal space-y-1.5 pl-5 marker:text-violet-400/70">
            {b.items.map((it, j) => <li key={j}>{inline(it, `o${i}-${j}`)}</li>)}
          </ol>
        ),
      )}
    </div>
  )
}

export const AnswerContent = memo(AnswerContentImpl)
