export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

// $1.35M, $851K, $2,683
export function shortMoney(n: number) {
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${n < 0 ? '−' : ''}$${(abs / 1e6).toFixed(2).replace(/\.?0+$/, '')}M`
  if (abs >= 1e5) return `${n < 0 ? '−' : ''}$${Math.round(abs / 1e3)}K`
  return money(n)
}

export const compactMoney = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 })

export const pct = (share: number, digits = 0) => `${(share * 100).toFixed(digits)}%`

// Traffic-light class for a probability or funded share.
export const status = (share: number) => (share >= 0.9 ? 'good' : share >= 0.5 ? 'warn' : 'bad')
