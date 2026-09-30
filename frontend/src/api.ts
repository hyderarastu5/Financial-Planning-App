import type { Plan, Projection } from './types'

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
        const field = (d.loc ?? []).filter((p) => p !== 'body').join(' → ')
        const msg = d.msg.replace(/^Value error, /, '')
        return field ? `${field}: ${msg}` : msg
      })
      .join('; ')
  }
  return 'Unexpected error'
}

export async function fetchProjection(plan: Plan, signal?: AbortSignal): Promise<Projection> {
  let res: Response
  try {
    res = await fetch('/api/project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(plan),
      signal,
    })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    throw new Error('Cannot reach the backend. Is it running on port 8000?')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(describeError(body.detail))
  }
  return res.json()
}
