import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "../state/AuthContext"

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[var(--color-bg)] text-sm text-[var(--color-text-dim)]">
        Loading…
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
