import { createContext, useContext, useMemo, useState } from 'react'

// In-memory only (no localStorage / cookies / server storage): applicant details vanish on refresh or tab close.
const Ctx = createContext(null)

export function PredictionProvider({ children }) {
  const [values, setValues] = useState({})      // feature name -> raw entered value
  const [optional, setOptional] = useState([])  // optional feature names the user added
  const [result, setResult] = useState(null)
  const value = useMemo(() => ({ values, setValues, optional, setOptional, result, setResult }), [values, optional, result])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const usePrediction = () => useContext(Ctx)
