import { Route, Routes } from 'react-router'
import Layout from './components/Layout'
import CopilotPage from './pages/CopilotPage'
import TituloDetalhePage from './pages/TituloDetalhePage'
import TitulosPage from './pages/TitulosPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<TitulosPage />} />
        <Route path="/titulos/:id" element={<TituloDetalhePage />} />
        <Route path="/copilot" element={<CopilotPage />} />
        <Route path="*" element={<p className="text-slate-600">Page not found.</p>} />
      </Routes>
    </Layout>
  )
}
