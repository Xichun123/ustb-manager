package com.xichun.ustbmanager

import android.os.Build
import android.os.Bundle
import android.webkit.WebView
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.xichun.ustbmanager.ui.ExamsScreen
import com.xichun.ustbmanager.ui.GradesScreen
import com.xichun.ustbmanager.ui.HomeScreen
import com.xichun.ustbmanager.ui.LoginScreen
import com.xichun.ustbmanager.ui.ProfileScreen
import com.xichun.ustbmanager.ui.ScheduleScreen
import com.xichun.ustbmanager.ui.theme.UstbManagerTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            window.isNavigationBarContrastEnforced = false
        }
        setContent {
            UstbManagerTheme {
                UstbManagerApp()
            }
        }
    }
}

private enum class MainTab(val title: String, val icon: ImageVector) {
    Home("首页", Icons.Default.Home),
    Schedule("课表", Icons.Default.DateRange),
    Grades("成绩", Icons.Default.Star),
    Exams("考试", Icons.AutoMirrored.Filled.List),
    Profile("我的", Icons.Default.Person),
}

@Composable
private fun UstbManagerApp(viewModel: AppViewModel = viewModel()) {
    val state = viewModel.state
    when {
        state.checkingSession -> LoadingScreen()
        !state.authenticated || state.data == null -> LoginScreen(
            checkingLogin = state.loginChecking,
            error = state.error,
            onAuthenticated = viewModel::onLoginRedirect,
            onDismissError = viewModel::dismissError,
        )
        else -> AuthenticatedApp(
            state = state,
            onRefresh = { viewModel.refresh() },
            onDismissError = viewModel::dismissError,
            onLogout = viewModel::logout,
        )
    }
}

@Composable
private fun LoadingScreen() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AuthenticatedApp(
    state: AppUiState,
    onRefresh: () -> Unit,
    onDismissError: () -> Unit,
    onLogout: () -> Unit,
) {
    var selectedTab by remember { mutableStateOf(MainTab.Home) }
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(state.error) {
        state.error?.let {
            snackbarHostState.showSnackbar(it)
            onDismissError()
        }
    }
    val data = requireNotNull(state.data)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(selectedTab.title) },
                actions = {
                    IconButton(onClick = onRefresh, enabled = !state.loading) {
                        if (state.loading) {
                            CircularProgressIndicator(strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = "刷新数据")
                        }
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar {
                MainTab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = selectedTab == tab,
                        onClick = { selectedTab = tab },
                        icon = { Icon(tab.icon, contentDescription = null) },
                        label = { Text(tab.title) },
                    )
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        Box(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentAlignment = Alignment.TopCenter,
        ) {
            Box(Modifier.fillMaxSize().widthIn(max = 760.dp)) {
                when (selectedTab) {
                    MainTab.Home -> HomeScreen(data) { selectedTab = MainTab.Schedule }
                    MainTab.Schedule -> ScheduleScreen(data)
                    MainTab.Grades -> GradesScreen(data)
                    MainTab.Exams -> ExamsScreen(data)
                    MainTab.Profile -> ProfileScreen(data, onLogout)
                }
            }
        }
    }
}
