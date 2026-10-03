import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import StatusBadge from './StatusBadge'

describe('StatusBadge', () => {
  it.each(['PENDENTE', 'APROVADO', 'PAGO', 'CANCELADO', 'ERRO'])('mostra o status %s', (status) => {
    render(<StatusBadge status={status} />)
    expect(screen.getByText(status)).toBeTruthy()
  })

  it('usa cores diferentes para ERRO e PAGO', () => {
    render(
      <>
        <StatusBadge status="ERRO" />
        <StatusBadge status="PAGO" />
      </>,
    )
    expect(screen.getByText('ERRO').className).toContain('red')
    expect(screen.getByText('PAGO').className).toContain('emerald')
  })
})
