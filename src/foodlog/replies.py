"""回覆上傳者的文字。"""
from __future__ import annotations

from discord.utils import escape_mentions

from .analysis import Analysis

DISCORD_LIMIT = 1900  # Discord 單則訊息上限 2000 字，留點餘地

FAIL_ANALYSIS = "分析失敗，請再傳一次"
FAIL_BAD_IMAGE = "這個檔案不是我看得懂的圖片（支援 JPG、PNG、WebP、GIF），請再傳一次"
FAIL_TOO_BIG = "圖片太大了（上限 10 MB），請縮小後再傳"
FAIL_LEDGER = "已收到，但紀錄暫時寫不進去，請稍後再傳一次"
FAIL_GENERIC = "處理這張照片時發生問題，請再傳一次"
BUSY_FULL = "目前人多，請稍後再傳"
BUSY_USER = "你還有照片在排隊，請等一下再傳"


def _clean(text: str) -> str:
    """AI 回來的文字不可信：拆掉 @everyone、@here、<@id> 這類會通知人的寫法。"""
    return escape_mentions(text)


def _fit(text: str) -> str:
    return text if len(text) <= DISCORD_LIMIT else text[: DISCORD_LIMIT - 1] + "…"


def food_reply(mention: str, analysis: Analysis, daily_total: int) -> str:
    ingredients = "、".join(analysis.ingredients) or "（沒有列出）"
    return _fit(
        f"{mention} 這餐是：{_clean(analysis.name)}\n"
        f"成份：{_clean(ingredients)}\n"
        f"約 {analysis.weight_g:,} 公克，約 {analysis.calories_kcal:,} 大卡（以上都是估計值）\n"
        f"當日已攝取熱量（全頻道合計）：約 {daily_total:,} 大卡"
    )


def not_food_reply(mention: str, analysis: Analysis, daily_total: int) -> str:
    return _fit(
        f"{mention} 你傳的不是食物，是{_clean(analysis.name)}。\n"
        f"當日已攝取熱量（全頻道合計）：約 {daily_total:,} 大卡（這張不算）"
    )
