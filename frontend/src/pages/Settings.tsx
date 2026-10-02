import { useEffect, useState } from "react"
import { Card, SectionTitle } from "../components/Card"
import { useAuth } from "../state/AuthContext"
import { getHealth } from "../api/system"
import type { HealthResponse } from "../api/types"

export function Settings() {
  const { user, logout } = useAuth()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not reach backend."))
  }, [])

  return (
    <div className="mx-auto max-w-2xl px-8 py-6">
      <SectionTitle>Settings</SectionTitle>

      <Card>
        <SectionTitle>System status</SectionTitle>
        {error ? (
          <p className="text-sm text-red-300">{error}</p>
        ) : health ? (
          <dl className="flex flex-col gap-2 text-sm">
            <Row label="Overall" value={health.status} ok={health.status === "ok"} />
            <Row label="LLM" value={`${health.model_name} (${health.llm_status})`} ok={health.llm_status === "reachable"} />
            <Row label="Database" value={health.database_status} ok={health.database_status === "ok"} />
            <Row label="ML model" value={health.ml_model_status} ok={health.ml_model_status === "ready"} />
            <Row label="Version" value={health.version} />
          </dl>
        ) : (
          <p className="text-sm text-[var(--color-text-dim)]">Checking…</p>
        )}
      </Card>

      <Card className="mt-4">
        <SectionTitle>Profile</SectionTitle>
        <dl className="flex flex-col gap-2 text-sm">
          <Row label="Name" value={user?.name ?? "—"} />
          <Row label="Email" value={user?.email ?? "—"} />
        </dl>
      </Card>

      <Card className="mt-4">
        <SectionTitle>Session</SectionTitle>
        <button
          onClick={logout}
          className="mt-3 rounded-lg border border-white/10 px-4 py-2 text-sm text-white hover:bg-white/5"
        >
          Logout
        </button>
      </Card>
    </div>
  )
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex justify-between">
      <dt className="text-[var(--color-text-dim)]">{label}</dt>
      <dd className={ok === undefined ? "text-white" : ok ? "text-emerald-300" : "text-red-300"}>{value}</dd>
    </div>
  )
}
