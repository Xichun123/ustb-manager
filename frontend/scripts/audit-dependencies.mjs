import { spawnSync } from 'node:child_process'

const allowedAdvisories = new Map([
  [
    'https://github.com/advisories/GHSA-qwww-vcr4-c8h2',
    'React Router RSC/Server Action advisory; this app only uses client-side BrowserRouter',
  ],
])

const audit = spawnSync('npm', ['audit', '--json', '--audit-level=high'], {
  encoding: 'utf8',
})

let report
try {
  report = JSON.parse(audit.stdout)
} catch {
  process.stderr.write(audit.stderr || audit.stdout)
  console.error('Unable to parse npm audit output')
  process.exit(audit.status || 1)
}

const vulnerabilities = report.vulnerabilities ?? {}
const severityRank = { info: 0, low: 1, moderate: 2, high: 3, critical: 4 }
const checked = new Map()

function isAllowed(name, visiting = new Set()) {
  if (checked.has(name)) return checked.get(name)
  if (visiting.has(name)) return true

  const vulnerability = vulnerabilities[name]
  if (!vulnerability) return false

  const nextVisiting = new Set(visiting).add(name)
  const allowed = vulnerability.via.every((cause) => {
    if (typeof cause === 'string') return isAllowed(cause, nextVisiting)
    if ((severityRank[cause.severity] ?? 0) < severityRank.high) return true
    return allowedAdvisories.has(cause.url)
  })

  checked.set(name, allowed)
  return allowed
}

const unexpected = Object.entries(vulnerabilities).filter(
  ([name, vulnerability]) =>
    (severityRank[vulnerability.severity] ?? 0) >= severityRank.high &&
    !isAllowed(name),
)

if (unexpected.length > 0) {
  process.stderr.write(audit.stdout)
  console.error(
    `npm audit found unexpected high/critical vulnerabilities: ${unexpected
      .map(([name]) => name)
      .join(', ')}`,
  )
  process.exit(1)
}

const activeAllowlist = [...allowedAdvisories.entries()].filter(([url]) =>
  Object.values(vulnerabilities).some((vulnerability) =>
    vulnerability.via.some(
      (cause) => typeof cause !== 'string' && cause.url === url,
    ),
  ),
)

if (activeAllowlist.length === 0) {
  console.log('npm audit found no high or critical vulnerabilities')
} else {
  for (const [url, reason] of activeAllowlist) {
    console.warn(`Allowed advisory ${url}: ${reason}`)
  }
}
