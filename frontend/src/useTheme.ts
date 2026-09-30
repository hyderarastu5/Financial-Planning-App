import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const systemTheme = (): Theme => (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')

function savedTheme(): Theme | null {
  try {
    const t = localStorage.getItem('theme')
    return t === 'light' || t === 'dark' ? t : null
  } catch {
    return null
  }
}

// Follows the system setting until the user picks a theme with the toggle; the pick is remembered.
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => savedTheme() ?? systemTheme())

  useEffect(() => {
    if (savedTheme()) return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const follow = () => setTheme(systemTheme())
    media.addEventListener('change', follow)
    return () => media.removeEventListener('change', follow)
  }, [])

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem('theme', next)
    } catch {
      // private browsing: the choice just isn't remembered
    }
    setTheme(next)
  }

  return { theme, toggle }
}
