import { cn } from '@/lib/utils'

const STYLES: Record<string, string> = {
  pdf: 'bg-rose-500/15 text-rose-300 border-rose-400/20',
  docx: 'bg-sky-500/15 text-sky-300 border-sky-400/20',
  md: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/20',
}

export function FileBadge({ archivo, small }: { archivo: string; small?: boolean }) {
  const ext = archivo.split('.').pop()?.toLowerCase() ?? ''
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-md border font-mono font-semibold uppercase',
        small ? 'h-5 min-w-9 px-1 text-[0.6rem]' : 'h-7 min-w-11 px-1.5 text-[0.65rem]',
        STYLES[ext] ?? 'border-zinc-400/20 bg-zinc-500/15 text-zinc-300',
      )}
    >
      {ext}
    </span>
  )
}
