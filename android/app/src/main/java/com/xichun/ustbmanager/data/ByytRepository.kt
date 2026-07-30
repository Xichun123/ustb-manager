package com.xichun.ustbmanager.data

import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate

class ByytRepository(private val client: ByytClient = ByytClient()) {
    suspend fun loadDashboard(): DashboardData {
        val profile = getProfile()
        val context = getAcademicContext()
        val courses = getSchedule(context)
        val grades = getGrades()
        val summary = getGradeSummary(grades)
        val exams = getExams(context)
        return DashboardData(profile, context, courses, grades, summary, exams)
    }

    suspend fun validateSession(): StudentProfile = getProfile()

    suspend fun getProfile(): StudentProfile {
        val studentResponse = client.postEmpty("/UserManager/queryxsxx") as? JSONObject
            ?: throw UpstreamException("无法读取学生信息")
        val student = studentResponse.contentObject() ?: studentResponse
        val user = client.postEmpty("/user/me") as? JSONObject ?: JSONObject()
        val studentId = student.text("XH").ifBlank { user.text("userId") }
        if (studentId.isBlank()) throw SessionExpiredException()
        return StudentProfile(
            studentId = studentId,
            name = student.text("XM").ifBlank { user.text("xm") },
            college = student.text("YXMC").ifBlank { user.text("bmmc") },
            major = student.text("ZYMC"),
            className = student.text("BJMC"),
            grade = student.text("NJMC"),
            email = student.nullableText("DZYX"),
            phone = student.nullableText("LXDH"),
        )
    }

    suspend fun getAcademicContext(date: LocalDate = LocalDate.now()): AcademicContext {
        val dated = client.get("/component/getXnxqByRq", mapOf("rq" to date.toString())) as? JSONObject
        val teaching = dated?.contentObject()?.optJSONObject("rqxnxq")
        if (teaching != null && teaching.text("xn").isNotBlank()) {
            return AcademicContext(
                year = teaching.text("xn"),
                semester = teaching.text("xq"),
                week = teaching.text("zc").toIntOrNull(),
            )
        }
        val current = client.postEmpty("/component/querydangqianxnxq") as? JSONObject
            ?: throw UpstreamException("无法读取当前学期")
        return AcademicContext(
            year = current.text("XN"),
            semester = current.text("XQ"),
            week = null,
        )
    }

    suspend fun getSchedule(context: AcademicContext): List<Course> {
        val response = client.postForm(
            "/Xskbcx/queryXskbcxList",
            mapOf(
                "sfmrdqxq" to "true",
                "xn" to context.year,
                "xq" to context.semester,
                "bs" to "2",
                "xskb" to "1",
                "bjkb" to "0",
                "gwckb" to "0",
                "tabs" to "1",
                "sfxsgwc" to "1",
                "sxbj" to "",
            ),
        ) as? JSONArray ?: return emptyList()

        val unique = linkedMapOf<String, Course>()
        response.objects().mapNotNull(::parseCourse).forEach { course ->
            val key = listOf(
                course.name,
                course.teacher,
                course.weekday,
                course.startPeriod,
                course.endPeriod,
                course.weekText,
                course.location,
            ).joinToString("|")
            unique[key] = course
        }
        return unique.values.toList()
    }

    suspend fun getGrades(): List<Grade> {
        val response = client.postJson(
            "/cjgl/grcjcx/grcjcx",
            JSONObject().apply {
                put("xn", JSONObject.NULL)
                put("xq", JSONObject.NULL)
                put("kcmc", JSONObject.NULL)
                put("cxbj", "-1")
                put("pylx", "1")
                put("current", 1)
                put("pageSize", 1000)
                put("xscjlb", JSONObject.NULL)
                put("sffx", JSONObject.NULL)
                put("yhdm", "")
            },
        ) as? JSONObject ?: return emptyList()
        val list = response.contentObject()?.optJSONArray("list") ?: return emptyList()
        return list.objects().map { item ->
            val score = item.text("xscj")
            Grade(
                id = item.text("id"),
                taskId = item.text("rwid"),
                term = normalizeTerm(item.text("xnxq").ifBlank { item.text("xnxqmc") }),
                courseCode = item.text("kcdm"),
                courseName = item.text("kcmc"),
                credit = item.text("xf").toDoubleOrNull() ?: 0.0,
                score = score,
                courseNature = item.text("kcxz"),
                passed = when (item.text("sfjg")) {
                    "1" -> true
                    "0" -> false
                    else -> score.toDoubleOrNull()?.let { it >= 60.0 }
                },
            )
        }
    }

    suspend fun getGradeSummary(grades: List<Grade>): GradeSummary {
        val officialResponse = client.postEmpty("/cjgl/grcjcx/getgpa") as? JSONObject
            ?: JSONObject()
        val official = officialResponse.contentObject() ?: officialResponse
        val officialCredits = official.text("HDXF").toDoubleOrNull()
        val officialPassed = official.text("TGKC").toIntOrNull()
        return GradeSummary(
            officialGpa = official.text("GPA").toDoubleOrNull(),
            earnedCredits = officialCredits ?: grades.filter { it.passed == true }.sumOf { it.credit },
            passedCourses = officialPassed ?: grades.count { it.passed == true },
            failedCourses = grades.count { it.passed == false },
        )
    }

    suspend fun getExams(context: AcademicContext): List<Exam> {
        val response = client.postForm(
            "/kscxtj/queryXsksByxhList",
            mapOf(
                "ppylx" to "1",
                "pxn" to context.year,
                "pxq" to context.semester,
                "pkssjdm" to "",
                "pkkyx" to "",
                "pageNum" to "1",
                "pageSize" to "100",
            ),
        ) as? JSONObject ?: return emptyList()
        return response.optJSONArray("list")?.objects()?.map { item ->
            Exam(
                id = item.text("ROW_ID").ifBlank { item.text("KSHKID") },
                courseName = item.text("KCMC"),
                examType = item.text("KSSJDMC"),
                date = item.text("KSRQ"),
                dateDisplay = item.text("KSRQ2"),
                time = item.text("KSJTSJ"),
                building = item.text("JXLMC"),
                room = item.text("CDMC").ifBlank { item.text("JXCDMC") },
                seatNumber = item.nullableText("ZWH"),
            )
        }.orEmpty()
    }
}

private fun normalizeTerm(value: String): String {
    val match = Regex("^(\\d{4}-\\d{4})-?([123])$").matchEntire(value) ?: return value
    return "${match.groupValues[1]}-${match.groupValues[2]}"
}

internal fun parseCourse(item: JSONObject): Course? {
    val lines = item.text("kbxx").lines()
    val key = item.text("key")
    val weekday = Regex("xq([1-7])_jc\\d+").find(key)?.groupValues?.get(1)?.toIntOrNull()
        ?: return null
    val startPeriod = item.text("ksjc").toIntOrNull() ?: return null
    val endPeriod = item.text("jsjc").toIntOrNull() ?: return null
    val name = lines.getOrNull(0).orEmpty()
    if (name.isBlank()) return null
    val locationText = lines.getOrNull(3).orEmpty()
    val locationMatch = Regex("^【([^】]+)】(.*)$").find(locationText)
    return Course(
        id = item.text("id").ifBlank { "$key:$name" },
        name = name,
        teacher = lines.getOrNull(1).orEmpty(),
        weekday = weekday,
        startPeriod = startPeriod,
        endPeriod = endPeriod,
        weeks = parseWeeks(lines.getOrNull(2).orEmpty()),
        weekText = lines.getOrNull(2).orEmpty(),
        campus = locationMatch?.groupValues?.get(1).orEmpty(),
        location = locationMatch?.groupValues?.get(2) ?: locationText,
    )
}

internal fun parseWeeks(text: String): List<Int> {
    val oddOnly = "单" in text
    val evenOnly = "双" in text
    val weeks = mutableSetOf<Int>()
    Regex("(\\d+)\\s*-\\s*(\\d+)|(\\d+)").findAll(text).forEach { match ->
        val single = match.groups[3]?.value?.toIntOrNull()
        if (single != null) {
            weeks += single
        } else {
            val start = match.groups[1]?.value?.toIntOrNull() ?: return@forEach
            val end = match.groups[2]?.value?.toIntOrNull() ?: return@forEach
            weeks += start..end
        }
    }
    return weeks.filter { (!oddOnly || it % 2 == 1) && (!evenOnly || it % 2 == 0) }.sorted()
}

private fun JSONArray.objects(): List<JSONObject> = buildList {
    for (index in 0 until length()) optJSONObject(index)?.let(::add)
}
