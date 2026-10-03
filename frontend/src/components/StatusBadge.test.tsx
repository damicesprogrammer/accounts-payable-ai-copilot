import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { setLanguage } from '../i18n'
import StatusBadge from './StatusBadge'

afterEach(() => {
  setLanguage('en-US')
  localStorage.clear()
})

describe('StatusBadge', () => {
  it.each([
    ['PENDENTE', 'Pending'],
    ['APROVADO', 'Approved'],
    ['PAGO', 'Paid'],
    ['CANCELADO', 'Canceled'],
    ['ERRO', 'Error'],
  ])('EN-US: %s → %s', (status, rotulo) => {
    render(<StatusBadge status={status} />)
    expect(screen.getByText(rotulo)).toBeTruthy()
    expect(screen.queryByText(status)).toBeNull()
  })

  it.each([
    ['PENDENTE', 'Pendente'],
    ['APROVADO', 'Aprovado'],
    ['PAGO', 'Pago'],
    ['CANCELADO', 'Cancelado'],
    ['ERRO', 'Erro'],
  ])('PT-BR: %s → %s', (status, rotulo) => {
    setLanguage('pt-BR')
    render(<StatusBadge status={status} />)
    expect(screen.getByText(rotulo)).toBeTruthy()
  })

  it('troca de idioma atualiza o badge sem recarregar', () => {
    render(<StatusBadge status="PENDENTE" />)
    expect(screen.getByText('Pending')).toBeTruthy()

    act(() => setLanguage('pt-BR'))

    expect(screen.getByText('Pendente')).toBeTruthy()
    expect(screen.queryByText('Pending')).toBeNull()
  })

  it('cor vem do código da API, não do rótulo traduzido', () => {
    render(
      <>
        <StatusBadge status="ERRO" />
        <StatusBadge status="PAGO" />
      </>,
    )
    expect(screen.getByText('Error').className).toContain('red')
    expect(screen.getByText('Paid').className).toContain('emerald')
  })

  it('código desconhecido aparece como veio da API', () => {
    render(<StatusBadge status="NOVO_STATUS" />)
    expect(screen.getByText('NOVO_STATUS')).toBeTruthy()
  })
})
