package com.xichun.ustbmanager.data

data class StudentProfile(
    val studentId: String,
    val name: String,
    val college: String,
    val major: String,
    val className: String,
    val grade: String,
    val email: String?,
    val phone: String?,
)

data class AcademicContext(
    val year: String,
    val semester: String,
    val week: Int?,
) {
    val term: String get() = if (year.isBlank() || semester.isBlank()) "" else "$year-$semester"
}

data class Course(
    val id: String,
    val name: String,
    val teacher: String,
    val weekday: Int,
    val startPeriod: Int,
    val endPeriod: Int,
    val weeks: List<Int>,
    val weekText: String,
    val location: String,
    val campus: String,
)

data class Grade(
    val id: String,
    val taskId: String,
    val term: String,
    val courseCode: String,
    val courseName: String,
    val credit: Double,
    val score: String,
    val courseNature: String,
    val passed: Boolean?,
)

data class GradeSummary(
    val officialGpa: Double?,
    val earnedCredits: Double,
    val passedCourses: Int,
    val failedCourses: Int,
)

data class Exam(
    val id: String,
    val courseName: String,
    val examType: String,
    val date: String,
    val dateDisplay: String,
    val time: String,
    val building: String,
    val room: String,
    val seatNumber: String?,
)

data class DashboardData(
    val profile: StudentProfile,
    val context: AcademicContext,
    val courses: List<Course>,
    val grades: List<Grade>,
    val gradeSummary: GradeSummary,
    val exams: List<Exam>,
)
