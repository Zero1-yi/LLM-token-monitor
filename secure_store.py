"""Secure storage layer: DPAPI-protected Fernet encryption for config at rest.

Strategy:
- Generate a random Fernet key on first run.
- Encrypt the Fernet key with Windows DPAPI (CryptProtectData), store on disk.
- Use the Fernet key to encrypt/decrypt the JSON config file.
- The DPAPI binding means only the current Windows user can decrypt the key.
"""

import ctypes
import json
import os
import base64
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet


# Windows DPAPI constants
_CRYPTPROTECT_UI_FORBIDDEN = 0x1
_CRYPTPROTECT_LOCAL_MACHINE = 0x4


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.c_void_p),
    ]


def _dpapi_encrypt(data: bytes) -> bytes:
    """Encrypt data using Windows DPAPI (CryptProtectData).

    The output is bound to the current user account and machine.
    """
    blob_in = _DATA_BLOB(len(data), ctypes.cast(data, ctypes.c_void_p))
    blob_out = _DATA_BLOB()

    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,  # szDataDescr
        None,  # pOptionalEntropy
        None,  # pvReserved
        None,  # pPromptStruct
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(blob_out),
    ):
        raise OSError("CryptProtectData failed")

    try:
        result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        # Must cast to c_void_p for 64-bit compatibility
        ctypes.windll.kernel32.LocalFree(ctypes.c_void_p(blob_out.pbData))

    return result


def _dpapi_decrypt(data: bytes) -> bytes:
    """Decrypt data using Windows DPAPI (CryptUnprotectData)."""
    blob_in = _DATA_BLOB(len(data), ctypes.cast(data, ctypes.c_void_p))
    blob_out = _DATA_BLOB()

    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,  # ppszDataDescr
        None,  # pOptionalEntropy
        None,  # pvReserved
        None,  # pPromptStruct
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(blob_out),
    ):
        raise OSError("CryptUnprotectData failed")

    try:
        result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        # Must cast to c_void_p for 64-bit compatibility
        ctypes.windll.kernel32.LocalFree(ctypes.c_void_p(blob_out.pbData))

    return result


class SecureStore:
    """Encrypts/decrypts a JSON-serializable dict using Fernet + DPAPI.

    Files (stored in %APPDATA%/LLMTokenMonitor/):
        .keyfile   — DPAPI-encrypted Fernet key
        config.enc — Fernet-encrypted JSON configuration
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
            config_dir = Path(appdata) / "LLMTokenMonitor"
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.enc"
        self._key_file = self._config_dir / ".keyfile"
        self._fernet: Optional[Fernet] = None

    def _get_or_create_fernet(self) -> Fernet:
        """Load existing DPAPI-protected Fernet key, or generate a new one."""
        if self._fernet is not None:
            return self._fernet

        if self._key_file.exists():
            encrypted_key = self._key_file.read_bytes()
            fernet_key = _dpapi_decrypt(encrypted_key)
        else:
            fernet_key = Fernet.generate_key()
            encrypted_key = _dpapi_encrypt(fernet_key)
            self._key_file.write_bytes(encrypted_key)

        self._fernet = Fernet(fernet_key)
        return self._fernet

    def load(self) -> dict:
        """Read and decrypt config file. Returns empty dict on first run."""
        if not self._config_file.exists():
            return {}

        fernet = self._get_or_create_fernet()
        try:
            encrypted_data = self._config_file.read_bytes()
            decrypted = fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            # Corrupted or tampered file — return empty, will be overwritten
            return {}

    def save(self, data: dict) -> None:
        """Encrypt and write config dict to disk."""
        fernet = self._get_or_create_fernet()
        plaintext = json.dumps(data, ensure_ascii=False, indent=2)
        encrypted = fernet.encrypt(plaintext.encode("utf-8"))
        self._config_file.write_bytes(encrypted)

    def delete_config(self) -> None:
        """Remove stored configuration (for reset purposes)."""
        if self._config_file.exists():
            self._config_file.unlink()
        if self._key_file.exists():
            self._key_file.unlink()
        self._fernet = None
