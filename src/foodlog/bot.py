"""Discord 這一端：收訊息、加 ⏳、排隊、處理、回覆。

處理流程的每個步驟都會寫 log（終端機與 DATA_DIR/agent.log）。
同一張照片的 log 都帶同一個標籤 [訊息ID 第n/m張]，方便從頭追到尾。
"""
from __future__ import annotations

import logging
import os
import re
import time

import discord

from . import replies
from .analysis import AnalysisError
from .analyzer import analyze_photo
from .config import MAX_IMAGE_BYTES, PER_USER_MAX, QUEUE_MAX, Config
from .ledger import Ledger, LedgerBusyError, MealRecord
from .queueing import REJECT_FULL, Job, JobQueue
from .storage import detect_image_ext, relative_to_data_dir, save_photo

log = logging.getLogger(__name__)

WAITING_EMOJI = "⏳"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")
NOT_FOOD_STEM = "不是食物"


class _Reject(Exception):
    """已知的失敗：訊息就是要回覆給上傳者的白話。"""


def _for_log(value: object, limit: int = 60) -> str:
    """別人給的文字（暱稱、AI 回的名稱）寫進 log 前，換行等控制字元要換掉，免得假造出多行 log。"""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _looks_like_image(attachment: discord.Attachment) -> bool:
    if attachment.content_type and attachment.content_type.startswith("image/"):
        return True
    return attachment.filename.lower().endswith(IMAGE_SUFFIXES)


class FoodBot(discord.Client):
    def __init__(self, cfg: Config) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # 要打開 Developer Portal 的 Message Content Intent 才看得到附件
        super().__init__(intents=intents)
        self.cfg = cfg
        self.ledger = Ledger(cfg.excel_path)
        self.jobs = JobQueue(self._process, QUEUE_MAX, PER_USER_MAX)
        self._pending: dict[int, int] = {}  # 訊息 id -> 這則訊息還有幾張在排隊或處理中

    async def setup_hook(self) -> None:
        self.jobs.start()

    async def close(self) -> None:
        await self.jobs.stop()
        await super().close()

    async def on_ready(self) -> None:
        log.info("已登入為 %s", self.user)
        if self.get_channel(self.cfg.channel_id) is None:
            log.warning("看不到 CHANNEL_ID=%s 這個頻道：請確認 bot 已被邀進 Server、頻道 ID 沒填錯", self.cfg.channel_id)
        else:
            log.info("正在聽頻道 %s，等待照片…", self.cfg.channel_id)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.channel.id != self.cfg.channel_id:
            return
        images = [a for a in message.attachments if _looks_like_image(a)]
        if not images:
            log.debug("訊息 %s 沒有圖片附件，略過", message.id)
            return  # 沒有圖片附件：完全不理

        uploader = _for_log(message.author.display_name)
        log.info("收到 %s 的訊息 %s：%d 張圖片", uploader, message.id, len(images))

        accepted, rejection = 0, None
        for number, attachment in enumerate(images, start=1):  # 一則訊息有好幾張圖，每張各算一餐
            tag = f"[{message.id} 第{number}/{len(images)}張]"
            job = Job(message.author.id, message, attachment, tag)
            rejection = self.jobs.put(job)
            if rejection is not None:
                log.warning("%s 沒有加入排隊：%s", tag, "排隊區已滿" if rejection == REJECT_FULL else f"{uploader} 排隊中的照片太多")
                break
            accepted += 1
            self._pending[message.id] = self._pending.get(message.id, 0) + 1
            log.info("%s 已加入排隊（排隊與處理中共 %d 張）", tag, self.jobs.size)

        if accepted:
            await self._add_waiting_reaction(message)
            if message.id not in self._pending:  # 加反應的空檔，已經全部處理完了
                await self._remove_waiting_reaction(message)
        if rejection is not None:
            text = replies.BUSY_FULL if rejection == REJECT_FULL else replies.BUSY_USER
            await self._reply(message, text)

    async def _process(self, job: Job) -> None:
        message, tag = job.message, job.tag
        started = time.monotonic()
        log.info("%s 輪到了，開始處理", tag)
        try:
            await self._handle(job)
            log.info("%s 處理完成，共 %.1f 秒", tag, time.monotonic() - started)
        except _Reject as reject:
            log.warning("%s 處理中止，回覆上傳者：%s", tag, reject)
            await self._reply(message, str(reject))
        except AnalysisError as exc:
            log.warning("%s 分析失敗（%.1f 秒）：%s", tag, time.monotonic() - started, exc)
            await self._reply(message, replies.FAIL_ANALYSIS)
        except Exception:
            log.exception("%s 處理照片時發生未預期的錯誤", tag)
            await self._reply(message, replies.FAIL_GENERIC)
        finally:
            self._pending[message.id] -= 1
            if self._pending[message.id] <= 0:
                del self._pending[message.id]
                await self._remove_waiting_reaction(message)

    async def _handle(self, job: Job) -> None:
        message, attachment, tag = job.message, job.attachment, job.tag
        if attachment.size > MAX_IMAGE_BYTES:
            raise _Reject(replies.FAIL_TOO_BIG)
        data = await attachment.read()
        ext = detect_image_ext(data)
        log.info("%s 已下載照片：%d KB，格式 %s", tag, len(data) // 1024, ext or "無法辨識")
        if ext is None:
            raise _Reject(replies.FAIL_BAD_IMAGE)

        log.info("%s 呼叫 claude -p 分析（模型 %s）", tag, self.cfg.claude_model)
        analyze_started = time.monotonic()
        analysis = await analyze_photo(self.cfg, data, ext, caption=message.content)
        log.info(
            "%s 分析結果（%.1f 秒）：%s「%s」成份 %d 樣，約 %d 公克、%d 大卡",
            tag,
            time.monotonic() - analyze_started,
            "食物" if analysis.is_food else "不是食物",
            _for_log(analysis.name),
            len(analysis.ingredients),
            analysis.weight_g,
            analysis.calories_kcal,
        )

        when = message.created_at.astimezone().replace(tzinfo=None)  # 本機時間
        stem = analysis.name if analysis.is_food else NOT_FOOD_STEM
        photo_path = save_photo(self.cfg.photos_dir, when, stem, ext, data)
        photo_rel = relative_to_data_dir(photo_path, self.cfg.data_dir)
        log.info("%s 照片已存：%s", tag, _for_log(photo_rel, 120))

        record = MealRecord(
            when=when,
            uploader=message.author.display_name,
            description=analysis.name if analysis.is_food else NOT_FOOD_STEM,
            ingredients="、".join(analysis.ingredients) if analysis.is_food else analysis.name,
            weight_g=analysis.weight_g,
            calories_kcal=analysis.calories_kcal,
            photo_path=photo_rel,
        )
        try:
            daily_total = await self.ledger.append_meal(record)
        except LedgerBusyError:
            os.remove(photo_path)  # 沒建成檔，就不留孤兒照片
            log.warning("%s Excel 寫入失敗，已刪除剛存的照片，這張不算進當日熱量", tag)
            raise _Reject(replies.FAIL_LEDGER) from None
        log.info("%s 已寫入 Excel（%s），當日累計 %d 大卡", tag, self.cfg.excel_path.name, daily_total)

        mention = message.author.mention
        make_reply = replies.food_reply if analysis.is_food else replies.not_food_reply
        await self._reply(message, make_reply(mention, analysis, daily_total))
        log.info("%s 已回覆上傳者 %s", tag, _for_log(record.uploader))

    async def _reply(self, message: discord.Message, text: str) -> None:
        """回覆該則訊息（不用私訊）。只准通知上傳者本人。"""
        mention = message.author.mention
        if not text.startswith(mention):
            text = f"{mention} {text}"
        allowed = discord.AllowedMentions(
            everyone=False, roles=False, users=[message.author], replied_user=True
        )
        try:
            await message.reply(text, allowed_mentions=allowed)
        except discord.HTTPException as exc:
            log.warning("回覆失敗（訊息可能已被刪除）：%s", exc)

    async def _add_waiting_reaction(self, message: discord.Message) -> None:
        try:
            await message.add_reaction(WAITING_EMOJI)
        except discord.HTTPException as exc:
            log.warning("加 %s 反應失敗（bot 需要 Add Reactions 權限）：%s", WAITING_EMOJI, exc)

    async def _remove_waiting_reaction(self, message: discord.Message) -> None:
        try:
            await message.remove_reaction(WAITING_EMOJI, self.user)
        except discord.HTTPException:
            pass  # 訊息被刪、或根本沒加成功，都不用管
