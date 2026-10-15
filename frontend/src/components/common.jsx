// Shared presentational pieces: state badges, pager, loading/error panels.

const STATE_CLASS = {
  HIT: 'state-hit',
  CHECKED_NO_HIT: 'state-ok',
  PARTIAL_COVERAGE: 'state-warn',
  UNVERIFIED_INPUT: 'state-warn',
  NOT_CHECKED: 'state-muted',
  DATA_EXPIRED: 'state-warn',
  SOURCE_CONFLICT: 'state-warn',
  SERVICE_UNAVAILABLE: 'state-hit',
  OPEN: 'state-warn',
  RESOLVED: 'state-ok',
  ACCEPTED: 'state-muted',
  HIGH: 'state-hit',
  MEDIUM: 'state-warn',
  LOW: 'state-muted',
  AMBIGUOUS: 'state-warn',
  UNMATCHED: 'state-muted',
  EXACT_UNIQUE: 'state-ok',
  NATIONAL_STW: 'state-ok',
  LOCAL_PROTOCOL: 'state-warn',
}

export function StateBadge({ value }) {
  if (!value) return null
  return <span className={`badge ${STATE_CLASS[value] || 'state-muted'}`}>{value}</span>
}

export function Pager({ data, page, setPage }) {
  if (!data) return null
  const pages = Math.max(1, Math.ceil((data.count || 0) / 25))
  return (
    <div className="pager">
      <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
      <span>
        Page {page} of {pages} · {data.count ?? 0} rows
      </span>
      <button disabled={!data.next} onClick={() => setPage(page + 1)}>Next</button>
    </div>
  )
}

export function Panel({ loading, error, children }) {
  if (loading) return <div className="panel muted">Loading…</div>
  if (error) {
    const unavailable = error.status === 503
    return (
      <div className={`panel ${unavailable ? 'panel-error' : 'panel-warn'}`}>
        <strong>{unavailable ? 'SERVICE_UNAVAILABLE' : 'Request failed'}</strong>
        <div>{error.message}</div>
        {unavailable && <div className="muted">The error was recorded in the gaps register.</div>}
      </div>
    )
  }
  return children
}
