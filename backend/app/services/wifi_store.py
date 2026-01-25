"""
校园网凭据存储 - 保存密码用于自动登录
"""
import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


WIFI_CRED_PATH = Path.home() / ".ustb_manager" / "wifi_credentials.json"


@dataclass
class WifiCredential:
    """校园网凭据"""
    student_id: str
    password: str
    vpn_cookie: Optional[str] = None
    cookie_created_at: Optional[float] = None


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
        """保存凭据"""
        self._credentials[student_id] = WifiCredential(
            student_id=student_id,
            password=password,
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
        return cred is not None and bool(cred.password)


# 全局凭据存储
wifi_credential_store = WifiCredentialStore()
