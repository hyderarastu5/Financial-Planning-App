import type {
  AccountAnalysis,
  Comparison,
  ComparisonKind,
  Holding,
  Plan,
  Projection,
  Simulation,
  StateOption,
} from './types'

interface ValidationIssue {
  loc?: (string | number)[]
  msg: string
}

// FastAPI returns either a string or a list of pydantic issues in `detail`.
function describeError(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return (detail as ValidationIssue[])
      .map((d) => {
        const field = (d.loc ?? []).filter((p) => p !== 'body' && p !== 'plan').join(' → ')
        const msg = d.msg.replace(/^Value error, /, '')
        return field ? `${field}: ${msg}` : msg
      })
      .join('; ')
  }
  return 'Unexpected error'
}

async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    throw new Error('Cannot reach the backend. Is it running on port 8000?')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(describeError(data.detail))
  }
  return res.json()
}

export const fetchProjection = (plan: Plan, signal?: AbortSignal) =>
  request<Projection>('/api/project', plan, signal)

// A fixed seed keeps the probabilities steady while the user edits unrelated fields.
export const fetchSimulation = (plan: Plan, signal?: AbortSignal) =>
  request<Simulation>('/api/simulate', { plan, runs: 1000, seed: 1 }, signal)

export const fetchComparison = (plan: Plan, kind: ComparisonKind) =>
  request<Comparison>('/api/compare', { plan, kind })

export const analyzeHoldings = (holdings: Holding[]) =>
  request<AccountAnalysis>('/api/holdings/analyze', holdings)

export const fetchStates = () => request<StateOption[]>('/api/states')
