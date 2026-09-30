import { describe, expect, it } from 'vitest'
import { encryptPlan, readPlanFile, samplePlan, upgrade } from '../planFile'
import type { Plan } from '../types'

const asFile = (content: unknown, name = 'client-plan.json') => new File([JSON.stringify(content)], name)

describe('plan files', () => {
  it('opens a plain plan file', async () => {
    const plan = samplePlan()
    const parsed = await readPlanFile(asFile(plan))
    expect(parsed.kind).toBe('plan')
    if (parsed.kind === 'plan') expect(parsed.plan).toEqual(plan)
  })

  it('round-trips a password-protected file', async () => {
    const plan = samplePlan()
    const encrypted = await encryptPlan(plan, 'correct horse battery')
    expect(JSON.stringify(encrypted)).not.toContain('Sample Client')
    const parsed = await readPlanFile(asFile(encrypted))
    expect(parsed.kind).toBe('locked')
    if (parsed.kind !== 'locked') return
    await expect(parsed.open('wrong password')).rejects.toThrow('Wrong password.')
    expect(await parsed.open('correct horse battery')).toEqual(plan)
  })

  it('upgrades a version 1 file with defaults', () => {
    const v1 = {
      version: 1,
      client: { name: 'Old', date_of_birth: '1980-01-01', state: '', retirement_age: 65, life_expectancy: 90 },
      income: { annual_income: 50000, annual_raise: 0.03 },
      spending: { current_annual: 30000, retirement_annual: 30000, inflation: 0.025 },
      accounts: [{ id: 'a', name: 'IRA', type: 'traditional', balance: 1, annual_contribution: 0, contribution_start_year: null, contribution_stop_year: null, expected_return: 0.07 }],
    } as unknown as Plan
    const plan = upgrade(v1)
    expect(plan.version).toBe(4)
    expect(plan.client.filing_status).toBe('single')
    expect(plan.accounts[0].holdings).toEqual([])
    expect(plan.goals).toEqual([])
    expect(plan.roth_conversion).toBeNull()
  })

  it('rejects files that are not plans or are too new', async () => {
    await expect(readPlanFile(new File(['not json'], 'x.json'))).rejects.toThrow('not JSON')
    await expect(readPlanFile(asFile({ hello: 1 }))).rejects.toThrow('not a plan file')
    await expect(readPlanFile(asFile({ ...samplePlan(), version: 99 }))).rejects.toThrow('newer version')
  })
})
