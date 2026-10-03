import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import Layout from './Layout'

function ativo(rota: string) {
  render(
    <MemoryRouter initialEntries={[rota]}>
      <Layout>conteúdo</Layout>
    </MemoryRouter>,
  )
  return {
    ap: screen.getByRole('link', { name: 'Accounts Payable' }).className.includes('bg-slate-900'),
    copilot: screen.getByRole('link', { name: 'AI Copilot' }).className.includes('bg-slate-900'),
  }
}

describe('Layout', () => {
  it.each([
    ['/', { ap: true, copilot: false }],
    ['/titulos/4', { ap: true, copilot: false }],
    ['/copilot', { ap: false, copilot: true }],
  ])('destaca a área da rota %s', (rota, esperado) => {
    expect(ativo(rota)).toEqual(esperado)
  })
})
