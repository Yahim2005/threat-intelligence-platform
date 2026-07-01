// src/hooks/useDarkMode.js
import { useState, useEffect } from 'react'

export function useDarkMode() {
  const [dark, setDark] = useState(() => {
    return localStorage.getItem('tip-theme') === 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark')
      localStorage.setItem('tip-theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('tip-theme', 'light')
    }
  }, [dark])

  return [dark, setDark]
}