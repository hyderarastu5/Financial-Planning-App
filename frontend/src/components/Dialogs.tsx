import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { TextField } from './fields'

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])
  return (
    <dialog ref={ref} aria-label={title} onCancel={onClose}>
      <h2 style={{ marginBottom: 14 }}>{title}</h2>
      {children}
    </dialog>
  )
}

export function SaveDialog({ onSave, onClose }: { onSave: (password?: string) => Promise<void>; onClose: () => void }) {
  const [protect, setProtect] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const mismatch = protect && confirm !== '' && password !== confirm
  const ready = !protect || (password.length >= 8 && password === confirm)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!ready) return
    setBusy(true)
    await onSave(protect ? password : undefined)
    setBusy(false)
    onClose()
  }

  return (
    <Modal title="Save plan" onClose={onClose}>
      <form onSubmit={submit}>
        <p className="muted" style={{ margin: 0 }}>
          The plan downloads as a file you can open again or share.
        </p>
        <label className="field checkbox">
          <input type="checkbox" checked={protect} onChange={(e) => setProtect(e.target.checked)} />
          <span>Protect with a password</span>
        </label>
        {protect && (
          <>
            <TextField label="Password (8+ characters)" type="password" value={password} onChange={setPassword} autoFocus />
            <TextField label="Repeat password" type="password" value={confirm} onChange={setConfirm} />
            {mismatch && <p className="error-text">The passwords don't match.</p>}
            <p className="field-hint">The file is encrypted. Without the password it can't be opened, and there's no way to recover it.</p>
          </>
        )}
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={!ready || busy}>
            {busy ? 'Encrypting…' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function UnlockDialog({ fileName, onUnlock, onClose }: {
  fileName: string
  onUnlock: (password: string) => Promise<void>
  onClose: () => void
}) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await onUnlock(password)
      onClose()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Password-protected plan" onClose={onClose}>
      <form onSubmit={submit}>
        <p className="muted" style={{ margin: 0 }}>
          Enter the password for {fileName}.
        </p>
        <TextField label="Password" type="password" value={password} onChange={setPassword} autoFocus />
        {error && <p className="error-text">{error}</p>}
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={!password || busy}>
            {busy ? 'Opening…' : 'Open'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
