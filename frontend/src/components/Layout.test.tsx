import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import { setLanguage } from '../i18n'
import Layout from './Layout'

function renderizar(rota = '/') {
  render(
    <MemoryRouter initialEntries={[rota]}>
      <Layout>conteúdo</Layout>
    </MemoryRouter>,
  )
}

function ativo(rota: string) {
  renderizar(rota)
  return {
    ap: screen.getByRole('link', { name: 'Accounts Payable' }).className.includes('bg-slate-900'),
    copilot: screen.getByRole('link', { name: 'AI Copilot' }).className.includes('bg-slate-900'),
  }
}

afterEach(() => {
  setLanguage('en-US')
  localStorage.clear()
})

describe('Layout', () => {
  it.each([
    ['/', { ap: true, copilot: false }],
    ['/titulos/4', { ap: true, copilot: false }],
    ['/copilot', { ap: false, copilot: true }],
  ])('destaca a área da rota %s', (rota, esperado) => {
    expect(ativo(rota)).toEqual(esperado)
  })

  it('alterna o idioma da interface entre EN-US e PT-BR', () => {
    renderizar()
    expect(screen.getByRole('button', { name: 'EN-US' }).getAttribute('aria-pressed')).toBe('true')

    fireEvent.click(screen.getByRole('button', { name: 'PT-BR' }))

    expect(screen.getByRole('link', { name: 'Contas a Pagar' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Copiloto de IA' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'PT-BR' }).getAttribute('aria-pressed')).toBe('true')
    expect(document.documentElement.lang).toBe('pt-BR')
    expect(localStorage.getItem('ap-copilot.language')).toBe('pt-BR')

    fireEvent.click(screen.getByRole('button', { name: 'EN-US' }))

    expect(screen.getByRole('link', { name: 'Accounts Payable' })).toBeTruthy()
    expect(document.documentElement.lang).toBe('en-US')
  })
})
