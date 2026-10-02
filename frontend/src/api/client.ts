const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8080"
const TOKEN_KEY = "myai.access_token"

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setAuthToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // ignore (private browsing, storage disabled, etc.)
  }
}

export function clearAuthToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // ignore
  }
}

export function authHeaders(): Record<string, string> {
  const token = getAuthToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function apiBaseUrl(): string {
  return BASE_URL
}

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    if (response.status === 401) clearAuthToken()
    throw new ApiError(await safeMessage(response), response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, { headers: { ...authHeaders() } })
  return handle<T>(response)
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body ?? {}),
  })
  return handle<T>(response)
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  })
  return handle<T>(response)
}

export async function apiDelete<T = void>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  })
  return handle<T>(response)
}

async function safeMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    return data.detail ?? response.statusText
  } catch {
    return response.statusText || "Request failed"
  }
}
