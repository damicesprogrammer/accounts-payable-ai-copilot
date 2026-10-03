import { Route, Routes } from 'react-router'
import Layout from './components/Layout'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="*" element={<p className="text-slate-600">Page not found.</p>} />
      </Routes>
    </Layout>
  )
}
