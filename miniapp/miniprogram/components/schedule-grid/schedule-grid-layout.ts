export function coveredPeriodIndexes(startPeriod: number, endPeriod: number): number[] {
  const startIdx = Math.floor((startPeriod - 1) / 2)
  const endIdx = Math.floor((Math.max(startPeriod, endPeriod) - 1) / 2)
  const indexes: number[] = []

  for (let periodIdx = startIdx; periodIdx <= endIdx; periodIdx += 1) {
    if (periodIdx >= 0 && periodIdx < 6) {
      indexes.push(periodIdx)
    }
  }

  return indexes
}
