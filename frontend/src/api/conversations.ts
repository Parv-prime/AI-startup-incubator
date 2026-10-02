import { apiBaseUrl, apiDelete, apiGet, apiPost, apiPut, authHeaders } from "./client"
import type { AnalysisResponse, Recommendation, Source, ToolActivity, ViabilityResponse } from "./types"

export interface Conversation {
  id: string
  project_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: "user" | "assistant" | "system" | "tool"
  content: string
  created_at: string
}

export function listConversations(projectId: string): Promise<Conversation[]> {
  return apiGet(`/api/v1/projects/${projectId}/conversations`)
}

export function createConversation(projectId: string, title = "New Conversation"): Promise<Conversation> {
  return apiPost(`/api/v1/projects/${projectId}/conversations`, { title })
}

export function renameConversation(conversationId: string, title: string): Promise<Conversation> {
  return apiPut(`/api/v1/conversations/${conversationId}`, { title })
}

export function deleteConversation(conversationId: string): Promise<void> {
  return apiDelete(`/api/v1/conversations/${conversationId}`)
}

export function listMessages(conversationId: string): Promise<Message[]> {
  return apiGet(`/api/v1/conversations/${conversationId}/messages`)
}

export type StreamEvent =
  | { type: "status"; message: string }
  | { type: "token"; text: string }
  | {
      type: "done"
      path: "fast" | "agent"
      success: boolean
      response: string
      conversation_id: string
      project_id: string
      tool_activity: ToolActivity[]
      analysis: AnalysisResponse | null
      viability: ViabilityResponse | null
      recommendations: Recommendation[]
      sources: Source[]
      errors: string[]
    }

export async function streamMessage(
  conversationId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/conversations/${conversationId}/messages/stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ content }),
    },
  )
  if (!response.ok || !response.body) {
    let detail = `Request failed (${response.status})`
    try {
      detail = (await response.json()).detail ?? detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split("\n\n")
    buffer = parts.pop() ?? ""
    for (const part of parts) {
      const dataLine = part.split("\n").find((line) => line.startsWith("data:"))
      if (!dataLine) continue
      try {
        onEvent(JSON.parse(dataLine.slice(5).trim()))
      } catch {
        // ignore malformed chunk
      }
    }
  }
}
