/**
 * Sonidos sutiles sintetizados con Web Audio API: no se descarga ningún archivo.
 * El AudioContext se crea de forma perezosa en el primer gesto del usuario.
 */
let ctx: AudioContext | null = null
let enabled = true

export function setSoundEnabled(value: boolean) {
  enabled = value
}

function audio(): AudioContext | null {
  if (!enabled || typeof window === 'undefined') return null
  if (!ctx) {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AC) return null
    ctx = new AC()
  }
  if (ctx.state === 'suspended') void ctx.resume()
  return ctx
}

interface ToneOpts {
  type?: OscillatorType
  gain?: number
  /** Frecuencia final (glissando). */
  to?: number
}

function tone(freq: number, delay: number, duration: number, { type = 'sine', gain = 0.035, to }: ToneOpts = {}) {
  const ac = audio()
  if (!ac) return
  const t0 = ac.currentTime + delay
  const osc = ac.createOscillator()
  const amp = ac.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, t0)
  if (to) osc.frequency.exponentialRampToValueAtTime(to, t0 + duration)
  amp.gain.setValueAtTime(0.0001, t0)
  amp.gain.exponentialRampToValueAtTime(gain, t0 + 0.012)
  amp.gain.exponentialRampToValueAtTime(0.0001, t0 + duration)
  osc.connect(amp).connect(ac.destination)
  osc.start(t0)
  osc.stop(t0 + duration + 0.02)
}

export const sounds = {
  /** Envío de una pregunta: breve barrido ascendente. */
  send: () => tone(480, 0, 0.14, { to: 760, gain: 0.03 }),
  /** Respuesta recibida: dos notas suaves (quinta justa). */
  receive: () => {
    tone(659.25, 0, 0.22, { gain: 0.03 })
    tone(987.77, 0.08, 0.32, { gain: 0.022 })
  },
  /** Evidencia insuficiente: nota única más grave. */
  notice: () => tone(523.25, 0, 0.28, { type: 'triangle', gain: 0.03, to: 440 }),
  error: () => tone(240, 0, 0.3, { type: 'triangle', gain: 0.04, to: 150 }),
  tick: () => tone(1320, 0, 0.045, { gain: 0.012 }),
  open: () => tone(392, 0, 0.12, { to: 523, gain: 0.018 }),
  close: () => tone(523, 0, 0.12, { to: 392, gain: 0.018 }),
}
