package com.xichun.ustbmanager.data

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.webkit.CookieManager
import androidx.core.content.edit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlin.coroutines.resume

internal const val BYYT_BASE_URL = "https://byyt.ustb.edu.cn"
private const val SESSION_COOKIE_NAME = "SESSION"
private const val PREFERENCES_NAME = "encrypted_session"
private const val SESSION_KEY = "byyt_session"
private const val KEY_ALIAS = "ustb_manager_session_key"
private const val ANDROID_KEYSTORE = "AndroidKeyStore"
private const val CIPHER_TRANSFORMATION = "AES/GCM/NoPadding"
private const val PAYLOAD_VERSION: Byte = 1
private const val GCM_TAG_LENGTH_BITS = 128
private const val MIN_IV_LENGTH = 12
private const val MAX_IV_LENGTH = 32
private const val MIN_CIPHERTEXT_LENGTH = GCM_TAG_LENGTH_BITS / 8
private val SESSION_AAD = "com.xichun.ustbmanager:byyt-session:v1".toByteArray()

class SessionStore(
    context: Context,
    private val cookieManager: CookieManager = CookieManager.getInstance(),
) {
    private val preferences: SharedPreferences = context.applicationContext.getSharedPreferences(
        PREFERENCES_NAME,
        Context.MODE_PRIVATE,
    )

    suspend fun restoreSession(): Boolean {
        val session = withContext(Dispatchers.IO) { readStoredSession() } ?: return false
        val restored = setSessionCookie(session)
        if (restored) {
            withContext(Dispatchers.IO) { cookieManager.flush() }
        } else {
            withContext(Dispatchers.IO) { clearStoredSession() }
        }
        return restored
    }

    suspend fun saveCurrentSession(): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            val session = extractCookieValue(
                cookieManager.getCookie(BYYT_BASE_URL),
                SESSION_COOKIE_NAME,
            ) ?: return@runCatching false
            saveSession(session)
            true
        }.getOrElse {
            clearStoredSession()
            false
        }
    }

    fun saveFromSetCookie(header: String) {
        val pair = parseCookiePair(header) ?: return
        if (pair.first != SESSION_COOKIE_NAME) return
        runCatching {
            if (pair.second.isBlank() || header.split(';').drop(1).any { attribute ->
                    attribute.trim().equals("Max-Age=0", ignoreCase = true)
                }
            ) {
                clearStoredSession()
            } else {
                saveSession(pair.second)
            }
        }.onFailure {
            clearStoredSession()
        }
    }

    suspend fun clearSession() {
        withContext(Dispatchers.IO) { clearStoredSession() }
        setCookie("$SESSION_COOKIE_NAME=; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Strict")
        withContext(Dispatchers.IO) { cookieManager.flush() }
    }

    suspend fun clearAllCookies() {
        withContext(Dispatchers.IO) { clearStoredSession() }
        withContext(Dispatchers.Main.immediate) {
            suspendCancellableCoroutine { continuation ->
                cookieManager.removeAllCookies {
                    if (continuation.isActive) continuation.resume(Unit)
                }
            }
        }
        withContext(Dispatchers.IO) { cookieManager.flush() }
    }

    private suspend fun setSessionCookie(session: String): Boolean = setCookie(
        "$SESSION_COOKIE_NAME=$session; Path=/; Secure; HttpOnly; SameSite=Strict",
    )

    private suspend fun setCookie(cookie: String): Boolean = withContext(Dispatchers.Main.immediate) {
        suspendCancellableCoroutine { continuation ->
            cookieManager.setCookie(BYYT_BASE_URL, cookie) { accepted ->
                if (continuation.isActive) continuation.resume(accepted)
            }
        }
    }

    private fun saveSession(session: String) {
        val cipher = Cipher.getInstance(CIPHER_TRANSFORMATION).apply {
            init(Cipher.ENCRYPT_MODE, getOrCreateKey())
            updateAAD(SESSION_AAD)
        }
        val payload = packEncryptedPayload(cipher.iv, cipher.doFinal(session.toByteArray(Charsets.UTF_8)))
        // Synchronous persistence prevents a process killed immediately after login losing the session.
        preferences.edit(commit = true) {
            putString(SESSION_KEY, Base64.encodeToString(payload, Base64.NO_WRAP))
        }
    }

    private fun readStoredSession(): String? {
        val encoded = preferences.getString(SESSION_KEY, null) ?: return null
        return runCatching {
            val payload = unpackEncryptedPayload(Base64.decode(encoded, Base64.NO_WRAP))
                ?: error("Invalid encrypted session payload")
            val cipher = Cipher.getInstance(CIPHER_TRANSFORMATION).apply {
                init(
                    Cipher.DECRYPT_MODE,
                    getOrCreateKey(),
                    GCMParameterSpec(GCM_TAG_LENGTH_BITS, payload.iv),
                )
                updateAAD(SESSION_AAD)
            }
            String(cipher.doFinal(payload.ciphertext), Charsets.UTF_8).takeIf { it.isNotBlank() }
                ?: error("Empty session")
        }.getOrElse {
            clearStoredSession()
            null
        }
    }

    private fun clearStoredSession() {
        preferences.edit(commit = true) { remove(SESSION_KEY) }
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE).run {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setRandomizedEncryptionRequired(true)
                    .build(),
            )
            generateKey()
        }
    }
}

internal fun extractCookieValue(header: String?, name: String): String? = header
    ?.split(';')
    ?.firstNotNullOfOrNull { segment ->
        val pair = parseCookiePair(segment) ?: return@firstNotNullOfOrNull null
        pair.second.takeIf { pair.first == name && it.isNotBlank() }
    }

private fun parseCookiePair(value: String): Pair<String, String>? {
    val separator = value.indexOf('=')
    if (separator <= 0) return null
    return value.substring(0, separator).trim() to value.substring(separator + 1).trim()
}

internal data class EncryptedPayload(val iv: ByteArray, val ciphertext: ByteArray)

internal fun packEncryptedPayload(iv: ByteArray, ciphertext: ByteArray): ByteArray {
    require(iv.size in MIN_IV_LENGTH..MAX_IV_LENGTH)
    require(ciphertext.size >= MIN_CIPHERTEXT_LENGTH)
    return byteArrayOf(PAYLOAD_VERSION, iv.size.toByte()) + iv + ciphertext
}

internal fun unpackEncryptedPayload(payload: ByteArray): EncryptedPayload? {
    if (payload.size < 2 || payload[0] != PAYLOAD_VERSION) return null
    val ivLength = payload[1].toInt() and 0xff
    if (ivLength !in MIN_IV_LENGTH..MAX_IV_LENGTH) return null
    val ciphertextOffset = 2 + ivLength
    if (payload.size - ciphertextOffset < MIN_CIPHERTEXT_LENGTH) return null
    return EncryptedPayload(
        iv = payload.copyOfRange(2, ciphertextOffset),
        ciphertext = payload.copyOfRange(ciphertextOffset, payload.size),
    )
}
