# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5.2: Token Encryption Utilities
# Secure token storage using Windows DPAPI with Fernet fallback

"""
Token Encryption Utilities

Primary: Uses Windows DPAPI (Data Protection API) for secure token storage.
Fallback: Uses Fernet symmetric encryption if DPAPI unavailable.

DPAPI tokens are encrypted per-user and cannot be decrypted by other users.
Fernet tokens use a machine-specific key stored in settings (less secure).

All encrypted tokens are base64-encoded for safe JSON storage.
"""

import base64
import logging
import os
import sys

logger = logging.getLogger("FishingMacro")

# Try to import Windows DPAPI (pywin32)
DPAPI_AVAILABLE = False
try:
    import win32crypt

    DPAPI_AVAILABLE = True
    logger.info("✅ Windows DPAPI available (pywin32)")
except ImportError:
    logger.warning("⚠️ Windows DPAPI (pywin32) not available, using Fernet fallback")

# Fernet fallback (cryptography package)
FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet

    FERNET_AVAILABLE = True
except ImportError:
    logger.error("❌ cryptography package not installed - encryption unavailable!")


def _get_or_create_fernet_key():
    """
    Get or create a Fernet encryption key for fallback mode.

    WARNING: This is less secure than DPAPI because the key is stored in plaintext.
    The key is stored in the user's home directory (~/.bps_fishing_key).

    Returns:
        Fernet: Fernet cipher instance
    """
    key_file = os.path.join(os.path.expanduser("~"), ".bps_fishing_key")

    if os.path.exists(key_file):
        # Load existing key
        with open(key_file, "rb") as f:
            key = f.read()
        logger.debug("Loaded existing Fernet key")
    else:
        # Generate new key
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        logger.info(f"Generated new Fernet key: {key_file}")

    return Fernet(key)


def encrypt_token(token: str) -> str:
    """
    Encrypt a token using Windows DPAPI or Fernet fallback.

    The encrypted token is base64-encoded for storage in JSON.

    DPAPI mode: Only the current Windows user can decrypt it.
    Fernet mode: Anyone with access to ~/.bps_fishing_key can decrypt it.

    Args:
        token: Plain text token to encrypt

    Returns:
        Base64-encoded encrypted token (prefixed with "DPAPI:" or "FERNET:")

    Raises:
        RuntimeError: If no encryption method is available
        Exception: If encryption fails
    """
    if not token:
        return ""

    try:
        if DPAPI_AVAILABLE:
            # Windows DPAPI encryption (most secure)
            encrypted_bytes = win32crypt.CryptProtectData(
                token.encode("utf-8"),
                None,  # Optional description
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                0,  # Flags
            )
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode("utf-8")
            logger.debug("Token encrypted with DPAPI")
            return f"DPAPI:{encrypted_b64}"

        elif FERNET_AVAILABLE:
            # Fernet fallback (less secure - key stored in plaintext)
            fernet = _get_or_create_fernet_key()
            encrypted_bytes = fernet.encrypt(token.encode("utf-8"))
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode("utf-8")
            logger.warning(
                "Token encrypted with Fernet (LESS SECURE - key stored in plaintext)"
            )
            return f"FERNET:{encrypted_b64}"

        else:
            raise RuntimeError(
                "No encryption method available! Install 'pywin32' (Windows DPAPI) "
                "or 'cryptography' (Fernet fallback)."
            )

    except Exception as e:
        logger.error(f"Token encryption failed: {e}")
        raise


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a token using Windows DPAPI or Fernet.

    Automatically detects encryption method from prefix (DPAPI: or FERNET:).

    Args:
        encrypted_token: Prefixed base64-encoded encrypted token

    Returns:
        Decrypted plain text token

    Raises:
        ValueError: If token format is invalid
        RuntimeError: If decryption method is unavailable
        Exception: If decryption fails (wrong user, corrupted data, etc.)
    """
    if not encrypted_token:
        return ""

    try:
        # Detect encryption method from prefix
        if encrypted_token.startswith("DPAPI:"):
            if not DPAPI_AVAILABLE:
                raise RuntimeError("Cannot decrypt DPAPI token - pywin32 not installed")

            # Remove prefix and decode
            encrypted_b64 = encrypted_token[6:]  # Skip "DPAPI:"
            encrypted_bytes = base64.b64decode(encrypted_b64.encode("utf-8"))

            # DPAPI decryption
            _, decrypted_bytes = win32crypt.CryptUnprotectData(
                encrypted_bytes,
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                0,  # Flags
            )
            logger.debug("Token decrypted with DPAPI")
            return decrypted_bytes.decode("utf-8")

        elif encrypted_token.startswith("FERNET:"):
            if not FERNET_AVAILABLE:
                raise RuntimeError(
                    "Cannot decrypt Fernet token - cryptography not installed"
                )

            # Remove prefix and decode
            encrypted_b64 = encrypted_token[7:]  # Skip "FERNET:"
            encrypted_bytes = base64.b64decode(encrypted_b64.encode("utf-8"))

            # Fernet decryption
            fernet = _get_or_create_fernet_key()
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            logger.debug("Token decrypted with Fernet")
            return decrypted_bytes.decode("utf-8")

        else:
            raise ValueError(
                f"Invalid encrypted token format (missing DPAPI: or FERNET: prefix). "
                f"Got: {encrypted_token[:20]}..."
            )

    except Exception as e:
        logger.error(f"Token decryption failed: {e}")
        raise


def delete_token(name: str):
    """
    Delete a stored token (for future use with Windows Credential Manager).

    Currently a placeholder - tokens are stored in JSON settings file.
    Future enhancement: Store in Windows Credential Manager for better security.

    Args:
        name: Token name (e.g., "discord_bot_token")
    """
    logger.warning(f"delete_token('{name}') - Not implemented (tokens stored in JSON)")
    # TODO: Future enhancement - integrate with Windows Credential Manager
    # import win32cred
    # win32cred.CredDelete(Target=name, Type=win32cred.CRED_TYPE_GENERIC)


# ============================================================================
# MANUAL TEST SUITE (Run with: python -m utils.token_encryption)
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("BPS Fishing Macro - Token Encryption Test Suite")
    print("=" * 70)
    print()

    # Test 1: Check available encryption methods
    print("1️⃣ Available Encryption Methods:")
    print(
        f"   - Windows DPAPI (pywin32): {'✅ Available' if DPAPI_AVAILABLE else '❌ Not available'}"
    )
    print(
        f"   - Fernet fallback (cryptography): {'✅ Available' if FERNET_AVAILABLE else '❌ Not available'}"
    )
    print()

    if not DPAPI_AVAILABLE and not FERNET_AVAILABLE:
        print("❌ ERROR: No encryption method available!")
        print("   Install: pip install pywin32 cryptography")
        sys.exit(1)

    # Test 2: Encrypt/Decrypt roundtrip
    print("2️⃣ Encrypt/Decrypt Roundtrip Test:")
    test_tokens = [
        "my_super_secret_discord_bot_token_123456789",
        "short",
        "token with spaces and special chars!@#$%",
        "",  # Empty token
    ]

    for i, original_token in enumerate(test_tokens, 1):
        print(f"\n   Test {i}: {repr(original_token)}")

        try:
            # Encrypt
            encrypted = encrypt_token(original_token)
            print(
                f"   ✅ Encrypted: {encrypted[:50]}..."
                if len(encrypted) > 50
                else f"   ✅ Encrypted: {encrypted}"
            )

            # Decrypt
            decrypted = decrypt_token(encrypted)
            print(f"   ✅ Decrypted: {repr(decrypted)}")

            # Verify
            if decrypted == original_token:
                print(f"   ✅ PASS - Roundtrip successful")
            else:
                print(f"   ❌ FAIL - Mismatch!")
                print(f"      Original:  {repr(original_token)}")
                print(f"      Decrypted: {repr(decrypted)}")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    # Test 3: JSON storage compatibility
    print("\n3️⃣ JSON Storage Compatibility Test:")
    import json

    test_token = "test_discord_bot_token_ABC123"
    encrypted = encrypt_token(test_token)

    # Simulate JSON storage
    settings_dict = {
        "discord_bot_token": encrypted,
        "discord_rpc_enabled": True,
    }

    try:
        # Serialize to JSON
        json_str = json.dumps(settings_dict, indent=2)
        print(f"   ✅ JSON serialization successful")
        print(f"   JSON preview:\n{json_str}")

        # Deserialize from JSON
        loaded_dict = json.loads(json_str)
        decrypted = decrypt_token(loaded_dict["discord_bot_token"])

        if decrypted == test_token:
            print(f"   ✅ PASS - JSON roundtrip successful")
        else:
            print(f"   ❌ FAIL - JSON roundtrip mismatch!")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test 4: Error handling
    print("\n4️⃣ Error Handling Test:")

    # Test invalid format
    try:
        decrypt_token("INVALID:aGVsbG8=")
        print("   ❌ FAIL - Should have raised ValueError")
    except ValueError as e:
        print(f"   ✅ PASS - Invalid format caught: {e}")
    except Exception as e:
        print(f"   ❌ FAIL - Wrong exception type: {e}")

    # Test corrupted data
    try:
        if DPAPI_AVAILABLE:
            decrypt_token("DPAPI:corrupted_base64_data!!!")
        else:
            decrypt_token("FERNET:corrupted_base64_data!!!")
        print("   ❌ FAIL - Should have raised exception")
    except Exception as e:
        print(f"   ✅ PASS - Corrupted data caught: {type(e).__name__}")

    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
    print()
    print("💡 Usage in your code:")
    print("   from utils.token_encryption import encrypt_token, decrypt_token")
    print("   encrypted = encrypt_token('my_bot_token')")
    print("   decrypted = decrypt_token(encrypted)")
    print()

    if not DPAPI_AVAILABLE:
        print("⚠️ WARNING: Using Fernet fallback (less secure)")
        print("   Recommendation: Install pywin32 for DPAPI support")
        print("   Command: pip install pywin32")
        print()
