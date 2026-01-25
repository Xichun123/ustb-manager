"""MAC地址厂商查询服务（离线数据库）"""
import json
from pathlib import Path

_oui_db: dict[str, str] = {}

def _load_db():
    global _oui_db
    if not _oui_db:
        db_path = Path(__file__).parent.parent / "data" / "oui.json"
        if db_path.exists():
            with open(db_path, "r") as f:
                _oui_db = json.load(f)

def is_random_mac(mac: str) -> bool:
    """检查是否为随机MAC地址（本地管理地址）"""
    first_byte = int(mac.replace("-", "").replace(":", "")[:2], 16)
    return bool(first_byte & 0x02)

def get_vendor(mac: str) -> dict:
    """查询MAC地址厂商"""
    if is_random_mac(mac):
        return {"vendor": "随机MAC", "is_random": True}

    _load_db()
    prefix = mac.replace("-", "").replace(":", "")[:6].upper()
    vendor = _oui_db.get(prefix, "")
    return {"vendor": vendor, "is_random": False}
