"""啟動入口：uv run python -m foodlog

四段防護各自用註解標出開始／結束，位置：
  防護 1 analyzer.py   claude -p 的檔案範圍隔離
  防護 2 analyzer.py   上傳者的文字只當資料
  防護 3 storage.py    食物名稱當檔名前先清洗
  防護 4 ledger.py     寫進 Excel 的文字防公式注入
行號會隨修改漂移，要找請搜尋「防護 N」，詳見 README。
"""
from __future__ import annotations

import logging
import shutil
import sys
from logging.handlers import RotatingFileHandler

import discord

from .bot import FoodBot
from .config import Config, ConfigError, load_config


def _setup_logging(cfg: Config) -> None:
    """同一份 log 同時顯示在終端機、記在 DATA_DIR/agent.log（滿 5 MB 換新檔，留 3 份舊的）。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(cfg.log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
        ],
    )
    logging.getLogger("foodlog").info(
        "啟動：模型 %s，頻道 %s，資料夾 %s，log 檔 %s", cfg.claude_model, cfg.channel_id, cfg.data_dir, cfg.log_path
    )


def main() -> None:
    # 讓終端機能正確顯示中文與 emoji
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:
        cfg = load_config()
    except ConfigError as exc:
        print(f"設定有問題：{exc}", file=sys.stderr)
        raise SystemExit(1) from None
    if shutil.which("claude") is None:
        print("找不到 claude 指令：請先安裝 Claude Code 並登入。", file=sys.stderr)
        raise SystemExit(1)

    _setup_logging(cfg)
    bot = FoodBot(cfg)
    try:
        bot.run(cfg.discord_token, log_handler=None)  # log_handler=None：用上面設定好的 logging
    except discord.LoginFailure:
        print("登入失敗：DISCORD_TOKEN 不正確。請到 Developer Portal 重新產生（Reset Token）。", file=sys.stderr)
        raise SystemExit(1) from None
    except discord.PrivilegedIntentsRequired:
        print("請到 Developer Portal → Bot，打開 Message Content Intent 並按 Save Changes。", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
