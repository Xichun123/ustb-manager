import os
import json
from pathlib import Path
from typing import Optional

# Cookie存储文件路径
COOKIE_STORE_PATH = Path.home() / ".ustb_manager" / "cookies.json"


def ensure_cookie_dir():
    """确保Cookie存储目录存在"""
    COOKIE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def save_cookies(student_id: str, cookies: dict):
    """保存Cookie到本地文件"""
    ensure_cookie_dir()

    # 读取现有的cookies
    all_cookies = {}
    if COOKIE_STORE_PATH.exists():
        try:
            with open(COOKIE_STORE_PATH, "r") as f:
                all_cookies = json.load(f)
        except Exception:
            pass

    # 更新cookies
    all_cookies[student_id] = cookies

    # 保存到文件
    with open(COOKIE_STORE_PATH, "w") as f:
        json.dump(all_cookies, f, indent=2)


def load_cookies(student_id: str) -> Optional[dict]:
    """从本地文件加载Cookie"""
    if not COOKIE_STORE_PATH.exists():
        return None

    try:
        with open(COOKIE_STORE_PATH, "r") as f:
            all_cookies = json.load(f)
            return all_cookies.get(student_id)
    except Exception:
        return None


def delete_cookies(student_id: str):
    """删除指定学生的Cookie"""
    if not COOKIE_STORE_PATH.exists():
        return

    try:
        with open(COOKIE_STORE_PATH, "r") as f:
            all_cookies = json.load(f)

        if student_id in all_cookies:
            del all_cookies[student_id]

            with open(COOKIE_STORE_PATH, "w") as f:
                json.dump(all_cookies, f, indent=2)
    except Exception:
        pass
