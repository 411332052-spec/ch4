"""讀取並檢查 .env 設定。"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

# 這些數字寫在程式裡，不放進 .env（.env 只有四項）
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 單張照片上限
CLAUDE_TIMEOUT_SECONDS = 120  # claude -p 最久等多久
QUEUE_MAX = 20  # 排隊區最多容納幾張
PER_USER_MAX = 3  # 同一個人同時最多排幾張
EXCEL_RETRIES = 3  # Excel 寫不進去時，第一次失敗後再重試幾次
EXCEL_RETRY_DELAY_SECONDS = 3

REQUIRED_KEYS = ("DISCORD_TOKEN", "CHANNEL_ID", "CLAUDE_MODEL", "DATA_DIR")


class ConfigError(Exception):
    """設定有問題。訊息是給使用者看的白話。"""


@dataclass(frozen=True)
class Config:
    discord_token: str
    channel_id: int
    claude_model: str
    data_dir: Path

    @property
    def photos_dir(self) -> Path:
        return self.data_dir / "photos"

    @property
    def excel_path(self) -> Path:
        return self.data_dir / "food_log.xlsx"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "agent.log"


def load_config(env_file: Path | None = None) -> Config:
    load_dotenv(env_file or REPO_ROOT / ".env")

    missing = [key for key in REQUIRED_KEYS if not os.environ.get(key, "").strip()]
    if missing:
        raise ConfigError(
            f".env 缺少這些項目：{'、'.join(missing)}。請照 .env.example 補齊。"
        )

    try:
        channel_id = int(os.environ["CHANNEL_ID"].strip())
    except ValueError:
        raise ConfigError("CHANNEL_ID 必須是一串數字（在 Discord 對頻道按右鍵複製頻道 ID）。") from None

    data_dir = Path(os.path.expanduser(os.environ["DATA_DIR"].strip()))
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir  # 相對路徑一律從專案資料夾算起，不隨啟動位置改變
    data_dir = data_dir.resolve()
    try:
        (data_dir / "photos").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=data_dir):
            pass
    except OSError as exc:
        raise ConfigError(f"DATA_DIR（{data_dir}）無法建立或寫入：{exc}") from None

    return Config(
        discord_token=os.environ["DISCORD_TOKEN"].strip(),
        channel_id=channel_id,
        claude_model=os.environ["CLAUDE_MODEL"].strip(),
        data_dir=data_dir,
    )
