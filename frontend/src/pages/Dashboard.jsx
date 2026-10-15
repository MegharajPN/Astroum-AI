import useApi from '../hooks/useApi.js'
import { getDashboard, getStockSummary } from '../api/services.js'
import { Panel, StateBadge } from '../components/common.jsx'

const LABELS = {
  products: 'Brands / SKUs',
  fdc_products: 'Fixed-dose combinations',
  product_ingredients: 'Ingredient rows',
  nlem_entries: 'NLEM entries',
  jan_aushadhi_items: 'Jan Aushadhi items',
  regulatory_events: 'Gazette events',
  severe_interaction_pairs: 'Severe pairs (seed)',
  stock_lines: 'Stock lines',
  protocol_documents: 'Protocol editions',
  protocol_units: 'Decision units',
}

export default function Dashboard() {
  const dash = useApi(getDashboard, [])
  const stock = useApi(getStockSummary, [])

  return (
    <div className="stack">
      <h1>Dashboard</h1>
      <Panel loading={dash.loading} error={dash.error}>
        {dash.data && (
          <>
            <div className="cards">
              {Object.entries(dash.data.counts).map(([key, value]) => (
                <div className="card" key={key}>
                  <div className="card-value">{value.toLocaleString()}</div>
                  <div className="card-label">{LABELS[key] || key}</div>
                </div>
              ))}
            </div>

            <div className="grid-2">
              <section className="panel">
                <h2>Open gaps by severity</h2>
                {Object.keys(dash.data.open_gaps_by_severity).length === 0 && (
                  <div className="muted">No open gaps.</div>
                )}
                <ul className="plain">
                  {Object.entries(dash.data.open_gaps_by_severity).map(([sev, n]) => (
                    <li key={sev}><StateBadge value={sev} /> {n}</li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <h2>Latest load per dataset</h2>
                <table className="table">
                  <thead>
                    <tr><th>Dataset</th><th>Status</th><th>Loaded</th><th>Rejected</th></tr>
                  </thead>
                  <tbody>
                    {Object.entries(dash.data.latest_batches).map(([name, b]) => (
                      <tr key={name}>
                        <td>{name}</td>
                        <td><StateBadge value={b.status} /></td>
                        <td>{b.rows_loaded}</td>
                        <td>{b.rows_rejected}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </div>
          </>
        )}
      </Panel>

      <Panel loading={stock.loading} error={stock.error}>
        {stock.data && (
          <section className="panel">
            <h2>Pharmacy stock</h2>
            <p className="muted">{stock.data.note}</p>
            <div className="cards">
              <div className="card"><div className="card-value">{stock.data.lines}</div><div className="card-label">Lines</div></div>
              <div className="card"><div className="card-value">{stock.data.expired}</div><div className="card-label">Expired</div></div>
              <div className="card"><div className="card-value">{stock.data.expiring_within_window}</div><div className="card-label">Expiring in {stock.data.window_days} days</div></div>
              <div className="card"><div className="card-value">{stock.data.expiry_unparsed}</div><div className="card-label">Expiry unreadable</div></div>
            </div>
          </section>
        )}
      </Panel>
    </div>
  )
}
