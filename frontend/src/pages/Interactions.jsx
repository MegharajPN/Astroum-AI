import { useState } from 'react'
import useApi from '../hooks/useApi.js'
import { checkInteractions, listInteractionSeeds } from '../api/services.js'
import { Panel, StateBadge } from '../components/common.jsx'

export default function Interactions() {
  const [input, setInput] = useState('')
  const [submitted, setSubmitted] = useState('')
  const check = useApi(
    () => (submitted ? checkInteractions(submitted) : Promise.resolve(null)),
    [submitted],
  )
  const seeds = useApi(() => listInteractionSeeds(), [])

  const onSubmit = (e) => {
    e.preventDefault()
    setSubmitted(input.trim())
  }

  return (
    <div className="stack">
      <h1>Severe interaction check</h1>
      <p className="muted">
        Enter ingredient names (salts, not brands). The check is a pure lookup over the seed list.
        Pairs not on the list return <StateBadge value="PARTIAL_COVERAGE" />, never a clean result.
      </p>

      <form className="filters" onSubmit={onSubmit}>
        <input
          placeholder="e.g. warfarin, aspirin, azithromycin"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit">Check pairs</button>
      </form>

      <Panel loading={check.loading && !!submitted} error={check.error}>
        {check.data && (
          <section className="panel">
            <h2>Results</h2>
            <p className="muted">Seed list size: {check.data.seed_list_pairs} pairs.</p>
            <table className="table">
              <thead><tr><th>Pair</th><th>Status</th><th>Detail</th></tr></thead>
              <tbody>
                {check.data.results.map((r) => (
                  <tr key={r.pair.join('+')}>
                    <td>{r.pair.join(' + ')}</td>
                    <td>
                      <StateBadge value={r.status} />
                      {r.severity && <> <StateBadge value={r.severity} /></>}
                    </td>
                    <td>
                      {r.evidence?.note || r.detail}
                      {r.evidence && <div className="muted">seed row {r.evidence.seed_row_id} · {r.evidence.source_tag}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </Panel>

      <section className="panel">
        <h2>Seed list (what the check can actually find)</h2>
        <Panel loading={seeds.loading} error={seeds.error}>
          {Array.isArray(seeds.data) && seeds.data.length > 0 ? (
            <table className="table compact">
              <thead><tr><th>Ingredient A</th><th>Ingredient B</th><th>Severity</th><th>Note</th></tr></thead>
              <tbody>
                {seeds.data.map((s) => (
                  <tr key={s.id}>
                    <td>{s.ingredient_a}</td>
                    <td>{s.ingredient_b}</td>
                    <td><StateBadge value={s.severity} /></td>
                    <td>{s.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No seed data available.</p>
          )}
        </Panel>
      </section>
    </div>
  )
}