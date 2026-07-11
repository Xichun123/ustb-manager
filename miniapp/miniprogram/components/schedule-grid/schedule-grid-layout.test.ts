import { describe, expect, it } from 'vitest'

import { coveredPeriodIndexes } from './schedule-grid-layout'

describe('coveredPeriodIndexes', () => {
  it('places a 9-12 period course in both V and VI rows', () => {
    expect(coveredPeriodIndexes(9, 12)).toEqual([4, 5])
  })

  it('keeps a 9-10 period course only in the V row', () => {
    expect(coveredPeriodIndexes(9, 10)).toEqual([4])
  })
})
