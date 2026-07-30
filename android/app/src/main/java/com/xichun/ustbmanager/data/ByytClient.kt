package com.xichun.ustbmanager.data

import android.webkit.CookieManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URLEncoder
import java.net.URL

private const val BASE_URL = "https://byyt.ustb.edu.cn"

class SessionExpiredException : IOException("学校登录状态已过期")
class UpstreamException(message: String) : IOException(message)

class ByytClient(
    private val cookieManager: CookieManager = CookieManager.getInstance(),
) {
    suspend fun get(path: String, params: Map<String, String> = emptyMap()): Any? =
        request("GET", path, params = params)

    suspend fun postEmpty(path: String): Any? = request("POST", path, body = ByteArray(0))

    suspend fun postForm(path: String, fields: Map<String, String>): Any? = request(
        method = "POST",
        path = path,
        body = fields.entries.joinToString("&") { (key, value) ->
            "${key.urlEncode()}=${value.urlEncode()}"
        }.toByteArray(),
        contentType = "application/x-www-form-urlencoded; charset=UTF-8",
    )

    suspend fun postJson(path: String, body: JSONObject): Any? = request(
        method = "POST",
        path = path,
        body = body.toString().toByteArray(),
        contentType = "application/json; charset=UTF-8",
    )

    private suspend fun request(
        method: String,
        path: String,
        params: Map<String, String> = emptyMap(),
        body: ByteArray? = null,
        contentType: String? = null,
    ): Any? = withContext(Dispatchers.IO) {
        val query = params.entries.joinToString("&") { (key, value) ->
            "${key.urlEncode()}=${value.urlEncode()}"
        }
        val requestUrl = "$BASE_URL/${path.trimStart('/')}${if (query.isEmpty()) "" else "?$query"}"
        val connection = (URL(requestUrl).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            instanceFollowRedirects = false
            connectTimeout = 15_000
            readTimeout = 30_000
            setRequestProperty("Accept", "application/json, text/plain, */*")
            setRequestProperty("X-Requested-With", "XMLHttpRequest")
            cookieManager.getCookie(BASE_URL)?.takeIf { it.isNotBlank() }?.let {
                setRequestProperty("Cookie", it)
            }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", contentType ?: "application/octet-stream")
            }
        }

        try {
            body?.let { connection.outputStream.use { output -> output.write(it) } }
            val status = connection.responseCode
            connection.headerFields["Set-Cookie"].orEmpty().forEach { cookie ->
                cookieManager.setCookie(BASE_URL, cookie)
            }
            cookieManager.flush()

            val location = connection.getHeaderField("Location").orEmpty()
            if (status == HttpURLConnection.HTTP_UNAUTHORIZED ||
                (status in 300..399 && location.contains("authentication", ignoreCase = true))
            ) {
                throw SessionExpiredException()
            }
            if (status in 300..399) {
                val host = runCatching { URI(location).host.orEmpty() }.getOrDefault("")
                if (host.contains("sso.ustb.edu.cn") || host.isBlank()) throw SessionExpiredException()
                throw UpstreamException("学校系统返回了意外跳转")
            }

            val stream = if (status >= 400) connection.errorStream else connection.inputStream
            val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (status >= 500) throw UpstreamException("学校系统暂时不可用（$status）")
            if (status >= 400) throw UpstreamException("学校系统请求失败（$status）")
            if (text.isBlank()) return@withContext null
            if (text.trimStart().startsWith("<")) {
                if (text.contains("统一身份认证") || text.contains("login", ignoreCase = true)) {
                    throw SessionExpiredException()
                }
                throw UpstreamException("学校系统返回了无法识别的页面")
            }

            val parsed = when (text.trimStart().firstOrNull()) {
                '{' -> JSONObject(text)
                '[' -> JSONArray(text)
                else -> throw UpstreamException("学校系统返回了无法识别的数据")
            }
            if (parsed is JSONObject && parsed.has("code") && parsed.optString("code") != "200") {
                val message = parsed.optString("msg").ifBlank {
                    parsed.optString("message").ifBlank { "学校系统返回失败结果" }
                }
                throw UpstreamException(message)
            }
            parsed
        } finally {
            connection.disconnect()
        }
    }
}

private fun String.urlEncode(): String = URLEncoder.encode(this, Charsets.UTF_8.name())

internal fun JSONObject.contentObject(): JSONObject? = when (val content = opt("content")) {
    is JSONObject -> content
    is JSONArray -> content.optJSONObject(0)
    else -> null
}

internal fun JSONObject.contentArray(): JSONArray? = optJSONArray("content")

internal fun JSONObject.text(key: String): String =
    opt(key)?.takeUnless { it == JSONObject.NULL }?.toString().orEmpty()

internal fun JSONObject.nullableText(key: String): String? = text(key).ifBlank { null }
