import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router'
import { LANGUAGES, useI18n } from '../i18n'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

export default function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const { t } = useI18n()
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div>
            <p className="text-lg font-semibold tracking-tight">AP Copilot</p>
            <p className="text-xs text-slate-500">{t('layout.tagline')}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <nav className="flex gap-1">
              {/* "/" e o detalhe do título (/titulos/:id) pertencem à área Accounts Payable */}
              <NavLink
                to="/"
                className={() => linkClass({ isActive: pathname === '/' || pathname.startsWith('/titulos/') })}
              >
                {t('nav.accountsPayable')}
              </NavLink>
              <NavLink to="/copilot" className={linkClass}>
                {t('nav.copilot')}
              </NavLink>
            </nav>
            <LanguageToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
    </div>
  )
}

function LanguageToggle() {
  const { language, setLanguage, t } = useI18n()
  return (
    <div role="group" aria-label={t('layout.language')} className="flex rounded-md border border-slate-300 p-0.5">
      {LANGUAGES.map((l) => (
        <button
          key={l}
          type="button"
          aria-pressed={language === l}
          onClick={() => setLanguage(l)}
          className={`rounded px-2 py-1 text-xs font-medium ${
            language === l ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
