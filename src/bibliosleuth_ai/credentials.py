"""Small native credential-vault adapter; secrets never enter Calibre JSONConfig."""

import ctypes
import ctypes.util
import os
import shutil
import subprocess
import sys
from ctypes import wintypes


SERVICE = "org.calibre.bibliosleuth_ai.openai"
ACCOUNT = "openai-api-key"


class CredentialStoreError(RuntimeError):
    pass


def _identity(provider="openai"):
    provider = str(provider or "openai").strip().lower()
    if provider not in ("openai", "anthropic", "ollama", "lmstudio"):
        raise CredentialStoreError("Unknown credential provider")
    if provider == "openai":
        return SERVICE, ACCOUNT
    return "org.calibre.bibliosleuth_ai.%s" % provider, "%s-api-key" % provider


def _run(args, input_text=None):
    try:
        return subprocess.run(
            args,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CredentialStoreError("Operating-system credential storage failed") from exc


def available():
    if sys.platform == "darwin":
        return bool(ctypes.util.find_library("Security"))
    if os.name == "nt":
        return True
    return bool(shutil.which("secret-tool"))


def load(provider="openai"):
    service, account = _identity(provider)
    if sys.platform == "darwin":
        secret, item = _mac_find(service, account)
        _mac_release(item)
        return secret
    if os.name == "nt":
        return _windows_load(service)
    if shutil.which("secret-tool"):
        result = _run(["secret-tool", "lookup", "service", service, "account", account])
        return result.stdout.rstrip("\r\n") if result.returncode == 0 else ""
    return ""


def save(secret, provider="openai"):
    service, account = _identity(provider)
    secret = (secret or "").strip()
    if not secret:
        delete(provider)
        return
    if sys.platform == "darwin":
        _mac_save(secret, service, account)
        return
    if os.name == "nt":
        _windows_save(secret, service, account)
        return
    if shutil.which("secret-tool"):
        result = _run(
            ["secret-tool", "store", "--label=BiblioSleuth AI %s API key" % provider, "service", service, "account", account],
            secret + "\n",
        )
        if result.returncode != 0:
            raise CredentialStoreError("Could not save the API key in Secret Service")
        return
    raise CredentialStoreError("No supported operating-system credential vault is available")


def delete(provider="openai"):
    service, account = _identity(provider)
    if sys.platform == "darwin":
        _mac_delete(service, account)
    elif os.name == "nt":
        _windows_delete(service)
    elif shutil.which("secret-tool"):
        _run(["secret-tool", "clear", "service", service, "account", account])


if sys.platform == "darwin":
    _security = ctypes.CDLL(ctypes.util.find_library("Security"))
    _core_foundation = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
    _security.SecKeychainFindGenericPassword.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
    ]
    _security.SecKeychainFindGenericPassword.restype = ctypes.c_int32
    _security.SecKeychainAddGenericPassword.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
    ]
    _security.SecKeychainAddGenericPassword.restype = ctypes.c_int32
    _security.SecKeychainItemModifyAttributesAndData.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    _security.SecKeychainItemModifyAttributesAndData.restype = ctypes.c_int32
    _security.SecKeychainItemDelete.argtypes = [ctypes.c_void_p]
    _security.SecKeychainItemDelete.restype = ctypes.c_int32
    _security.SecKeychainItemFreeContent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    _security.SecKeychainItemFreeContent.restype = ctypes.c_int32
    _core_foundation.CFRelease.argtypes = [ctypes.c_void_p]


def _mac_bytes(value):
    return value.encode("utf-8")


def _mac_release(item):
    if item and sys.platform == "darwin":
        _core_foundation.CFRelease(item)


def _mac_find(service=SERVICE, account=ACCOUNT):
    service, account = _mac_bytes(service), _mac_bytes(account)
    length = ctypes.c_uint32()
    data = ctypes.c_void_p()
    item = ctypes.c_void_p()
    status = _security.SecKeychainFindGenericPassword(
        None, len(service), service, len(account), account,
        ctypes.byref(length), ctypes.byref(data), ctypes.byref(item),
    )
    if status != 0:
        return "", None
    try:
        secret = ctypes.string_at(data, length.value).decode("utf-8")
    finally:
        _security.SecKeychainItemFreeContent(None, data)
    return secret, item


def _mac_save(secret, service=SERVICE, account=ACCOUNT):
    existing, item = _mac_find(service, account)
    raw = _mac_bytes(secret)
    try:
        if item:
            status = _security.SecKeychainItemModifyAttributesAndData(item, None, len(raw), raw)
        else:
            service, account = _mac_bytes(service), _mac_bytes(account)
            created = ctypes.c_void_p()
            status = _security.SecKeychainAddGenericPassword(
                None, len(service), service, len(account), account, len(raw), raw, ctypes.byref(created),
            )
            _mac_release(created)
        if status != 0:
            raise CredentialStoreError("Could not save the API key in macOS Keychain (status %d)" % status)
    finally:
        _mac_release(item)


def _mac_delete(service=SERVICE, account=ACCOUNT):
    secret, item = _mac_find(service, account)
    if not item:
        return
    try:
        status = _security.SecKeychainItemDelete(item)
        if status != 0:
            raise CredentialStoreError("Could not delete the API key from macOS Keychain (status %d)" % status)
    finally:
        _mac_release(item)


if os.name == "nt":
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR), ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
        ]

    _advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    _advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
    _advapi.CredReadW.restype = wintypes.BOOL
    _advapi.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    _advapi.CredWriteW.restype = wintypes.BOOL
    _advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    _advapi.CredDeleteW.restype = wintypes.BOOL
    _advapi.CredFree.argtypes = [ctypes.c_void_p]


def _windows_load(service=SERVICE):
    pointer = ctypes.POINTER(CREDENTIALW)()
    if not _advapi.CredReadW(service, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        return ""
    try:
        credential = pointer.contents
        raw = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        return raw.decode("utf-16-le")
    finally:
        _advapi.CredFree(pointer)


def _windows_save(secret, service=SERVICE, account=ACCOUNT):
    raw = secret.encode("utf-16-le")
    blob = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    credential = CREDENTIALW()
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = service
    credential.CredentialBlobSize = len(raw)
    credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = account
    if not _advapi.CredWriteW(ctypes.byref(credential), 0):
        raise CredentialStoreError("Could not save the API key in Windows Credential Manager")


def _windows_delete(service=SERVICE):
    _advapi.CredDeleteW(service, CRED_TYPE_GENERIC, 0)
