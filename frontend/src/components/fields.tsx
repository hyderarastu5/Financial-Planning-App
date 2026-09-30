import { useState } from 'react'

type Unit = 'money' | 'percent' | 'plain'

function toDisplay(value: number | null, unit: Unit): string {
  if (value === null) return ''
  // Rates are stored as decimals and shown as percentages; round away float noise.
  return unit === 'percent' ? String(Math.round(value * 100 * 1e4) / 1e4) : String(value)
}

interface NumberFieldProps {
  label: string
  value: number | null
  onChange: (value: number | null) => void
  unit?: Unit
  optional?: boolean // empty input means null instead of 0
  placeholder?: string
  hint?: string
  wide?: boolean
}

// Keeps the raw text while typing so partial input like "7." or "" is not clobbered.
export function NumberField({ label, value, onChange, unit = 'plain', optional, placeholder, hint, wide }: NumberFieldProps) {
  // null while not editing: show the formatted value instead.
  const [text, setText] = useState<string | null>(null)

  function handle(raw: string) {
    setText(raw)
    const cleaned = raw.replace(/[$,%\s]/g, '')
    if (cleaned === '') return onChange(optional ? null : 0)
    const n = Number(cleaned)
    if (Number.isFinite(n)) onChange(unit === 'percent' ? n / 100 : n)
  }

  return (
    <label className={`field${wide ? ' span-2' : ''}`}>
      <span className="field-label">{label}</span>
      <span className={`input-wrap unit-${unit}`}>
        <input
          inputMode="decimal"
          value={text ?? toDisplay(value, unit)}
          placeholder={placeholder}
          onFocus={() => setText(toDisplay(value, unit))}
          onBlur={() => setText(null)}
          onChange={(e) => handle(e.target.value)}
        />
      </span>
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

interface TextFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'date' | 'password'
  wide?: boolean
  autoFocus?: boolean
}

export function TextField({ label, value, onChange, type = 'text', wide, autoFocus }: TextFieldProps) {
  return (
    <label className={`field${wide ? ' span-2' : ''}`}>
      <span className="field-label">{label}</span>
      <span className="input-wrap">
        <input type={type} value={value} autoFocus={autoFocus} onChange={(e) => onChange(e.target.value)} />
      </span>
    </label>
  )
}

interface SelectFieldProps<T extends string> {
  label: string
  value: T
  options: Record<T, string>
  onChange: (value: T) => void
  wide?: boolean
}

export function SelectField<T extends string>({ label, value, options, onChange, wide }: SelectFieldProps<T>) {
  return (
    <label className={`field${wide ? ' span-2' : ''}`}>
      <span className="field-label">{label}</span>
      <span className="input-wrap">
        <select value={value} onChange={(e) => onChange(e.target.value as T)}>
          {(Object.entries(options) as [T, string][]).map(([v, text]) => (
            <option key={v} value={v}>
              {text}
            </option>
          ))}
        </select>
      </span>
    </label>
  )
}

export function CheckboxField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="field checkbox">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  )
}

export function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" className="btn-icon" aria-label={label} onClick={onClick}>
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M3 3l10 10M13 3L3 13" />
      </svg>
    </button>
  )
}
