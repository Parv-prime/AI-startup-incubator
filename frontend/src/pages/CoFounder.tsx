import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"
import { ToolActivityList } from "../components/ToolActivityList"
import { Badge, priorityTone } from "../components/Card"

const SUGGESTIONS = [
  "Describe your startup idea in a sentence or two.",
  "Who are our main competitors?",
  "Calculate break-even if I charge ₹500/month with ₹50,000 monthly cost.",
  "Evaluate our startup's viability.",
]

export function CoFounder() {
  const {
    project,
    conversations,
    activeConversationId,
    messages,
    sending,
    error,
    selectConversation,
    newConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
  } = useProjectWorkspace()
  const [input, setInput] = useState("")
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const autoGrow = (el: HTMLTextAreaElement | null) => {
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, sending])

  useEffect(() => {
    autoGrow(inputRef.current)
  }, [input])

  const submit = (value: string) => {
    const trimmed = value.trim()
    if (!trimmed || sending) return
    setInput("")
    void sendMessage(trimmed)
  }

  const editMessage = (content: string) => {
    setInput(content)
    inputRef.current?.focus()
  }

  return (
    <div className="flex h-full">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-white/5 px-3 py-4 md:flex">
        <button
          onClick={() => void newConversation()}
          className="mb-3 rounded-lg border border-white/10 px-3 py-2 text-left text-sm text-white hover:bg-white/5"
        >
          + New Conversation
        </button>
        <div className="mb-2 px-1 text-[11px] uppercase tracking-wide text-[var(--color-text-dim)]">
          Recent Conversations
        </div>
        <div className="flex flex-col gap-1 overflow-y-auto">
          {conversations.map((c) => (
            <div key={c.id} className="group flex items-center gap-1">
              <button
                onClick={() => void selectConversation(c.id)}
                className={`flex-1 truncate rounded-lg px-2 py-1.5 text-left text-sm ${
                  c.id === activeConversationId
                    ? "bg-white/10 text-white"
                    : "text-[var(--color-text-dim)] hover:bg-white/5"
                }`}
              >
                {c.title}
              </button>
              <button
                onClick={() => {
                  const title = prompt("Rename conversation", c.title)
                  if (title) void renameConversation(c.id, title)
                }}
                className="hidden shrink-0 px-1 text-xs text-[var(--color-text-dim)] hover:text-white group-hover:block"
                title="Rename"
              >
                ✎
              </button>
              <button
                onClick={() => {
                  if (confirm("Delete this conversation?")) void deleteConversation(c.id)
                }}
                className="hidden shrink-0 px-1 text-xs text-[var(--color-text-dim)] hover:text-red-300 group-hover:block"
                title="Delete"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="border-b border-white/5 px-8 py-3 text-xs text-[var(--color-text-dim)]">
          AI Co-Founder · Current project:{" "}
          <span className="text-white">{project?.name ?? "…"}</span>
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center gap-6 text-center"
            >
              <div className="gradient-text text-4xl font-bold">Meet your AI Co-Founder</div>
              <p className="text-[var(--color-text-dim)]">
                Describe your startup idea and the agent will automatically research the market,
                competitors, financials, and viability for you — then talk it through with you
                like a co-founder would.
              </p>
              <div className="grid w-full gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button
                    key={s}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, delay: 0.1 + i * 0.05, ease: "easeOut" }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => submit(s)}
                    className="card card-interactive px-4 py-3 text-left text-sm text-[var(--color-text-dim)] transition-colors hover:text-white"
                  >
                    {s}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          ) : (
            <div className="mx-auto flex max-w-2xl flex-col gap-4">
              <AnimatePresence initial={false}>
                {messages.map((m) => (
                  <motion.div
                    key={m.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className={`group flex items-start gap-1.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {m.role === "user" && (
                      <button
                        onClick={() => editMessage(m.content)}
                        title="Edit and resend"
                        className="mt-3 shrink-0 rounded-md p-1 text-[var(--color-text-dim)] opacity-0 transition-opacity hover:text-white group-hover:opacity-100"
                      >
                        <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
                          <path
                            d="M14.5 2.5a1.5 1.5 0 0 1 2 2L6 15l-3 1 1-3L14.5 2.5Z"
                            stroke="currentColor"
                            strokeWidth="1.4"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </button>
                    )}
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        m.role === "user"
                          ? "bg-[var(--color-accent)] text-white"
                          : "card text-[var(--color-text)]"
                      }`}
                    >
                      {m.role === "assistant" && m.toolActivity && m.toolActivity.length > 0 && (
                        <div className="mb-2 border-b border-white/5 pb-2">
                          <ToolActivityList items={m.toolActivity} />
                        </div>
                      )}
                      {m.role === "assistant" && m.streaming && !m.content && (
                        <div className="flex items-center gap-2 text-[var(--color-text-dim)]">
                          <ThinkingDots />
                          {m.statusLine ?? "Thinking..."}
                        </div>
                      )}
                      {m.content && <div className="whitespace-pre-wrap">{m.content}</div>}
                      {m.role === "assistant" && m.recommendations && m.recommendations.length > 0 && (
                        <div className="mt-3 flex flex-col gap-2 border-t border-white/5 pt-3">
                          {m.recommendations.map((rec, i) => (
                            <div key={i} className="flex items-start gap-2 text-xs">
                              <Badge tone={priorityTone(rec.priority)}>{rec.priority}</Badge>
                              <div>
                                <div className="font-medium text-white">{rec.title}</div>
                                <div className="text-[var(--color-text-dim)]">{rec.description}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              <div ref={endRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="mx-8 mb-2 rounded-lg bg-red-500/10 px-4 py-2 text-xs text-red-300">
            {error}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault()
            submit(input)
          }}
          className="mx-auto mb-6 flex w-full max-w-2xl items-end gap-2 px-8"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                submit(input)
              }
            }}
            placeholder="Tell your co-founder about your startup…"
            rows={1}
            className="max-h-[200px] flex-1 resize-none overflow-y-auto rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-[var(--color-text-dim)] outline-none focus:border-[var(--color-accent)]"
          />
          <motion.button
            type="submit"
            disabled={sending || !input.trim()}
            whileHover={{ scale: sending || !input.trim() ? 1 : 1.04 }}
            whileTap={{ scale: sending || !input.trim() ? 1 : 0.96 }}
            className="btn-primary rounded-xl px-4 py-3 text-sm font-medium text-white transition-opacity disabled:opacity-40"
          >
            Send
          </motion.button>
        </form>
      </div>
    </div>
  )
}

function ThinkingDots() {
  return (
    <span className="flex gap-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent-2)]"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </span>
  )
}
