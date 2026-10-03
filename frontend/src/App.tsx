import { Route, Routes } from 'react-router'
import Layout from './components/Layout'
import { useI18n } from './i18n'
import CopilotPage from './pages/CopilotPage'
import TituloDetalhePage from './pages/TituloDetalhePage'
import TitulosPage from './pages/TitulosPage'

export default function App() {
  const { t } = useI18n()
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<TitulosPage />} />
        <Route path="/titulos/:id" element={<TituloDetalhePage />} />
        <Route path="/copilot" element={<CopilotPage />} />
        <Route path="*" element={<p className="text-slate-600">{t('common.pageNotFound')}</p>} />
      </Routes>
    </Layout>
  )
}
