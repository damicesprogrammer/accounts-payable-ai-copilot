import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

export default function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div>
            <p className="text-lg font-semibold tracking-tight">AP Copilot</p>
            <p className="text-xs text-slate-500">AI-powered Accounts Payable</p>
          </div>
          <nav className="flex gap-1">
            {/* "/" e o detalhe do título (/titulos/:id) pertencem à área Accounts Payable */}
            <NavLink to="/" className={() => linkClass({ isActive: pathname === '/' || pathname.startsWith('/titulos/') })}>
              Accounts Payable
            </NavLink>
            <NavLink to="/copilot" className={linkClass}>
              AI Copilot
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
    </div>
  )
}
