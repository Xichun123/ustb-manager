"""
校园网凭据存储 - 保存密码用于自动登录
支持可选的 Fernet 加密（需安装 cryptography）
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

WIFI_CRED_PATH = Path.home() / ".ustb_manager" / "wifi_credentials.json"
WIFI_KEY_PATH = Path.home() / ".ustb_manager" / ".wifi_key"

# ---------- 加密支持（可选） ----------

_fernet = None

try:
    from cryptography.fernet import Fernet

    def _get_or_create_key() -> bytes:
        """获取或创建加密密钥，文件权限 0o600。"""
        WIFI_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if WIFI_KEY_PATH.exists():
            return WIFI_KEY_PATH.read_bytes().strip()
        key = Fernet.generate_key()
        fd = os.open(str(WIFI_KEY_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, key)
        finally:
            os.close(fd)
        return key

    _fernet = Fernet(_get_or_create_key())
    logger.info("WiFi credential encryption enabled (Fernet)")
except ImportError:
    logger.warning("cryptography not installed – WiFi passwords stored in plaintext")
except Exception as e:
    logger.warning("Failed to initialise Fernet encryption: %s – falling back to plaintext", e)


def _encrypt(plain: str) -> str:
    if _fernet is None:
        return plain
    return _fernet.encrypt(plain.encode()).decode()


def _decrypt(token: str) -> str:
    if _fernet is None:
        return token
    try:
        return _fernet.decrypt(token.encode()).decode()
    except Exception:
        # 可能是旧的明文数据，直接返回
        return token


# ---------- 数据模型 ----------

@dataclass
class WifiCredential:
    """校园网凭据"""
    student_id: str
    password: str  # 存储时为加密文本
    vpn_cookie: Optional[str] = None
    cookie_created_at: Optional[float] = None

    def get_password(self) -> str:
        """返回解密后的密码。"""
        return _decrypt(self.password)


# ---------- 存储 ----------

class WifiCredentialStore:
    """校园网凭据存储"""

    def __init__(self):
        self._credentials: dict[str, WifiCredential] = {}
        self._load()

    def _load(self):
        """从文件加载凭据"""
        if not WIFI_CRED_PATH.exists():
            return

        try:
            with open(WIFI_CRED_PATH, 'r') as f:
                data = json.load(f)
                for student_id, cred_data in data.items():
                    self._credentials[student_id] = WifiCredential(
                        student_id=cred_data.get("student_id", student_id),
                        password=cred_data.get("password", ""),
                        vpn_cookie=cred_data.get("vpn_cookie"),
                        cookie_created_at=cred_data.get("cookie_created_at"),
                    )
        except Exception:
            pass

    def _save(self):
        """保存凭据到文件"""
        WIFI_CRED_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                student_id: asdict(cred)
                for student_id, cred in self._credentials.items()
            }
            with open(WIFI_CRED_PATH, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def get(self, student_id: str) -> Optional[WifiCredential]:
        """获取凭据"""
        return self._credentials.get(student_id)

    def save_credential(self, student_id: str, password: str, vpn_cookie: Optional[str] = None):
        """保存凭据（密码会被加密存储）"""
        self._credentials[student_id] = WifiCredential(
            student_id=student_id,
            password=_encrypt(password),
            vpn_cookie=vpn_cookie,
            cookie_created_at=time.time() if vpn_cookie else None,
        )
        self._save()

    def update_cookie(self, student_id: str, vpn_cookie: str):
        """更新 VPN cookie"""
        cred = self._credentials.get(student_id)
        if cred:
            cred.vpn_cookie = vpn_cookie
            cred.cookie_created_at = time.time()
            self._save()

    def delete(self, student_id: str):
        """删除凭据"""
        if student_id in self._credentials:
            del self._credentials[student_id]
            self._save()

    def has_credential(self, student_id: str) -> bool:
        """检查是否有保存的凭据"""
        cred = self._credentials.get(student_id)
        if cred is None:
            return False
        try:
            return bool(cred.get_password())
        except Exception:
            return False


# 全局凭据存储
wifi_credential_store = WifiCredentialStore()
