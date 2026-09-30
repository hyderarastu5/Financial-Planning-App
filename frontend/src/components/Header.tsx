import type { Theme } from '../useTheme'

interface Props {
  clientName: string
  theme: Theme
  onToggleTheme: () => void
  onNew: () => void
  onOpen: () => void
  onPrint: () => void
  onSave: () => void
}

const TODAY = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })

export function Header({ clientName, theme, onToggleTheme, onNew, onOpen, onPrint, onSave }: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <h1>Financial Planner</h1>
        <span>
          Prepared for {clientName || 'a client'} · {TODAY}
        </span>
      </div>
      <div className="topbar-actions">
        <button
          type="button"
          className="btn theme-toggle"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <circle cx="12" cy="12" r="4.5" />
              <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
            </svg>
          )}
        </button>
        <button type="button" className="btn" onClick={onNew}>
          New
        </button>
        <button type="button" className="btn" onClick={onOpen}>
          Open plan
        </button>
        <button type="button" className="btn" onClick={onPrint}>
          Download report
        </button>
        <button type="button" className="btn btn-primary" onClick={onSave}>
          Save plan
        </button>
      </div>
    </header>
  )
}
