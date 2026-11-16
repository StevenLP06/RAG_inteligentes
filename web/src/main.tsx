import { LazyMotion, MotionConfig } from 'motion/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Motion se usa con LazyMotion + componentes `m`: las funciones de animación se cargan aparte,
// reduciendo el JavaScript inicial. `reducedMotion="user"` respeta la preferencia del sistema.
const loadFeatures = () => import('motion/react').then((mod) => mod.domMax)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LazyMotion features={loadFeatures} strict>
      <MotionConfig reducedMotion="user">
        <App />
      </MotionConfig>
    </LazyMotion>
  </StrictMode>,
)
