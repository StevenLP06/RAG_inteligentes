import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Conversation, Message } from '@/lib/types'
import { readStorage, uid, writeStorage } from '@/lib/utils'

const KEY = 'rag-mesa:conversaciones:v1'
const ACTIVE_KEY = 'rag-mesa:activa:v1'

const titleFrom = (text: string) => {
  const t = text.replace(/\s+/g, ' ').trim()
  return t.length > 64 ? `${t.slice(0, 61)}…` : t
}

/** Historial de conversaciones persistido en localStorage (escritura diferida para no bloquear la UI). */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    // Al recargar, una petición que quedó "pending" ya no llegará: se marca como error reintentable.
    readStorage<Conversation[]>(KEY, []).map((c) => ({
      ...c,
      messages: c.messages.map((m) =>
        m.status === 'pending' ? { ...m, status: 'error', error: 'La consulta se interrumpió al recargar la página.' } : m,
      ),
    })),
  )
  const [activeId, setActiveId] = useState<string | null>(() => readStorage<string | null>(ACTIVE_KEY, null))

  // Persistencia diferida; si se excede la cuota se descartan las conversaciones más antiguas.
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => {
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      let list = conversations
      while (!writeStorage(KEY, list) && list.length > 1) list = list.slice(0, -1)
    }, 250)
    return () => window.clearTimeout(timer.current)
  }, [conversations])

  useEffect(() => {
    writeStorage(ACTIVE_KEY, activeId)
  }, [activeId])

  const sorted = useMemo(() => [...conversations].sort((a, b) => b.updatedAt - a.updatedAt), [conversations])
  const active = useMemo(() => conversations.find((c) => c.id === activeId) ?? null, [conversations, activeId])

  /** Agrega mensajes a la conversación indicada (o crea una nueva). Devuelve el id de la conversación. */
  const append = useCallback((conversationId: string | null, msgs: Message[]): string => {
    const now = Date.now()
    const id = conversationId ?? uid()
    setConversations((prev) => {
      const exists = prev.some((c) => c.id === id)
      if (!exists) {
        const first = msgs.find((m) => m.role === 'user')
        return [{ id, title: titleFrom(first?.content ?? 'Nueva conversación'), createdAt: now, updatedAt: now, messages: msgs }, ...prev]
      }
      return prev.map((c) => (c.id === id ? { ...c, updatedAt: now, messages: [...c.messages, ...msgs] } : c))
    })
    setActiveId(id)
    return id
  }, [])

  const updateMessage = useCallback((conversationId: string, messageId: string, patch: Partial<Message>) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id !== conversationId
          ? c
          : { ...c, updatedAt: Date.now(), messages: c.messages.map((m) => (m.id === messageId ? { ...m, ...patch } : m)) },
      ),
    )
  }, [])

  const remove = useCallback((id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id))
    setActiveId((cur) => (cur === id ? null : cur))
  }, [])

  const clearAll = useCallback(() => {
    setConversations([])
    setActiveId(null)
  }, [])

  return { conversations: sorted, active, activeId, setActiveId, append, updateMessage, remove, clearAll }
}
