import { useState } from 'react'
import useApi from '../hooks/useApi.js'
import { getProduct, searchNlem, searchProducts, searchRegulatoryEvents } from '../api/services.js'
import { Pager, Panel, StateBadge } from '../components/common.jsx'

export default function Drugs() {
  const [q, setQ] = useState('')
  const [ingredient, setIngredient] = useState('')
  const [fdcOnly, setFdcOnly] = useState('')
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState(null)

  const products = useApi(
    () => searchProducts({ q, ingredient, fdc: fdcOnly, page }),
    [q, ingredient, fdcOnly, page],
  )
  const detail = useApi(
    () => (selectedId ? getProduct(selectedId) : Promise.resolve(null)),
    [selectedId],
  )
  const nlem = useApi(
    () => (detail.data ? searchNlem({ q: detail.data.ingredients[0]?.ingredient_name }) : Promise.resolve(null)),
    [detail.data],
  )
  const events = useApi(
    () => (detail.data
      ? searchRegulatoryEvents({ target: detail.data.ingredients.map((i) => i.ingredient_name).join(' + ') })
      : Promise.resolve(null)),
    [detail.data],
  )

  const onFilter = (setter) => (e) => {
    setter(e.target.value)
    setPage(1)
  }

  return (
    <div className="stack">
      <h1>Drug master</h1>
      <p className="muted">
        Search by brand, salt or strength. Results show the salt-level decomposition
        that the safety rail uses. Ambiguous brands are never silently resolved.
      </p>

      <div className="filters">
        <input placeholder="Brand or strength (e.g. Dolo, 650)" value={q} onChange={onFilter(setQ)} />
        <input placeholder="Ingredient (e.g. paracetamol)" value={ingredient} onChange={onFilter(setIngredient)} />
        <select value={fdcOnly} onChange={onFilter(setFdcOnly)}>
          <option value="">All forms</option>
          <option value="true">Fixed-dose combinations only</option>
          <option value="false">Single-ingredient only</option>
        </select>
      </div>

      <div className="grid-2 wide-left">
        <Panel loading={products.loading} error={products.error}>
          {products.data && (
            <>
              <table className="table">
                <thead>
                  <tr><th>Brand</th><th>Form</th><th>Strength (as written)</th><th>FDC</th></tr>
                </thead>
                <tbody>
                  {products.data.results.map((p) => (
                    <tr
                      key={p.id}
                      className={`clickable ${selectedId === p.id ? 'selected' : ''}`}
                      onClick={() => setSelectedId(p.id)}
                    >
                      <td>{p.brand_name}</td>
                      <td>{p.dose_form}</td>
                      <td>{p.strength_text}</td>
                      <td>{p.is_fdc ? 'Yes' : ''}</td>
                    </tr>
                  ))}
                  {products.data.results.length === 0 && (
                    <tr><td colSpan={4} className="muted">No matches. Absence here is not a clearance.</td></tr>
                  )}
                </tbody>
              </table>
              <Pager data={products.data} page={page} setPage={setPage} />
            </>
          )}
        </Panel>

        <aside className="panel">
          <h2>Decomposition</h2>
          {!selectedId && <div className="muted">Select a product.</div>}
          {detail.data && (
            <>
              <div className="strong">{detail.data.brand_name}</div>
              <div className="muted">{detail.data.manufacturer} · source {detail.data.source} {detail.data.source_version}</div>
              <table className="table compact">
                <thead><tr><th>Salt</th><th>Strength (mg)</th><th>Method</th></tr></thead>
                <tbody>
                  {detail.data.ingredients.map((i) => (
                    <tr key={i.position}>
                      <td>{i.ingredient_name}</td>
                      <td>{i.strength_mg ?? <StateBadge value="MISSING_DATA" />}</td>
                      <td>{i.mapping_method} ({i.confidence})</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <h3>NLEM</h3>
              <Panel loading={nlem.loading} error={nlem.error}>
                {nlem.data && (nlem.data.results.length
                  ? <ul className="plain">{nlem.data.results.map((n) => (
                      <li key={n.id}>{n.medicine} · {n.care_levels || 'no care level'} · {n.edition}</li>
                    ))}</ul>
                  : <div className="muted">Not found in the NLEM extract.</div>)}
              </Panel>

              <h3>Gazette events mentioning these salts</h3>
              <Panel loading={events.loading} error={events.error}>
                {events.data && (events.data.results.length
                  ? <ul className="plain">{events.data.results.map((e) => (
                      <li key={e.id}>
                        <StateBadge value={e.action} /> {e.notification_id} · effective {e.effective_date}
                        <div className="muted">{e.target_description}</div>
                      </li>
                    ))}</ul>
                  : <div className="muted">No event matches this exact combination. Not a clearance.</div>)}
              </Panel>
            </>
          )}
        </aside>
      </div>
    </div>
  )
}
