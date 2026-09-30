import { useEffect, useRef, useState } from 'react'
import { fetchProjection, fetchSimulation, fetchStates } from './api'
import { SaveDialog, UnlockDialog } from './components/Dialogs'
import { Header } from './components/Header'
import { OutcomesPanel } from './components/OutcomesPanel'
import { Sidebar } from './components/Sidebar'
import { StrategyPanel } from './components/StrategyPanel'
import { GoalsPanel, KeyFigures, KpiCards } from './components/Summary'
import { downloadPlan, readPlanFile, samplePlan } from './planFile'
import type { Plan, Projection, Simulation, StateOption } from './types'
import { useTheme } from './useTheme'

const PREPARED_ON = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })

// Results are kept together with the plan that produced them, so the page never mixes old
// numbers with new inputs.
interface Result<T> {
  plan: Plan
  value: T
}

export default function App() {
  const { theme, toggle } = useTheme()
  const [plan, setPlan] = useState<Plan>(samplePlan)
  const [projection, setProjection] = useState<Result<Projection> | null>(null)
  const [simulation, setSimulation] = useState<Result<Simulation> | null>(null)
  const [error, setError] = useState<string | null>(null) // current inputs can't be projected
  const [fileError, setFileError] = useState<string | null>(null)
  const [states, setStates] = useState<StateOption[]>([])
  const [saving, setSaving] = useState(false)
  const [locked, setLocked] = useState<{ name: string; open: (password: string) => Promise<Plan> } | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchStates().then(setStates).catch(() => setStates([]))
  }, [])

  // Recalculate shortly after the user stops typing; the slower simulation waits a bit longer.
  useEffect(() => {
    const controller = new AbortController()
    const projectTimer = setTimeout(() => {
      fetchProjection(plan, controller.signal)
        .then((value) => {
          setProjection({ plan, value })
          setError(null)
        })
        .catch((e: Error) => {
          if (e.name !== 'AbortError') setError(e.message)
        })
    }, 250)
    const simulateTimer = setTimeout(() => {
      fetchSimulation(plan, controller.signal)
        .then((value) => setSimulation({ plan, value }))
        .catch(() => {}) // the projection request reports input errors
    }, 700)
    return () => {
      clearTimeout(projectTimer)
      clearTimeout(simulateTimer)
      controller.abort()
    }
  }, [plan])

  async function adoptPlan(next: Plan) {
    await fetchProjection(next) // reject plans the backend can't use before replacing the current one
    setPlan(next)
    setFileError(null)
  }

  async function openFile(file: File) {
    try {
      const parsed = await readPlanFile(file)
      if (parsed.kind === 'locked') setLocked({ name: file.name, open: parsed.open })
      else await adoptPlan(parsed.plan)
    } catch (e) {
      setFileError(`Could not open ${file.name}: ${(e as Error).message}`)
    }
  }

  const shown = projection?.value
  const shownPlan = projection?.plan ?? plan
  const sim = simulation?.value ?? null
  const simulating = simulation?.plan !== plan

  return (
    <>
      <Header
        clientName={plan.client.name}
        theme={theme}
        onToggleTheme={toggle}
        onNew={() => setPlan(samplePlan())}
        onOpen={() => fileInput.current?.click()}
        onPrint={() => window.print()}
        onSave={() => setSaving(true)}
      />
      <input
        ref={fileInput}
        type="file"
        accept="application/json,.json"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) openFile(file)
          e.target.value = ''
        }}
      />

      <main className="layout">
        <Sidebar plan={plan} onChange={setPlan} states={states} />
        <div className="content">
          <div className="print-only report-cover">
            <h1>Financial plan for {plan.client.name || 'client'}</h1>
            <p className="muted">
              Prepared {PREPARED_ON}. Projections
              are estimates, not guarantees.
            </p>
          </div>
          {[fileError, error].map(
            (message) =>
              message && (
                <div key={message} className="error no-print" role="alert">
                  {message}
                </div>
              ),
          )}
          {shown ? (
            <div className={error ? 'stale' : ''} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <KpiCards plan={shownPlan} projection={shown} simulation={sim} simulating={simulating} />
              <OutcomesPanel plan={shownPlan} projection={shown} simulation={sim} simulating={simulating} />
              <div className="two-col">
                <GoalsPanel projection={shown} simulation={sim} simulating={simulating} />
                <KeyFigures plan={shownPlan} projection={shown} simulation={sim} states={states} />
              </div>
              <StrategyPanel plan={plan} />
            </div>
          ) : (
            !error && <p className="muted">Calculating…</p>
          )}
        </div>
      </main>

      {saving && <SaveDialog onSave={(password) => downloadPlan(plan, password)} onClose={() => setSaving(false)} />}
      {locked && (
        <UnlockDialog
          fileName={locked.name}
          onUnlock={async (password) => adoptPlan(await locked.open(password))}
          onClose={() => setLocked(null)}
        />
      )}
    </>
  )
}
