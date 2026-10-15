import { useState } from 'react'
import useApi from '../hooks/useApi.js'
import { getStock } from '../api/services.js'
import { Pager, Panel, StateBadge } from '../components/common.jsx'

export default function Stock() {
  const [q, setQ] = useState('')
  const [matchStatus, setMatchStatus] = useState('')
  const [expiring, setExpiring] = useState('')
  const [page, setPage] = useState(1)

  const stock = useApi(
    () => getStock({ q, match_status: matchStatus, expiring, page }),
    [q, matchStatus, expiring, page],
  )

  const onFilter = (setter) => (e) => {
    setter(e.target.value)
    setPage(1)
  }

  return (
    <div className="stack">
      <h1>Pharmacy stock</h1>
      <p className="muted">
        Clinic billing lines, treated as untrusted input. A line is linked to a CDCI product only when
        its brand matches exactly once. Anything else stays unlinked and is listed here.
      </p>

      <div className="filters">
        <input placeholder="Search billed name" value={q} onChange={onFilter(setQ)} />
        <select value={matchStatus} onChange={onFilter(setMatchStatus)}>
          <option value="">Any match status</option>
          <option value="EXACT_UNIQUE">Exact unique</option>
          <option value="AMBIGUOUS">Ambiguous</option>
          <option value="UNMATCHED">Unmatched</option>
        </select>
        <select value={expiring} onChange={onFilter(setExpiring)}>
          <option value="">Any expiry</option>
          <option value="1">Expiring within window</option>
        </select>
      </div>

      <Panel loading={stock.loading} error={stock.error}>
        {stock.data && (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Line</th><th>Billed name</th><th>Key</th><th>Pack</th><th>Qty</th>
                    <th>MRP ₹</th><th>Expiry</th><th>Match</th><th>Linked product</th>
                  </tr>
                </thead>
                <tbody>
                  {stock.data.results.map((s) => (
                    <tr key={s.id}>
                      <td>{s.line_no}</td>
                      <td>{s.item_name_as_billed}</td>
                      <td className="muted">{s.billed_brand_key}</td>
                      <td>{s.pack_tokens}</td>
                      <td>{s.qty_units ?? <StateBadge value="MISSING_DATA" />}</td>
                      <td>{s.mrp_inr ?? <StateBadge value="MISSING_DATA" />}</td>
                      <td>{s.expiry_date ?? s.expiry_text}</td>
                      <td><StateBadge value={s.match_status} /></td>
                      <td>{s.matched_product ? s.matched_product.brand_name : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pager data={stock.data} page={page} setPage={setPage} />
          </>
        )}
      </Panel>
    </div>
  )
}
