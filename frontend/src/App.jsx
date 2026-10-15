import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Drugs from './pages/Drugs.jsx'
import Interactions from './pages/Interactions.jsx'
import Stock from './pages/Stock.jsx'
import Protocols from './pages/Protocols.jsx'
import Gaps from './pages/Gaps.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/drugs" element={<Drugs />} />
        <Route path="/interactions" element={<Interactions />} />
        <Route path="/stock" element={<Stock />} />
        <Route path="/protocols" element={<Protocols />} />
        <Route path="/gaps" element={<Gaps />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
