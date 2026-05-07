/**
 * AES-256-GCM Encryption for API Keys
 *
 * Uses the NEXUS_ENCRYPTION_KEY env var (64-char hex = 256 bits).
 * Produces: encryptedKey (base64), iv (base64), authTag (base64)
 */

import { createCipheriv, createDecipheriv, randomBytes } from 'crypto'

const ALGORITHM = 'aes-256-gcm'
const IV_LENGTH = 12 // 96-bit IV recommended for GCM
const TAG_LENGTH = 16 // 128-bit auth tag

function getEncryptionKey(): Buffer {
  const hexKey = process.env.NEXUS_ENCRYPTION_KEY
  if (!hexKey || hexKey.length !== 64) {
    throw new Error('NEXUS_ENCRYPTION_KEY must be a 64-character hex string (256 bits)')
  }
  return Buffer.from(hexKey, 'hex')
}

export interface EncryptedData {
  encryptedKey: string // base64
  keyIv: string       // base64
  keyTag: string      // base64
}

/**
 * Encrypt a plaintext API key using AES-256-GCM.
 * Returns base64-encoded ciphertext, IV, and auth tag.
 */
export function encrypt(plaintext: string): EncryptedData {
  const key = getEncryptionKey()
  const iv = randomBytes(IV_LENGTH)

  const cipher = createCipheriv(ALGORITHM, key, iv, { authTagLength: TAG_LENGTH })
  const encrypted = Buffer.concat([
    cipher.update(plaintext, 'utf8'),
    cipher.final(),
  ])
  const authTag = cipher.getAuthTag()

  return {
    encryptedKey: encrypted.toString('base64'),
    keyIv: iv.toString('base64'),
    keyTag: authTag.toString('base64'),
  }
}

/**
 * Decrypt an encrypted API key using AES-256-GCM.
 * Takes base64-encoded ciphertext, IV, and auth tag.
 * Returns the plaintext key.
 */
export function decrypt(encryptedKey: string, keyIv: string, keyTag: string): string {
  const key = getEncryptionKey()
  const iv = Buffer.from(keyIv, 'base64')
  const authTag = Buffer.from(keyTag, 'base64')
  const encrypted = Buffer.from(encryptedKey, 'base64')

  const decipher = createDecipheriv(ALGORITHM, key, iv, { authTagLength: TAG_LENGTH })
  decipher.setAuthTag(authTag)

  const decrypted = Buffer.concat([
    decipher.update(encrypted),
    decipher.final(),
  ])

  return decrypted.toString('utf8')
}

/**
 * Mask an API key for display: show first 8 and last 4 chars.
 */
export function maskKey(key: string): string {
  if (key.length <= 12) return '***'
  return key.slice(0, 8) + '...' + key.slice(-4)
}
