package com.xichun.ustbmanager.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.xichun.ustbmanager.data.Course
import com.xichun.ustbmanager.data.DashboardData
import com.xichun.ustbmanager.data.Exam
import com.xichun.ustbmanager.data.Grade
import java.time.LocalDate

private val pagePadding = 16.dp

@Composable
fun HomeScreen(data: DashboardData, onOpenSchedule: () -> Unit) {
    val week = data.context.week
    val todayWeekday = LocalDate.now().dayOfWeek.value
    val todayCourses = data.courses.filter { course ->
        course.weekday == todayWeekday && (week == null || course.weeks.isEmpty() || week in course.weeks)
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(pagePadding),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Text(
                text = "你好，${data.profile.name.ifBlank { data.profile.studentId }}",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = listOfNotNull(
                    data.context.term.takeIf { it.isNotBlank() },
                    week?.let { "第 $it 周" },
                ).joinToString(" · "),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                InfoCard(
                    title = "官方 GPA",
                    value = data.gradeSummary.officialGpa?.pretty() ?: "—",
                    modifier = Modifier.weight(1f),
                )
                InfoCard(
                    title = "已获学分",
                    value = data.gradeSummary.earnedCredits.pretty(),
                    modifier = Modifier.weight(1f),
                )
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                InfoCard(
                    title = "已通过课程",
                    value = data.gradeSummary.passedCourses.toString(),
                    modifier = Modifier.weight(1f),
                )
                InfoCard(
                    title = "未通过课程",
                    value = data.gradeSummary.failedCourses.toString(),
                    modifier = Modifier.weight(1f),
                )
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                SectionTitle("今日课程")
                OutlinedButton(onClick = onOpenSchedule) { Text("完整课表") }
            }
        }
        if (todayCourses.isEmpty()) {
            item { EmptyCard("今天没有课程") }
        } else {
            items(todayCourses, key = { it.id + it.startPeriod }) { CourseCard(it) }
        }
        item { SectionTitle("近期考试") }
        if (data.exams.isEmpty()) {
            item { EmptyCard("暂无考试安排") }
        } else {
            items(data.exams.take(3), key = { it.id + it.courseName }) { ExamCard(it) }
        }
    }
}

@Composable
fun ScheduleScreen(data: DashboardData) {
    val visibleCourses = data.courses.filter { course ->
        data.context.week == null || course.weeks.isEmpty() || data.context.week in course.weeks
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(pagePadding),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("本周课表", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                listOfNotNull(data.context.term, data.context.week?.let { "第 $it 周" }).joinToString(" · "),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (visibleCourses.isEmpty()) {
            item { EmptyCard("本周没有课程") }
        }
        (1..7).forEach { weekday ->
            val courses = visibleCourses.filter { it.weekday == weekday }.sortedBy { it.startPeriod }
            if (courses.isNotEmpty()) {
                item { SectionTitle(weekdayNames[weekday], Modifier.padding(top = 8.dp)) }
                items(courses, key = { it.id + it.startPeriod + weekday }) { CourseCard(it) }
            }
        }
    }
}

@Composable
fun GradesScreen(data: DashboardData) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(pagePadding),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("成绩", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "共 ${data.grades.size} 门课程",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                InfoCard(
                    "官方 GPA",
                    data.gradeSummary.officialGpa?.pretty() ?: "—",
                    modifier = Modifier.weight(1f),
                )
                InfoCard(
                    "已获学分",
                    data.gradeSummary.earnedCredits.pretty(),
                    modifier = Modifier.weight(1f),
                )
            }
        }
        if (data.grades.isEmpty()) item { EmptyCard("暂无成绩") }
        items(data.grades, key = { it.id + it.courseName }) { GradeCard(it) }
    }
}

@Composable
fun ExamsScreen(data: DashboardData) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(pagePadding),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("考试安排", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(data.context.term, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (data.exams.isEmpty()) item { EmptyCard("当前学期暂无考试安排") }
        items(data.exams, key = { it.id + it.courseName }) { ExamCard(it) }
    }
}

@Composable
fun ProfileScreen(data: DashboardData, onLogout: () -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(pagePadding),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Text("我的", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(data.profile.name, style = MaterialTheme.typography.titleLarge)
            Text(data.profile.studentId, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            Card {
                Column(Modifier.padding(16.dp)) {
                    LabelValue("学院", data.profile.college)
                    HorizontalDivider()
                    LabelValue("专业", data.profile.major)
                    HorizontalDivider()
                    LabelValue("班级", data.profile.className)
                    HorizontalDivider()
                    LabelValue("年级", data.profile.grade)
                    data.profile.email?.let {
                        HorizontalDivider()
                        LabelValue("邮箱", it)
                    }
                    data.profile.phone?.let {
                        HorizontalDivider()
                        LabelValue("手机", it)
                    }
                }
            }
        }
        item {
            Text(
                "数据直接来自北京科技大学本研一体教务系统，不经过第三方服务器。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            Button(onClick = onLogout, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                Text("退出登录")
            }
        }
    }
}

@Composable
private fun CourseCard(course: Course) {
    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(course.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "第 ${course.startPeriod}-${course.endPeriod} 节 · ${course.teacher}",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (course.location.isNotBlank()) {
                Text(listOf(course.campus, course.location).filter { it.isNotBlank() }.joinToString(" · "))
            }
            if (course.weekText.isNotBlank()) {
                Text(course.weekText, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun GradeCard(grade: Grade) {
    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(grade.courseName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text(
                    listOf(grade.term, "${grade.credit.pretty()} 学分", grade.courseNature)
                        .filter { it.isNotBlank() }.joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                grade.score.ifBlank { "—" },
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = if (grade.passed == false) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
            )
        }
    }
}

@Composable
private fun ExamCard(exam: Exam) {
    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(exam.courseName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                listOf(exam.dateDisplay.ifBlank { exam.date }, exam.time).filter { it.isNotBlank() }.joinToString(" · "),
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Medium,
            )
            Text(
                listOf(exam.building, exam.room, exam.seatNumber?.let { "$it 号座" }.orEmpty())
                    .filter { it.isNotBlank() }.joinToString(" · "),
            )
            if (exam.examType.isNotBlank()) Text(exam.examType, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun EmptyCard(text: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Text(
            text,
            modifier = Modifier.fillMaxWidth().padding(24.dp),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
