import type { components } from './openapi'

type AcademicTerm = components['schemas']['AcademicTermOption']

const SEMESTER_NAMES: Record<string, string> = {
  '1': '第一学期',
  '2': '第二学期',
  '3': '夏季学期',
}

export function formatAcademicTermLabel(term: AcademicTerm): string {
  const semesterName = SEMESTER_NAMES[term.semester] || term.name || `第${term.semester}学期`
  return `${term.year}学年${semesterName}`
}
