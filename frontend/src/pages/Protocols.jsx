import { useState } from 'react'
import useApi from '../hooks/useApi.js'
import { searchProtocolUnits } from '../api/services.js'
import { Pager, Panel, StateBadge } from '../components/common.jsx'

const UNIT_TYPES = ['', 'RECOMMENDATION', 'WORKFLOW_STEP', 'REFERRAL', 'CONTRAINDICATION', 'MONITORING']

export default function Protocols() {
  const [q, setQ] = useState('')
  const [sourceKind, setSourceKind] = useState('')
  const [unitType, setUnitType] = useState('')
  const [page, setPage] = useState(1)

  const units = useApi(
    () => searchProtocolUnits({ q, source_kind: sourceKind, unit_type: unitType, page }),
    [q, sourceKind, unitType, page],
  )

  const onFilter = (setter) => (e) => {
    setter(e.target.value)
    setPage(1)
  }

  return (
    <div className="stack">
      <h1>Protocol references</h1>
      <p className="muted">
        Each row carries its edition and page anchor. The clinic's own protocol is labelled as such
        and is never presented as national guidance. Where editions or sources disagree, show both.
      </p>

      <div className="filters">
        <input placeholder="Search, e.g. azithromycin, amoxicillin, ORS" value={q} onChange={onFilter(setQ)} />
        <select value={sourceKind} onChange={onFilter(setSourceKind)}>
          <option value="">National + clinic</option>
          <option value="NATIONAL_STW">National STW only</option>
          <option value="LOCAL_PROTOCOL">Clinic protocol only</option>
        </select>
        <select value={unitType} onChange={onFilter(setUnitType)}>
          {UNIT_TYPES.map((t) => <option key={t} value={t}>{t || 'Any unit type'}</option>)}
        </select>
      </div>

      <Panel loading={units.loading} error={units.error}>
        {units.data && (
          <>
            <ul className="units">
              {units.data.results.map((u) => (
                <li key={u.id} className="unit">
                  <div className="unit-head">
                    <StateBadge value={u.source_kind} />
                    <StateBadge value={u.unit_type} />
                    {u.has_dose_text && <span className="badge state-muted">contains dose text: quote, do not compute</span>}
                  </div>
                  <div>{u.text}</div>
                  <div className="muted cite">
                    {u.source_ref} · {u.specialty}
                    {u.effective_date ? ` · effective ${u.effective_date}` : ''}
                  </div>
                </li>
              ))}
              {units.data.results.length === 0 && (
                <li className="muted">No units match. A miss means the corpus does not cover this, not that there is no answer.</li>
              )}
            </ul>
            <Pager data={units.data} page={page} setPage={setPage} />
          </>
        )}
      </Panel>
    </div>
  )
}
