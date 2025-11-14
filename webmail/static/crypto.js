/**
 * Privra Mail - Client-Side Encryption Utilities
 * Uses WebCrypto API for RSA-OAEP encryption/decryption
 */

const PrivraCrypto = {
    /**
     * Import a PEM-encoded RSA public key
     * @param {string} pemKey - PEM formatted public key
     * @returns {Promise<CryptoKey>}
     */
    async importPublicKey(pemKey) {
        // Remove PEM headers and whitespace
        const pemContents = pemKey
            .replace('-----BEGIN PUBLIC KEY-----', '')
            .replace('-----END PUBLIC KEY-----', '')
            .replace(/\s/g, '');

        // Base64 decode
        const binaryDer = atob(pemContents);
        const bytes = new Uint8Array(binaryDer.length);
        for (let i = 0; i < binaryDer.length; i++) {
            bytes[i] = binaryDer.charCodeAt(i);
        }

        // Import as CryptoKey
        return await crypto.subtle.importKey(
            'spki',
            bytes.buffer,
            {
                name: 'RSA-OAEP',
                hash: 'SHA-256'
            },
            true,
            ['encrypt']
        );
    },

    /**
     * Import a PEM-encoded RSA private key
     * @param {string} pemKey - PEM formatted private key
     * @returns {Promise<CryptoKey>}
     */
    async importPrivateKey(pemKey) {
        // Remove PEM headers and whitespace
        const pemContents = pemKey
            .replace('-----BEGIN PRIVATE KEY-----', '')
            .replace('-----END PRIVATE KEY-----', '')
            .replace(/\s/g, '');

        // Base64 decode
        const binaryDer = atob(pemContents);
        const bytes = new Uint8Array(binaryDer.length);
        for (let i = 0; i < binaryDer.length; i++) {
            bytes[i] = binaryDer.charCodeAt(i);
        }

        // Import as CryptoKey
        return await crypto.subtle.importKey(
            'pkcs8',
            bytes.buffer,
            {
                name: 'RSA-OAEP',
                hash: 'SHA-256'
            },
            true,
            ['decrypt']
        );
    },

    /**
     * Encrypt text with recipient's public key
     * @param {string} text - Plain text to encrypt
     * @param {CryptoKey} publicKey - Recipient's public key
     * @returns {Promise<string>} - Base64 encoded encrypted data
     */
    async encryptText(text, publicKey) {
        const encoder = new TextEncoder();
        const data = encoder.encode(text);

        const encrypted = await crypto.subtle.encrypt(
            {
                name: 'RSA-OAEP'
            },
            publicKey,
            data
        );

        // Convert to base64
        return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
    },

    /**
     * Decrypt text with own private key
     * @param {string} encryptedBase64 - Base64 encoded encrypted data
     * @param {CryptoKey} privateKey - Own private key
     * @returns {Promise<string>} - Decrypted plain text
     */
    async decryptText(encryptedBase64, privateKey) {
        // Decode base64
        const binaryString = atob(encryptedBase64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        const decrypted = await crypto.subtle.decrypt(
            {
                name: 'RSA-OAEP'
            },
            privateKey,
            bytes.buffer
        );

        const decoder = new TextDecoder();
        return decoder.decode(decrypted);
    },

    /**
     * Look up recipient's public key from server
     * @param {string} email - Recipient's email address
     * @returns {Promise<object>} - {email, public_key, is_privra, encrypted}
     */
    async lookupPublicKey(email) {
        const response = await fetch(`/api/pubkey/${encodeURIComponent(email)}`);
        if (response.ok) {
            return await response.json();
        } else if (response.status === 404) {
            // External user
            return {
                email: email,
                is_privra: false,
                encrypted: false
            };
        } else {
            throw new Error('Failed to lookup public key');
        }
    },

    /**
     * Check if email should be encrypted
     * @param {string} recipientEmail - Recipient's email
     * @returns {Promise<{shouldEncrypt: boolean, publicKey: CryptoKey|null, info: object}>}
     */
    async checkEncryptionStatus(recipientEmail) {
        try {
            const keyInfo = await this.lookupPublicKey(recipientEmail);

            if (keyInfo.is_privra && keyInfo.encrypted && keyInfo.public_key) {
                // Privra user with encryption - import their public key
                const publicKey = await this.importPublicKey(keyInfo.public_key);
                return {
                    shouldEncrypt: true,
                    publicKey: publicKey,
                    info: keyInfo
                };
            } else {
                // External user or Privra user without encryption
                return {
                    shouldEncrypt: false,
                    publicKey: null,
                    info: keyInfo
                };
            }
        } catch (error) {
            console.error('Error checking encryption status:', error);
            return {
                shouldEncrypt: false,
                publicKey: null,
                info: {error: error.message}
            };
        }
    }
};

// Make available globally
window.PrivraCrypto = PrivraCrypto;
