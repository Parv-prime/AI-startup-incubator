import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import * as conversationsApi from "../api/conversations"
import * as projectDataApi from "../api/projectData"
import * as projectsApi from "../api/projects"
import type {
  AnalysisResponse,
  Recommendation,
  Source,
  StartupProfile,
  ToolActivity,
  ViabilityResponse,
} from "../api/types"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  streaming?: boolean
  statusLine?: string
  toolActivity?: ToolActivity[]
  recommendations?: Recommendation[]
  sources?: Source[]
}

const AI_UNAVAILABLE_MESSAGE = "AI service is temporarily unavailable. Please try again."

/** User-facing text for a failed request — never a raw exception or stack trace. */
function friendlyError(err: unknown): string {
  // fetch() rejects with a TypeError when the backend can't be reached at all.
  if (err instanceof TypeError) return AI_UNAVAILABLE_MESSAGE
  if (err instanceof Error && err.message && !/^Request failed \(5\d\d\)$/.test(err.message)) {
    return err.message
  }
  return AI_UNAVAILABLE_MESSAGE
}

interface WorkspaceState {
  projectId: string
  project: projectsApi.Project | null
  profile: StartupProfile | null
  analysis: AnalysisResponse | null
  viability: ViabilityResponse | null
  recommendations: Recommendation[]
  conversations: conversationsApi.Conversation[]
  activeConversationId: string | null
  messages: ChatMessage[]
  loading: boolean
  sending: boolean
  error: string | null
  selectConversation: (id: string) => Promise<void>
  newConversation: () => Promise<void>
  renameConversation: (id: string, title: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  sendMessage: (input: string) => Promise<void>
  refreshProjectData: () => Promise<void>
}

const WorkspaceContext = createContext<WorkspaceState | null>(null)

function toProfile(project: projectsApi.Project | null): StartupProfile | null {
  if (!project) return null
  return {
    startup_name: project.name,
    industry: project.industry,
    problem: project.problem,
    solution: project.solution,
    target_customer: project.target_customer,
    geography: project.geography,
    business_model: project.business_model,
    startup_stage: project.stage,
    budget: project.budget,
    goals: project.goals,
  }
}

export function ProjectWorkspaceProvider({
  projectId,
  children,
}: {
  projectId: string
  children: ReactNode
}) {
  const [project, setProject] = useState<projectsApi.Project | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [viability, setViability] = useState<ViabilityResponse | null>(null)
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [conversations, setConversations] = useState<conversationsApi.Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshProjectData = useCallback(async () => {
    const [proj, market, competitor, financial, viab, recs] = await Promise.all([
      projectsApi.getProject(projectId),
      projectDataApi.getLatestMarketResearch(projectId),
      projectDataApi.getCompetitorsForDisplay(projectId),
      projectDataApi.getLatestFinancialAnalysis(projectId),
      projectDataApi.getViability(projectId),
      projectDataApi.getRecommendations(projectId),
    ])
    setProject(proj)
    setAnalysis({
      market_research: market as unknown as AnalysisResponse["market_research"],
      competitor_research: competitor as AnalysisResponse["competitor_research"],
      financial_analysis: financial as unknown as AnalysisResponse["financial_analysis"],
    })
    setViability(viab)
    setRecommendations(recs)
  }, [projectId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([refreshProjectData(), conversationsApi.listConversations(projectId)])
      .then(([, convos]) => {
        if (cancelled) return
        setConversations(convos)
        if (convos.length > 0) {
          setActiveConversationId(convos[0].id)
        } else {
          setActiveConversationId(null)
          setMessages([])
        }
      })
      .catch((err) => {
        if (!cancelled) setError(friendlyError(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  useEffect(() => {
    if (!activeConversationId) return
    let cancelled = false
    conversationsApi
      .listMessages(activeConversationId)
      .then((rows) => {
        if (cancelled) return
        setMessages(
          rows
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({ id: m.id, role: m.role as "user" | "assistant", content: m.content })),
        )
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load messages.")
      })
    return () => {
      cancelled = true
    }
  }, [activeConversationId])

  const selectConversation = useCallback(async (id: string) => {
    setActiveConversationId(id)
  }, [])

  const newConversation = useCallback(async () => {
    const conversation = await conversationsApi.createConversation(projectId)
    setConversations((prev) => [conversation, ...prev])
    setActiveConversationId(conversation.id)
    setMessages([])
  }, [projectId])

  const renameConversation = useCallback(async (id: string, title: string) => {
    const updated = await conversationsApi.renameConversation(id, title)
    setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)))
  }, [])

  const deleteConversation = useCallback(
    async (id: string) => {
      await conversationsApi.deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeConversationId === id) {
        setActiveConversationId(null)
        setMessages([])
      }
    },
    [activeConversationId],
  )

  const sendMessage = useCallback(
    async (input: string) => {
      let conversationId = activeConversationId
      if (!conversationId) {
        const conversation = await conversationsApi.createConversation(projectId)
        setConversations((prev) => [conversation, ...prev])
        conversationId = conversation.id
        setActiveConversationId(conversationId)
      }

      const userMsgId = crypto.randomUUID()
      const assistantMsgId = crypto.randomUUID()
      setMessages((prev) => [
        ...prev,
        { id: userMsgId, role: "user", content: input },
        { id: assistantMsgId, role: "assistant", content: "", streaming: true },
      ])
      setSending(true)
      setError(null)
      let extras: Pick<ChatMessage, "toolActivity" | "recommendations" | "sources"> | null = null

      try {
        await conversationsApi.streamMessage(conversationId, input, (event) => {
          if (event.type === "status") {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantMsgId ? { ...m, statusLine: event.message } : m)),
            )
          } else if (event.type === "token") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, content: m.content + event.text } : m,
              ),
            )
          } else if (event.type === "done") {
            extras = {
              toolActivity: event.tool_activity,
              recommendations: event.recommendations,
              sources: event.sources,
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: event.response,
                      streaming: false,
                      statusLine: undefined,
                      ...extras,
                    }
                  : m,
              ),
            )
            if (event.analysis) {
              const update = event.analysis
              // Merge: a turn that only ran competitor research must not blank the market page.
              setAnalysis((prev) => ({
                market_research: update.market_research ?? prev?.market_research ?? null,
                competitor_research: update.competitor_research ?? prev?.competitor_research ?? null,
                financial_analysis: update.financial_analysis ?? prev?.financial_analysis ?? null,
              }))
            }
            if (event.viability) setViability(event.viability)
            if (event.recommendations.length) setRecommendations(event.recommendations)
            if (!event.success && event.errors.length) setError(event.errors.join(" "))
            conversationsApi
              .listConversations(projectId)
              .then(setConversations)
              .catch(() => {})
          }
        })
      } catch (err) {
        const message = friendlyError(err)
        setError(message)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: message, streaming: false, statusLine: undefined }
              : m,
          ),
        )
      } finally {
        setSending(false)
        // The backend persists the assistant reply before the stream finishes (or even if
        // the client-side stream read fails), so re-sync from the server here rather than
        // relying solely on the incremental SSE events reaching this component.
        conversationsApi
          .listMessages(conversationId)
          .then((rows) => {
            const synced: ChatMessage[] = rows
              .filter((m) => m.role === "user" || m.role === "assistant")
              .map((m) => ({ id: m.id, role: m.role as "user" | "assistant", content: m.content }))
            // Keep this turn's tool activity + sources on the reply they belong to.
            const last = synced[synced.length - 1]
            if (extras && last?.role === "assistant") Object.assign(last, extras)
            setMessages(synced)
          })
          .catch(() => {})
      }
    },
    [activeConversationId, projectId],
  )

  const value = useMemo<WorkspaceState>(
    () => ({
      projectId,
      project,
      profile: toProfile(project),
      analysis,
      viability,
      recommendations,
      conversations,
      activeConversationId,
      messages,
      loading,
      sending,
      error,
      selectConversation,
      newConversation,
      renameConversation,
      deleteConversation,
      sendMessage,
      refreshProjectData,
    }),
    [
      projectId,
      project,
      analysis,
      viability,
      recommendations,
      conversations,
      activeConversationId,
      messages,
      loading,
      sending,
      error,
      selectConversation,
      newConversation,
      renameConversation,
      deleteConversation,
      sendMessage,
      refreshProjectData,
    ],
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}

export function useProjectWorkspace(): WorkspaceState {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error("useProjectWorkspace must be used within ProjectWorkspaceProvider")
  return ctx
}
