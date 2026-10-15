import { useState } from 'react'
import useApi from '../hooks/useApi.js'
import { listGaps, resolveGap } from '../api/services.js'
import { Pager, Panel, StateBadge } from '../components/common.jsx'

export default function Gaps() {
  const [status, setStatus] = useState('OPEN')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [busy, setBusy] = useState(null)
  const [actionError, setActionError] = useState(null)

  const gaps = useApi(
    () => listGaps({ status, category, page }),
    [status, category, page],
  )

  const resolve = async (row, newStatus) => {
    const note = window.prompt(
      newStatus === 'RESOLVED' ? 'How was this resolved?' : 'Why is this accepted as a limitation?',
    )
    if (!note) return
    setBusy(row.id)
    setActionError(null)
    try {
      await resolveGap(row.id, { status: newStatus, resolution_note: note })
      gaps.reload()
    } catch (err) {
      setActionError(err)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="stack">
      <h1>Gaps register</h1>
      <p className="muted">
        Missing data, unmapped brands, rejected rows and service errors. Nothing here is hidden
        or auto-resolved. Resolving a gap needs a note.
      </p>

      <div className="filters">
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="OPEN">Open</option>
          <option value="RESOLVED">Resolved</option>
          <option value="ACCEPTED">Accepted limitation</option>
          <option value="">All</option>
        </select>
        <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(1) }}>
          <option value="">Any category</option>
          <option value="MISSING_DATA">Missing data</option>
          <option value="AMBIGUOUS_MAPPING">Ambiguous mapping</option>
          <option value="ANOMALY">Anomaly</option>
          <option value="PARSE_REJECT">Parse reject</option>
          <option value="SOURCE_CONFLICT">Source conflict</option>
          <option value="SERVICE_ERROR">Service error</option>
        </select>
      </div>

      {actionError && <div className="panel panel-error">{actionError.message}</div>}

      <Panel loading={gaps.loading} error={gaps.error}>
        {gaps.data && (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Severity</th><th>Category</th><th>Reason</th><th>Source</th>
                    <th>Message</th><th>Status</th><th />
                  </tr>
                </thead>
                <tbody>
                  {gaps.data.results.map((g) => (
                    <tr key={g.id}>
                      <td><StateBadge value={g.severity} /></td>
                      <td>{g.category}</td>
                      <td className="mono">{g.reason_code}</td>
                      <td className="muted">{g.source_ref}</td>
                      <td>{g.message}</td>
                      <td><StateBadge value={g.status} /></td>
                      <td>
                        {g.status === 'OPEN' && (
                          <div className="row-actions">
                            <button disabled={busy === g.id} onClick={() => resolve(g, 'RESOLVED')}>Resolve</button>
                            <button className="ghost" disabled={busy === g.id} onClick={() => resolve(g, 'ACCEPTED')}>Accept</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {gaps.data.results.length === 0 && (
                    <tr><td colSpan={7} className="muted">Nothing in this view.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <Pager data={gaps.data} page={page} setPage={setPage} />
          </>
        )}
      </Panel>
    </div>
  )
}
