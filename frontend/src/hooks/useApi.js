import { useCallback, useEffect, useState } from 'react'

// Runs an async loader whenever `deps` change. Returns the same shape everywhere:
// { data, error, loading, reload }. Errors are kept, never swallowed.
export default function useApi(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })

  const run = useCallback(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    loader()
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((error) => !cancelled && setState({ data: null, error, loading: false }))
    return () => {
      cancelled = true
    }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => run(), [run])

  return { ...state, reload: run }
}
