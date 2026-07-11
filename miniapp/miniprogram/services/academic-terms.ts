const SEMESTER_NAMES: Record<string, string> = {
  '1': '第一学期',
  '2': '第二学期',
  '3': '夏季学期',
}

interface AcademicTermLabelInput {
  year: string
  semester: string
  name?: string
}

export function formatAcademicTermLabel(term: AcademicTermLabelInput): string {
  const semesterName = SEMESTER_NAMES[term.semester] || term.name || `第${term.semester}学期`
  return `${term.year}学年${semesterName}`
}

export function formatAcademicTermCodeLabel(code: string, name?: string): string {
  const match = String(code || '').match(/^(.*)-(\d+)$/)
  if (!match) {
    return name || code
  }
  return formatAcademicTermLabel({ year: match[1], semester: match[2], name })
}
