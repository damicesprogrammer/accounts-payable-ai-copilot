import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { LIMITE_TITULOS, listarFornecedores, listarTitulos, type FiltrosTitulos } from '../api/titulos'
import { useApi } from '../api/useApi'
import EmptyState from '../components/EmptyState'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import StatusBadge from '../components/StatusBadge'
import { useI18n } from '../i18n'
import { formatCurrency, formatDate } from '../utils/format'

const STATUS = ['PENDENTE', 'APROVADO', 'PAGO', 'CANCELADO', 'ERRO']

const selectClass =
  'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none'

export default function TitulosPage() {
  const navigate = useNavigate()
  const { t, label } = useI18n()
  const [filtros, setFiltros] = useState<FiltrosTitulos>({ status: '', fornecedorId: '', vencidos: false })
  // A filtragem é sempre feita pelo backend.
  const titulos = useApi(JSON.stringify(filtros), () => listarTitulos(filtros))
  const fornecedores = useApi('fornecedores', listarFornecedores)

  return (
    <section>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">{t('nav.accountsPayable')}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('titulos.subtitle')}</p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          aria-label={t('titulos.status')}
          className={selectClass}
          value={filtros.status}
          onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
        >
          <option value="">{t('titulos.allStatuses')}</option>
          {STATUS.map((s) => (
            <option key={s} value={s}>
              {label(s)}
            </option>
          ))}
        </select>
        <select
          aria-label={t('titulos.supplier')}
          className={selectClass}
          value={filtros.fornecedorId}
          onChange={(e) => setFiltros({ ...filtros, fornecedorId: e.target.value })}
        >
          <option value="">{t('titulos.allSuppliers')}</option>
          {fornecedores.data?.map((f) => (
            <option key={f.id} value={f.id}>
              {f.nome}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300"
            checked={filtros.vencidos}
            onChange={(e) => setFiltros({ ...filtros, vencidos: e.target.checked })}
          />
          {t('titulos.overdueOnly')}
        </label>
        {titulos.data && (
          <span className="ml-auto text-sm text-slate-500">
            {titulos.data.length === LIMITE_TITULOS
              ? t('titulos.showingFirst', { count: LIMITE_TITULOS })
              : t(titulos.data.length === 1 ? 'titulos.record' : 'titulos.records', { count: titulos.data.length })}
          </span>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
        {titulos.loading && <div className="px-4"><Loading /></div>}
        {titulos.error && <div className="p-4"><ErrorMessage message={titulos.error} /></div>}
        {titulos.data?.length === 0 && <EmptyState text={t('titulos.empty')} />}
        {!!titulos.data?.length && (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">{t('titulo.number')}</th>
                <th className="px-4 py-3">{t('titulo.supplier')}</th>
                <th className="px-4 py-3">{t('titulo.dueDate')}</th>
                <th className="px-4 py-3 text-right">{t('titulo.totalAmount')}</th>
                <th className="px-4 py-3">{t('titulo.status')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {titulos.data.map((t) => (
                <tr
                  key={t.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => navigate(`/titulos/${t.id}`)}
                >
                  <td className="whitespace-nowrap px-4 py-3 font-medium">
                    <Link to={`/titulos/${t.id}`} className="text-slate-900 hover:underline">
                      {t.numero}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{t.fornecedor.nome}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-700">{formatDate(t.data_vencimento)}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right font-medium tabular-nums">{formatCurrency(t.valor_total)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={t.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
