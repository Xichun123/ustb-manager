package com.xichun.ustbmanager.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.math.RoundingMode
import java.text.DecimalFormat

@Composable
internal fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        modifier = modifier,
    )
}

@Composable
internal fun InfoCard(
    title: String,
    value: String,
    modifier: Modifier = Modifier,
    supporting: String? = null,
) {
    Card(modifier = modifier) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(title, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            supporting?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
        }
    }
}

@Composable
internal fun LabelValue(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value.ifBlank { "—" }, fontWeight = FontWeight.Medium)
    }
}

internal fun Double.pretty(): String = DecimalFormat("0.##").apply {
    roundingMode = RoundingMode.HALF_UP
}.format(this)

internal val weekdayNames = listOf("", "周一", "周二", "周三", "周四", "周五", "周六", "周日")
