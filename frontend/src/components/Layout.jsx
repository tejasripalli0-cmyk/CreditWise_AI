import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Menu, TrendingUp, X } from 'lucide-react'

const links = [['/', 'Home'], ['/predict', 'Predict'], ['/analytics', 'Analytics'], ['/about', 'About']]

export default function Layout() {
  const [open, setOpen] = useState(false)
  useLocation()
  return (
    <>
      <a href="#main" className="sr-only">Skip to content</a>
      <header className="nav">
        <div className="container nav-inner">
          <Link to="/" className="brand" onClick={() => setOpen(false)}>
            <span className="brand-mark"><TrendingUp size={19} /></span>CreditWise AI
          </Link>
          <button className="nav-toggle" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
          <nav className={`nav-links ${open ? 'open' : ''}`} aria-label="Main">
            {links.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}>{label}</NavLink>
            ))}
            <Link to="/predict" className="btn btn-primary btn-sm" onClick={() => setOpen(false)}>Predict credit risk</Link>
          </nav>
        </div>
      </header>
      <main id="main"><Outlet /></main>
      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div>
              <Link to="/" className="brand"><span className="brand-mark"><TrendingUp size={19} /></span>CreditWise AI</Link>
              <p className="muted small" style={{ marginTop: 12, maxWidth: 360 }}>
                A machine-learning project that estimates recorded loan payment difficulty from application details, trained on the public Home Credit dataset.
              </p>
            </div>
            <div><h4>Explore</h4>{links.map(([to, l]) => <Link key={to} to={to}>{l}</Link>)}</div>
            <div><h4>Built with</h4><span className="muted small">React, Vite, FastAPI, scikit-learn, SHAP, Recharts. Hosted on Vercel.</span></div>
          </div>
          <p className="disclaimer">
            CreditWise AI is an educational and research project. Its output is a statistical model score, not a CIBIL score or any official credit score,
            and it is not a lending, approval or rejection decision. Do not use it to make decisions about real people. Details you enter are processed
            for a single request and are not stored.
          </p>
        </div>
      </footer>
    </>
  )
}
