package com.xichun.ustbmanager.data

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SessionStoreTest {
    @Test
    fun `extracts session value without truncating padding`() {
        assertEquals(
            "opaque-value==",
            extractCookieValue("theme=dark; SESSION=opaque-value==; locale=zh", "SESSION"),
        )
    }

    @Test
    fun `cookie names are matched exactly`() {
        assertNull(extractCookieValue("MYSESSION=wrong; session=wrong", "SESSION"))
        assertNull(extractCookieValue("SESSION=", "SESSION"))
        assertNull(extractCookieValue(null, "SESSION"))
    }

    @Test
    fun `encrypted payload round trips`() {
        val iv = byteArrayOf(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
        val ciphertext = ByteArray(24) { it.toByte() }

        val unpacked = unpackEncryptedPayload(packEncryptedPayload(iv, ciphertext))

        assertArrayEquals(iv, unpacked?.iv)
        assertArrayEquals(ciphertext, unpacked?.ciphertext)
    }

    @Test
    fun `rejects malformed encrypted payloads`() {
        assertNull(unpackEncryptedPayload(byteArrayOf()))
        assertNull(unpackEncryptedPayload(byteArrayOf(2, 12) + ByteArray(28)))
        assertNull(unpackEncryptedPayload(byteArrayOf(1, 40) + ByteArray(40)))
        assertNull(unpackEncryptedPayload(byteArrayOf(1, 12) + ByteArray(12)))
    }
}
