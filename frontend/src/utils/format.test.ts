import { describe, expect, it } from 'vitest'
import { formatCurrency, formatDate, formatDateTime } from './format'

// Intl usa espaço não separável entre "R$" e o valor.
const normalizar = (texto: string) => texto.replace(/\s/g, ' ')

describe('formatCurrency', () => {
  it('formata decimal da API como BRL', () => {
    expect(normalizar(formatCurrency('1234.56'))).toBe('R$ 1.234,56')
    expect(normalizar(formatCurrency('1000000.00'))).toBe('R$ 1.000.000,00')
    expect(normalizar(formatCurrency('0.00'))).toBe('R$ 0,00')
  })
})

describe('formatDate', () => {
  it('formata data ISO como dd/mm/yyyy sem deslocar o fuso', () => {
    expect(formatDate('2026-10-03')).toBe('03/10/2026')
    expect(formatDate('2026-01-01')).toBe('01/01/2026')
  })
})

describe('formatDateTime', () => {
  it('formata timestamp como data e hora', () => {
    expect(formatDateTime('2026-10-03T16:48:07.555327Z')).toMatch(/^\d{2}\/\d{2}\/\d{4},? \d{2}:\d{2}$/)
  })
})
