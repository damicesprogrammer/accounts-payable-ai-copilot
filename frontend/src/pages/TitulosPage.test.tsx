import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { setLanguage } from '../i18n'
import TitulosPage from './TitulosPage'

const TITULO = {
  id: 1,
  numero: 'NF-0001',
  fornecedor_id: 1,
  fornecedor: { id: 1, nome: 'Alfa Tecnologia' },
  descricao: 'Teste',
  data_emissao: '2026-09-01',
  data_vencimento: '2026-10-01',
  valor_total: '100.00',
  status: 'PENDENTE',
}

function api() {
  return vi.fn((url: string) =>
    Promise.resolve(new Response(JSON.stringify(url.includes('/fornecedores') ? [] : [TITULO]))),
  )
}

function renderizar() {
  render(
    <MemoryRouter>
      <TitulosPage />
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  setLanguage('en-US')
  localStorage.clear()
})

describe('TitulosPage', () => {
  it('mostra o status traduzido e atualiza ao trocar o idioma', async () => {
    vi.stubGlobal('fetch', api())
    renderizar()

    expect(await screen.findByText('Pending')).toBeTruthy()

    act(() => setLanguage('pt-BR'))

    expect(screen.getAllByText('Pendente').length).toBeGreaterThan(0)
    expect(screen.queryByText('PENDENTE')).toBeNull()
  })

  it('filtro mostra o rótulo, mas envia o código do domínio à API', async () => {
    const fetch = api()
    vi.stubGlobal('fetch', fetch)
    renderizar()
    await screen.findByText('NF-0001')

    const opcao = screen.getByRole('option', { name: 'Approved' }) as HTMLOptionElement
    expect(opcao.value).toBe('APROVADO')

    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'APROVADO' } })

    await vi.waitFor(() =>
      expect(fetch.mock.calls.some(([url]) => String(url).includes('status=APROVADO'))).toBe(true),
    )
  })
})
