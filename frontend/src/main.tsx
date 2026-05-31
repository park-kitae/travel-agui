import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { injectStyles } from '@a2ui/react/styles'
import App from './App.tsx'

injectStyles()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
