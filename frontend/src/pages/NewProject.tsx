import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "motion/react"
import { useProjects } from "../state/ProjectsContext"

const STAGES = ["Idea", "Research", "Validation", "MVP", "Early Stage", "Growth"]

export function NewProject() {
  const { createProject } = useProjects()
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [problem, setProblem] = useState("")
  const [targetCustomer, setTargetCustomer] = useState("")
  const [industry, setIndustry] = useState("")
  const [stage, setStage] = useState("Idea")
  const [geography, setGeography] = useState("")
  const [businessModel, setBusinessModel] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError("Startup name is required.")
      return
    }
    setError(null)
    setLoading(true)
    try {
      const project = await createProject({
        name: name.trim(),
        problem: problem.trim() || undefined,
        target_customer: targetCustomer.trim() || undefined,
        industry: industry.trim() || undefined,
        stage,
        geography: geography.trim() || undefined,
        business_model: businessModel.trim() || undefined,
      })
      navigate(`/projects/${project.id}/chat`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-8 py-6">
      <div className="mb-4">
        <h2 className="gradient-text text-2xl font-bold">Create Your Startup</h2>
        <p className="mt-0.5 text-sm text-[var(--color-text-dim)]">
          Tell your AI co-founder about the idea. Once you're in chat, describing it will
          automatically kick off market, competitor, financial, and viability research.
        </p>
      </div>

      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        onSubmit={submit}
        className="card flex flex-col gap-4 p-6"
      >
        <Field label="What is your startup called?">
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            placeholder="SafePlate"
          />
        </Field>
        <Field label="What problem are you solving?">
          <textarea
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            className="input min-h-20"
            placeholder="Restaurants struggle to track food safety compliance in real time."
          />
        </Field>
        <Field label="Who is your target customer?">
          <input
            value={targetCustomer}
            onChange={(e) => setTargetCustomer(e.target.value)}
            className="input"
            placeholder="Independent restaurants and small food chains"
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="What industry are you in?">
            <input
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="input"
              placeholder="FoodTech"
            />
          </Field>
          <Field label="What stage are you at?">
            <select value={stage} onChange={(e) => setStage(e.target.value)} className="input">
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Where will you operate?">
            <input
              value={geography}
              onChange={(e) => setGeography(e.target.value)}
              className="input"
              placeholder="United States"
            />
          </Field>
          <Field label="What is your business model?">
            <input
              value={businessModel}
              onChange={(e) => setBusinessModel(e.target.value)}
              className="input"
              placeholder="B2B SaaS subscription"
            />
          </Field>
        </div>

        {error && <p className="text-xs text-red-300">{error}</p>}

        <motion.button
          type="submit"
          disabled={loading}
          whileHover={{ scale: loading ? 1 : 1.02 }}
          whileTap={{ scale: loading ? 1 : 0.98 }}
          className="btn-primary mt-1 rounded-lg px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Creating…" : "Create Startup"}
        </motion.button>
      </motion.form>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-[var(--color-text-dim)]">{label}</span>
      {children}
    </label>
  )
}
