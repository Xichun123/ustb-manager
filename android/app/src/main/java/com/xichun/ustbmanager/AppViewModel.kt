package com.xichun.ustbmanager

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.xichun.ustbmanager.data.ByytClient
import com.xichun.ustbmanager.data.ByytRepository
import com.xichun.ustbmanager.data.DashboardData
import com.xichun.ustbmanager.data.SessionExpiredException
import com.xichun.ustbmanager.data.SessionStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

data class AppUiState(
    val checkingSession: Boolean = true,
    val authenticated: Boolean = false,
    val loading: Boolean = false,
    val loginChecking: Boolean = false,
    val data: DashboardData? = null,
    val error: String? = null,
)

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val sessionStore = SessionStore(application)
    private val repository = ByytRepository(ByytClient(sessionStore = sessionStore))

    var state by mutableStateOf(AppUiState())
        private set

    init {
        refresh(initial = true)
    }

    fun onLoginRedirect() {
        if (state.loginChecking || state.authenticated) return
        state = state.copy(loginChecking = true, error = null)
        viewModelScope.launch {
            try {
                val data = loadAndPersistDashboard()
                state = AppUiState(
                    checkingSession = false,
                    authenticated = true,
                    data = data,
                )
            } catch (error: Throwable) {
                if (error is CancellationException) throw error
                if (error is SessionExpiredException) sessionStore.clearSession()
                state = state.copy(
                    loginChecking = false,
                    error = error.userMessage("登录尚未完成，请在学校页面完成认证"),
                )
            }
        }
    }

    fun refresh(initial: Boolean = false) {
        if (state.loading) return
        state = state.copy(
            checkingSession = initial,
            loading = !initial,
            error = null,
        )
        viewModelScope.launch {
            try {
                if (initial) sessionStore.restoreSession()
                val data = loadAndPersistDashboard()
                state = AppUiState(
                    checkingSession = false,
                    authenticated = true,
                    data = data,
                )
            } catch (error: Throwable) {
                if (error is CancellationException) throw error
                state = if (error is SessionExpiredException) {
                    sessionStore.clearSession()
                    AppUiState(checkingSession = false, authenticated = false)
                } else {
                    state.copy(
                        checkingSession = false,
                        loading = false,
                        error = error.userMessage("加载失败，请稍后重试"),
                    )
                }
            }
        }
    }

    fun dismissError() {
        state = state.copy(error = null)
    }

    fun logout() {
        viewModelScope.launch {
            try {
                sessionStore.clearAllCookies()
            } finally {
                state = AppUiState(checkingSession = false, authenticated = false)
            }
        }
    }

    private suspend fun loadAndPersistDashboard(): DashboardData {
        val data = repository.loadDashboard()
        sessionStore.saveCurrentSession()
        return data
    }
}

private fun Throwable.userMessage(fallback: String): String =
    message?.takeIf { it.isNotBlank() } ?: fallback
