package com.xichun.ustbmanager.ui

import android.annotation.SuppressLint
import androidx.core.net.toUri
import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView

private const val SSO_URL = "https://sso.ustb.edu.cn/idp/authCenter/authenticate" +
    "?client_id=YW2025006" +
    "&redirect_uri=https%3A%2F%2Fbyyt.ustb.edu.cn%2Foauth%2Flogin%2Fcode" +
    "&login_return=true&state=null&response_type=code"

private enum class LoginMode(val title: String) {
    Sms("短信验证码登录"),
    Qr("微信 / 企微扫码登录"),
}

private fun LoginMode.mobileLayoutScript(): String {
    val selectLoginMode = when (this) {
        LoginMode.Sms -> """
            if ((window.__ustbManagerLoginMode || '').startsWith('sms')) return;
            window.__ustbManagerLoginMode = 'sms-pending';
            let attempts = 0;
            const selectMode = () => {
              fillViewport();
              if (document.querySelector('.login-form')) {
                window.__ustbManagerLoginMode = 'sms';
                return true;
              }
              const toggle = document.querySelector('.content_img');
              if (toggle && document.querySelector('iframe')) {
                toggle.click();
                attempts += 1;
              }
              return attempts >= 20;
            };
        """.trimIndent()
        LoginMode.Qr -> """
            if ((window.__ustbManagerLoginMode || '').startsWith('qr')) return;
            window.__ustbManagerLoginMode = 'qr-pending';
            let attempts = 0;
            const selectMode = () => {
              fillViewport();
              if (document.querySelector('iframe')) {
                window.__ustbManagerLoginMode = 'qr';
                return true;
              }
              const toggle = document.querySelector('.content_img');
              if (toggle && document.querySelector('.login-form')) {
                toggle.click();
                attempts += 1;
              }
              return attempts >= 20;
            };
        """.trimIndent()
    }
    return """
        (() => {
          const fillViewport = () => {
            const height = `${'$'}{window.innerHeight}px`;
            const app = document.getElementById('app');
            [
              document.documentElement,
              document.body,
              app,
              app?.firstElementChild,
              document.querySelector('#app > div > .topicPreview'),
            ].filter(Boolean).forEach((element) => {
              element.style.setProperty('height', height, 'important');
              element.style.setProperty('min-height', height, 'important');
            });
          };
          window.__ustbManagerFillViewport = fillViewport;
          if (!window.__ustbManagerViewportListener) {
            window.__ustbManagerViewportListener = true;
            window.addEventListener('resize', () => window.__ustbManagerFillViewport?.());
          }
          fillViewport();
          $selectLoginMode
          if (!selectMode()) {
            const timer = setInterval(() => {
              if (selectMode()) clearInterval(timer);
            }, 500);
          }
        })()
    """.trimIndent()
}

private fun applyRequestedLoginMode(view: WebView, url: String, loginMode: LoginMode) {
    val uri = runCatching { url.toUri() }.getOrNull() ?: return
    if (uri.host == "sso.ustb.edu.cn") {
        view.evaluateJavascript(loginMode.mobileLayoutScript(), null)
    }
}

@Composable
fun LoginScreen(
    checkingLogin: Boolean,
    error: String?,
    onAuthenticated: () -> Unit,
    onDismissError: () -> Unit,
) {
    var loginMode by remember { mutableStateOf<LoginMode?>(null) }
    val activeMode = loginMode
    if (activeMode != null) {
        SchoolLoginWebView(
            loginMode = activeMode,
            checkingLogin = checkingLogin,
            onClose = { loginMode = null },
            onAuthenticated = onAuthenticated,
        )
    } else {
        LoginWelcome(
            error = error,
            onDismissError = onDismissError,
            onLogin = { loginMode = it },
        )
    }
}

@Composable
private fun LoginWelcome(
    error: String?,
    onDismissError: () -> Unit,
    onLogin: (LoginMode) -> Unit,
) {
    Box(
        modifier = Modifier.fillMaxSize().padding(horizontal = 24.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Card(
                modifier = Modifier.size(88.dp),
                shape = RoundedCornerShape(24.dp),
            ) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        text = "USTB",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Spacer(Modifier.height(24.dp))
            Text(
                text = "USTB Manager",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = "在手机上查看课表、成绩与考试安排",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(32.dp))
            Button(
                onClick = { onLogin(LoginMode.Sms) },
                modifier = Modifier.fillMaxWidth().height(52.dp),
                contentPadding = PaddingValues(horizontal = 24.dp),
            ) {
                Text("短信验证码登录")
            }
            Spacer(Modifier.height(8.dp))
            androidx.compose.material3.OutlinedButton(
                onClick = { onLogin(LoginMode.Qr) },
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                Text("微信 / 企微扫码登录")
            }
            Spacer(Modifier.height(12.dp))
            Text(
                text = "以上认证均由学校统一身份认证系统完成。手机号、验证码与扫码结果仅提交给学校。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
            if (error != null) {
                Spacer(Modifier.height(20.dp))
                Card(onClick = onDismissError, modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = error,
                        modifier = Modifier.padding(16.dp),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SchoolLoginWebView(
    loginMode: LoginMode,
    checkingLogin: Boolean,
    onClose: () -> Unit,
    onAuthenticated: () -> Unit,
) {
    val context = LocalContext.current
    var webView by remember { mutableStateOf<WebView?>(null) }
    BackHandler {
        if (webView?.canGoBack() == true) webView?.goBack() else onClose()
    }
    DisposableEffect(Unit) {
        onDispose {
            webView?.stopLoading()
            webView?.destroy()
            webView = null
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(loginMode.title) },
                navigationIcon = {
                    IconButton(onClick = onClose) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "关闭登录")
                    }
                },
            )
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = {
                    WebView(context).apply webViewSetup@{
                        webView = this
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = true
                        settings.allowFileAccess = false
                        settings.allowContentAccess = false
                        settings.setSupportMultipleWindows(false)
                        CookieManager.getInstance().apply {
                            setAcceptCookie(true)
                            setAcceptThirdPartyCookies(this@webViewSetup, true)
                        }
                        webViewClient = object : WebViewClient() {
                            override fun shouldOverrideUrlLoading(
                                view: WebView,
                                request: WebResourceRequest,
                            ): Boolean = request.url.scheme !in setOf("http", "https")

                            override fun onPageCommitVisible(view: WebView, url: String) {
                                applyRequestedLoginMode(view, url, loginMode)
                            }

                            override fun doUpdateVisitedHistory(
                                view: WebView,
                                url: String,
                                isReload: Boolean,
                            ) {
                                applyRequestedLoginMode(view, url, loginMode)
                            }

                            override fun onPageFinished(view: WebView, url: String) {
                                applyRequestedLoginMode(view, url, loginMode)
                                // Older Android System WebView versions may replace the H5 document
                                // after this callback while mounting the hash-routed SSO app.
                                view.postDelayed(
                                    { view.url?.let { applyRequestedLoginMode(view, it, loginMode) } },
                                    800,
                                )
                                val uri = runCatching { url.toUri() }.getOrNull() ?: return
                                if (uri.host == "byyt.ustb.edu.cn" &&
                                    !uri.path.orEmpty().contains("/oauth/login/code")
                                ) {
                                    CookieManager.getInstance().flush()
                                    onAuthenticated()
                                }
                            }
                        }
                        loadUrl(SSO_URL)
                    }
                },
            )
            if (checkingLogin) {
                Card(modifier = Modifier.align(Alignment.Center)) {
                    Column(
                        modifier = Modifier.padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        CircularProgressIndicator()
                        Text("正在确认登录状态…")
                    }
                }
            }
        }
    }
}
