import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/drugs', label: 'Drug master' },
  { to: '/interactions', label: 'Interaction check' },
  { to: '/stock', label: 'Pharmacy stock' },
  { to: '/protocols', label: 'Protocols' },
  { to: '/gaps', label: 'Gaps register' },
]

export default function Layout() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">Astroum AI <span>Reference console</span></div>
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">
        Decision support over versioned reference data. The doctor decides.
      </footer>
    </div>
  )
}
