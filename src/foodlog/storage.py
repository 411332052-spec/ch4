"""照片的判斷與存檔。

四段防護裡的「防護 3」在這個檔案。
"""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
MAX_STEM_CHARS = 20
FALLBACK_STEM = "未命名"


def detect_image_ext(data: bytes) -> str | None:
    """看檔案開頭判斷圖片格式，不相信上傳者給的檔名或副檔名。"""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def timestamp_text(when: datetime) -> str:
    """YYYY-MM-DD hh-mm-ss（用 - 不用冒號，Windows 才存得了）。"""
    return when.strftime("%Y-%m-%d %H-%M-%S")


def build_stem(raw_name: str, photos_dir: Path, timestamp: str, ext: str) -> str:
    """把 AI 給的食物名稱變成可以放進檔名的簡稱。"""
    stem = raw_name  # 沒有防護時：AI 給什麼名稱，就直接拿來當檔名
    # ==== 防護 3：食物名稱當檔名前先清洗　開始 ====
    # 全形的／＼：先轉成半形，才清得掉
    stem = unicodedata.normalize("NFKC", raw_name)
    stem = re.sub(r"[\x00-\x1f\x7f]", " ", stem)  # 控制字元（換行、tab…）
    stem = re.sub(r'[/\\:*?"<>|]', " ", stem)  # 路徑分隔、冒號、Windows 不允許的字
    while ".." in stem:
        stem = stem.replace("..", " ")  # 「往上一層」
    stem = re.sub(r"\s+", "_", stem.strip())
    stem = re.sub(r"[^\w\-]", "", stem)  # 只留中英文字、數字、底線、減號（連單一的點也清掉）
    stem = stem.strip("_-")[:MAX_STEM_CHARS]
    if not stem:
        stem = FALLBACK_STEM
    if stem.upper() in WINDOWS_RESERVED:
        stem += "_"
    # 最後一道保險：組出來的路徑必須真的還在 photos 資料夾裡
    trial = photos_dir / f"{timestamp} {stem}.{ext}"
    if trial.resolve().parent != photos_dir.resolve():
        stem = FALLBACK_STEM
    # ==== 防護 3 結束 ====
    return stem


def save_photo(photos_dir: Path, when: datetime, raw_name: str, ext: str, data: bytes) -> Path:
    """存照片。檔名：YYYY-MM-DD hh-mm-ss 名稱.副檔名；同一秒撞名就在名稱後加 -2、-3。"""
    timestamp = timestamp_text(when)
    stem = build_stem(raw_name, photos_dir, timestamp, ext)
    for n in range(1, 1000):
        suffix = "" if n == 1 else f"-{n}"
        path = photos_dir / f"{timestamp} {stem}{suffix}.{ext}"
        try:
            with open(path, "xb") as f:  # x：只准新建，絕不覆蓋已存在的檔案
                f.write(data)
            return path
        except FileExistsError:
            continue
    raise OSError(f"同一秒內撞名太多次，無法存檔：{timestamp} {stem}")


def relative_to_data_dir(path: Path, data_dir: Path) -> str:
    return os.path.relpath(path, data_dir)
