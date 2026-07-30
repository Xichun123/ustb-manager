package com.xichun.ustbmanager.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Navy = Color(0xFF1E3A5F)
private val Blue = Color(0xFF2563EB)
private val Gold = Color(0xFFA16207)
private val LightBackground = Color(0xFFF8FAFC)
private val DarkBackground = Color(0xFF0F172A)

private val LightColors = lightColorScheme(
    primary = Navy,
    onPrimary = Color.White,
    secondary = Blue,
    tertiary = Gold,
    background = LightBackground,
    onBackground = Color(0xFF0F172A),
    surface = Color.White,
    onSurface = Color(0xFF0F172A),
    surfaceVariant = Color(0xFFE9EEF5),
    outline = Color(0xFF64748B),
    error = Color(0xFFB91C1C),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF9EC5FF),
    onPrimary = Color(0xFF052A52),
    secondary = Color(0xFFAAC7FF),
    tertiary = Color(0xFFF3C36B),
    background = DarkBackground,
    onBackground = Color(0xFFF1F5F9),
    surface = Color(0xFF172033),
    onSurface = Color(0xFFF1F5F9),
    surfaceVariant = Color(0xFF273449),
    outline = Color(0xFF94A3B8),
    error = Color(0xFFFFB4AB),
)

@Composable
fun UstbManagerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        content = content,
    )
}
