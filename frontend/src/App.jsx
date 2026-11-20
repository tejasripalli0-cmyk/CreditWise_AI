import { lazy, Suspense, useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { Spinner } from './components/ui.jsx'

// Route-level code splitting keeps the first load small; chart code only loads on pages that use it.
const Home = lazy(() => import('./pages/Home.jsx'))
const Predict = lazy(() => import('./pages/Predict.jsx'))
const Results = lazy(() => import('./pages/Results.jsx'))
const Analytics = lazy(() => import('./pages/Analytics.jsx'))
const About = lazy(() => import('./pages/About.jsx'))

function ScrollTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => { if (!hash) window.scrollTo(0, 0) }, [pathname, hash])
  return null
}

export default function App() {
  return (
    <>
      <ScrollTop />
      <Suspense fallback={<div className="container empty"><Spinner dark /></div>}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="predict" element={<Predict />} />
            <Route path="results" element={<Results />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="about" element={<About />} />
            <Route path="*" element={<div className="container empty"><h2>Page not found</h2><p className="muted">That page does not exist.</p></div>} />
          </Route>
        </Routes>
      </Suspense>
    </>
  )
}
