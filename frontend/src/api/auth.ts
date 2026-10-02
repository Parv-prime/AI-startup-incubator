import { apiGet, apiPost } from "./client"

export interface User {
  id: string
  name: string
  email: string
  created_at: string
}

export interface AuthResponse {
  user: User
  access_token: string
  token_type: string
}

export function signup(name: string, email: string, password: string): Promise<AuthResponse> {
  return apiPost("/api/v1/auth/signup", { name, email, password })
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return apiPost("/api/v1/auth/login", { email, password })
}

export function logout(): Promise<{ success: boolean }> {
  return apiPost("/api/v1/auth/logout")
}

export function me(): Promise<User> {
  return apiGet("/api/v1/auth/me")
}
