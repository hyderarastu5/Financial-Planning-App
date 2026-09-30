import { useEffect, useRef, useState } from 'react'
import { fetchProjection } from './api'
import { PlanForm } from './components/PlanForm'
import { Results } from './components/Results'
import { downloadPlan, readPlanFile, samplePlan } from './planFile'
import type { Plan, Projection } from './types'

export default function App() {
  const [plan, setPlan] = useState<Plan>(samplePlan)
  // The projection is kept together with the plan that produced it, so results never mix old numbers with new inputs.
  const [result, setResult] = useState<{ plan: Plan; projection: Projection } | null>(null)
  const [error, setError] = useState<string | null>(null) // current inputs can't be projected
  const [fileError, setFileError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  // Recalculate shortly after the user stops typing.
  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(() => {
      fetchProjection(plan, controller.signal)
        .then((projection) => {
          setResult({ plan, projection })
          setError(null)
        })
        .catch((e: Error) => {
          if (e.name !== 'AbortError') setError(e.message)
        })
    }, 250)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [plan])

  async function openFile(file: File) {
    try {
      const loaded = await readPlanFile(file)
      await fetchProjection(loaded) // reject files the backend can't use before replacing the current plan
      setPlan(loaded)
      setFileError(null)
    } catch (e) {
      setFileError(`Could not open ${file.name}: ${(e as Error).message}`)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>Financial Planner</h1>
        <div className="actions">
          <button type="button" onClick={() => setPlan(samplePlan())}>
            New
          </button>
          <button type="button" onClick={() => fileInput.current?.click()}>
            Open…
          </button>
          <button type="button" className="primary" onClick={() => downloadPlan(plan)}>
            Save plan
          </button>
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
        </div>
      </header>

      <main className="layout">
        <aside className="sidebar">
          <PlanForm plan={plan} onChange={setPlan} />
        </aside>
        <div className="content">
          {[fileError, error].map(
            (message) =>
              message && (
                <div key={message} className="error" role="alert">
                  {message}
                </div>
              ),
          )}
          {result ? (
            <div className={error ? 'stale' : ''}>
              <Results plan={result.plan} projection={result.projection} />
            </div>
          ) : (
            !error && <p className="muted">Calculating…</p>
          )}
        </div>
      </main>
    </div>
  )
}
