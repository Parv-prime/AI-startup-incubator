import { useState, type FormEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../state/AuthContext"
import { LogoBadge } from "../components/Logo"
import { TechBackground } from "../components/TechBackground"

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const from = (location.state as { from?: Location })?.from?.pathname ?? "/projects"

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex h-screen w-screen items-center justify-center overflow-hidden px-4">
      <TechBackground />
      <div className="relative w-full max-w-sm">
        <div className="mb-8 text-center">
          <LogoBadge size={40} className="mx-auto mb-3" />
          <div className="text-lg font-semibold text-white">AI Startup Incubator</div>
          <div className="text-sm text-[var(--color-text-dim)]">AI Co-Founder</div>
        </div>

        <form onSubmit={submit} className="card flex flex-col gap-4 p-6">
          <div>
            <label className="mb-1 block text-xs text-[var(--color-text-dim)]">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-[var(--color-accent)]"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[var(--color-text-dim)]">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-[var(--color-accent)]"
            />
          </div>

          {error && <p className="text-xs text-red-300">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary mt-1 rounded-lg px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {loading ? "Logging in…" : "Login"}
          </button>

          <button type="button" className="text-center text-xs text-[var(--color-text-dim)] hover:text-white">
            Forgot password?
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-[var(--color-text-dim)]">
          Don't have an account?{" "}
          <Link to="/signup" className="text-white hover:underline">
            Create Account
          </Link>
        </p>
      </div>
    </div>
  )
}
