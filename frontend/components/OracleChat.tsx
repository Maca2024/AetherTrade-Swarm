'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageCircle, X, Send, Bot, User, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const SUGGESTED_PROMPTS = [
  'What is the current market regime?',
  'How are the strategy pods performing?',
  'Explain the risk management system',
  'What is the portfolio allocation?',
]

export default function OracleChat() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "I'm **AETHERTRADE**, your AI trading intelligence. Ask me about market regimes, strategy performance, risk metrics, or portfolio positioning.",
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (isOpen) inputRef.current?.focus()
  }, [isOpen])

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return

    const userMsg: Message = { role: 'user', content: text.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''
      const res = await fetch(`${apiUrl}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMsg].map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      })

      if (!res.ok) throw new Error(`API error: ${res.status}`)

      const data = await res.json()
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.reply },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            "I'm having trouble connecting to the AETHERTRADE backend. Please check that the API is running and try again.",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <>
      {/* Floating button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full',
          'flex items-center justify-center shadow-2xl',
          'transition-all duration-300',
        )}
        style={{
          background: isOpen
            ? 'rgba(255,255,255,0.1)'
            : 'linear-gradient(135deg, #00D4FF 0%, #8B5CF6 100%)',
          border: '1px solid rgba(255,255,255,0.15)',
          boxShadow: isOpen
            ? '0 4px 20px rgba(0,0,0,0.3)'
            : '0 4px 30px rgba(0,212,255,0.4)',
        }}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        aria-label={isOpen ? 'Close chat' : 'Open AETHERTRADE chat'}
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
            >
              <X className="w-5 h-5 text-white" />
            </motion.div>
          ) : (
            <motion.div
              key="chat"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
            >
              <MessageCircle className="w-5 h-5 text-white" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="fixed bottom-24 right-6 z-50 w-[380px] max-h-[520px] rounded-2xl overflow-hidden flex flex-col"
            style={{
              background: 'rgba(8, 8, 16, 0.95)',
              border: '1px solid rgba(0, 212, 255, 0.15)',
              backdropFilter: 'blur(24px)',
              boxShadow:
                '0 20px 60px rgba(0,0,0,0.6), 0 0 30px rgba(0,212,255,0.1)',
            }}
          >
            {/* Header */}
            <div
              className="px-4 py-3 flex items-center gap-3 flex-shrink-0"
              style={{
                borderBottom: '1px solid rgba(255,255,255,0.07)',
                background:
                  'linear-gradient(180deg, rgba(0,212,255,0.06) 0%, transparent 100%)',
              }}
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{
                  background: 'rgba(0,212,255,0.15)',
                  border: '1px solid rgba(0,212,255,0.3)',
                }}
              >
                <Bot className="w-4 h-4 text-[#00D4FF]" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">AETHERTRADE AI</h3>
                <p className="text-[10px] text-white/40">
                  Trading Intelligence Assistant
                </p>
              </div>
              <div className="ml-auto flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse" />
                <span className="text-[10px] text-[#00FF94]">Online</span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={cn(
                    'flex gap-2',
                    msg.role === 'user' ? 'flex-row-reverse' : 'flex-row',
                  )}
                >
                  <div
                    className={cn(
                      'w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5',
                    )}
                    style={{
                      background:
                        msg.role === 'assistant'
                          ? 'rgba(0,212,255,0.15)'
                          : 'rgba(139,92,246,0.15)',
                      border: `1px solid ${msg.role === 'assistant' ? 'rgba(0,212,255,0.3)' : 'rgba(139,92,246,0.3)'}`,
                    }}
                  >
                    {msg.role === 'assistant' ? (
                      <Bot className="w-3 h-3 text-[#00D4FF]" />
                    ) : (
                      <User className="w-3 h-3 text-[#8B5CF6]" />
                    )}
                  </div>
                  <div
                    className={cn(
                      'rounded-xl px-3 py-2 text-xs leading-relaxed max-w-[280px]',
                      msg.role === 'user'
                        ? 'bg-[#8B5CF6]/15 text-white/90 border border-[#8B5CF6]/20'
                        : 'bg-white/5 text-white/70 border border-white/7',
                    )}
                    dangerouslySetInnerHTML={{
                      __html: msg.content
                        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
                        .replace(/\n/g, '<br/>'),
                    }}
                  />
                </motion.div>
              ))}

              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-2"
                >
                  <div
                    className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
                    style={{
                      background: 'rgba(0,212,255,0.15)',
                      border: '1px solid rgba(0,212,255,0.3)',
                    }}
                  >
                    <Bot className="w-3 h-3 text-[#00D4FF]" />
                  </div>
                  <div className="bg-white/5 border border-white/7 rounded-xl px-3 py-2 flex items-center gap-1.5">
                    <Loader2 className="w-3 h-3 text-[#00D4FF] animate-spin" />
                    <span className="text-xs text-white/40">Analyzing...</span>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Suggested prompts (only when no user messages yet) */}
            {messages.length <= 1 && (
              <div className="px-4 pb-2 flex flex-wrap gap-1.5">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => sendMessage(prompt)}
                    className="text-[10px] px-2.5 py-1 rounded-full text-white/50 hover:text-white/80 transition-colors"
                    style={{
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.08)',
                    }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="px-3 py-3 flex items-center gap-2 flex-shrink-0"
              style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}
            >
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask AETHERTRADE anything..."
                disabled={isLoading}
                className={cn(
                  'flex-1 bg-white/5 rounded-xl px-3 py-2.5 text-xs text-white/90',
                  'placeholder:text-white/25 outline-none',
                  'border border-white/7 focus:border-[#00D4FF]/40',
                  'transition-colors duration-200',
                )}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className={cn(
                  'w-9 h-9 rounded-xl flex items-center justify-center',
                  'transition-all duration-200',
                  input.trim() && !isLoading
                    ? 'text-black'
                    : 'bg-white/5 text-white/20',
                )}
                style={
                  input.trim() && !isLoading
                    ? {
                        background:
                          'linear-gradient(135deg, #00D4FF 0%, #8B5CF6 100%)',
                        boxShadow: '0 0 15px rgba(0,212,255,0.3)',
                      }
                    : {}
                }
                aria-label="Send message"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
