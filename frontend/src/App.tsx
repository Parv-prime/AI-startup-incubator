import { Navigate, Outlet, Route, Routes, useLocation, useParams } from "react-router-dom"
import { AnimatePresence } from "motion/react"
import { Sidebar } from "./components/Sidebar"
import { PageTransition } from "./components/PageTransition"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { AuthProvider } from "./state/AuthContext"
import { ProjectsProvider } from "./state/ProjectsContext"
import { ProjectWorkspaceProvider } from "./state/ProjectWorkspaceContext"
import { Login } from "./pages/Login"
import { Signup } from "./pages/Signup"
import { Projects } from "./pages/Projects"
import { NewProject } from "./pages/NewProject"
import { CoFounder } from "./pages/CoFounder"
import { Dashboard } from "./pages/Dashboard"
import { Market } from "./pages/Market"
import { Competitors } from "./pages/Competitors"
import { Financial } from "./pages/Financial"
import { Viability } from "./pages/Viability"
import { Roadmap } from "./pages/Roadmap"
import { Report } from "./pages/Report"
import { Settings } from "./pages/Settings"

function AppShell() {
  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}

function ProjectWorkspaceLayout() {
  const { projectId } = useParams()
  if (!projectId) return <Navigate to="/projects" replace />
  return (
    <ProjectWorkspaceProvider projectId={projectId}>
      <Outlet />
    </ProjectWorkspaceProvider>
  )
}

function AnimatedProjectRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route index element={<Navigate to="chat" replace />} />
        <Route path="chat" element={<PageTransition><CoFounder /></PageTransition>} />
        <Route path="dashboard" element={<PageTransition><Dashboard /></PageTransition>} />
        <Route path="market" element={<PageTransition><Market /></PageTransition>} />
        <Route path="competitors" element={<PageTransition><Competitors /></PageTransition>} />
        <Route path="financial" element={<PageTransition><Financial /></PageTransition>} />
        <Route path="viability" element={<PageTransition><Viability /></PageTransition>} />
        <Route path="roadmap" element={<PageTransition><Roadmap /></PageTransition>} />
        <Route path="report" element={<PageTransition><Report /></PageTransition>} />
      </Routes>
    </AnimatePresence>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ProjectsProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<Navigate to="/projects" replace />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/new" element={<NewProject />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/projects/:projectId" element={<ProjectWorkspaceLayout />}>
                <Route path="*" element={<AnimatedProjectRoutes />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/projects" replace />} />
        </Routes>
      </ProjectsProvider>
    </AuthProvider>
  )
}
