"use client"

import React, { createContext, useContext, useEffect, useRef, useState } from 'react'

export interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  images?: string[]
  mode?: '2D' | '3D'
  timestamp: Date
}

type PersistedMessage = Omit<Message, 'timestamp'> & { timestamp: string }

type SelectedPresets = {
  expression?: string
  action?: string
  style?: string
}

type ChatContextValue = {
  messages: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  input: string
  setInput: React.Dispatch<React.SetStateAction<string>>
  selectedPresets: SelectedPresets
  setSelectedPresets: React.Dispatch<React.SetStateAction<SelectedPresets>>
  persistState: (nextMessages?: Message[], nextInput?: string, nextSelectedPresets?: SelectedPresets, nextScrollTop?: number) => void
  scrollTop: number
  setScrollTop: React.Dispatch<React.SetStateAction<number>>
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function useChatState() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChatState must be used within ChatProvider')
  return ctx
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('我想生成一个[表情]的[动作]角色，[风格]风格的ip形象')
  const [selectedPresets, setSelectedPresets] = useState<SelectedPresets>({})
  const [scrollTop, setScrollTop] = useState<number>(0)
  const initializedRef = useRef(false)

  // 初始化：从本地恢复聊天与输入状态
  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    try {
      const saved = localStorage.getItem('joy_ip_chat_state')
      if (saved) {
        const parsed = JSON.parse(saved) as {
          messages?: PersistedMessage[]
          input?: string
          selectedPresets?: SelectedPresets
          scrollTop?: number
        }
        
        // 验证数据结构完整性
        if (!parsed || typeof parsed !== 'object') {
          console.warn('localStorage 数据格式无效，清除数据')
          localStorage.removeItem('joy_ip_chat_state')
          return
        }
        
        if (parsed.messages && Array.isArray(parsed.messages)) {
          try {
            const restored = parsed.messages.map(m => ({
              ...m,
              timestamp: new Date(m.timestamp)
            }))
            setMessages(restored)
          } catch (msgError) {
            console.warn('恢复消息失败:', msgError)
            // 消息恢复失败不影响其他数据
          }
        }
        if (typeof parsed.input === 'string') setInput(parsed.input)
        if (parsed.selectedPresets && typeof parsed.selectedPresets === 'object') {
          setSelectedPresets(parsed.selectedPresets)
        }
        if (typeof parsed.scrollTop === 'number') setScrollTop(parsed.scrollTop)
      }
    } catch (e) {
      console.error('恢复聊天状态失败，清除损坏数据:', e)
      // 清除损坏的数据，避免下次加载时再次失败
      try {
        localStorage.removeItem('joy_ip_chat_state')
      } catch (clearError) {
        console.error('清除 localStorage 失败:', clearError)
      }
    }
  }, [])

  // 持久化：消息/输入/预设变更时保存到本地
  useEffect(() => {
    try {
      const toSave = {
        messages: messages.map(m => ({ ...m, timestamp: m.timestamp.toISOString() } as PersistedMessage)),
        input,
        selectedPresets,
        scrollTop,
      }
      localStorage.setItem('joy_ip_chat_state', JSON.stringify(toSave))
    } catch (e) {
      console.warn('保存聊天状态失败:', e)
    }
  }, [messages, input, selectedPresets, scrollTop])

  const persistState = (
    nextMessages: Message[] = messages,
    nextInput: string = input,
    nextSelectedPresets: SelectedPresets = selectedPresets,
    nextScrollTop?: number
  ) => {
    try {
      const toSave = {
        messages: nextMessages.map(m => ({ ...m, timestamp: m.timestamp.toISOString() } as PersistedMessage)),
        input: nextInput,
        selectedPresets: nextSelectedPresets,
        scrollTop: typeof nextScrollTop === 'number' ? nextScrollTop : scrollTop,
      }
      localStorage.setItem('joy_ip_chat_state', JSON.stringify(toSave))
    } catch (e) {
      console.warn('即时保存聊天状态失败:', e)
    }
  }

  const value: ChatContextValue = {
    messages,
    setMessages,
    input,
    setInput,
    selectedPresets,
    setSelectedPresets,
    persistState,
    scrollTop,
    setScrollTop,
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}
