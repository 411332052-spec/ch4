# 食物照片記錄 agent

一支在你電腦上執行的 Discord bot。指定頻道裡有人傳食物照片，它用 `claude -p` 判斷是不是食物、估重量和熱量，記進 Excel、存照片，再回覆上傳者。程式關掉就不處理。

設計說明在 `docs/architecture.md`，需求在 `docs/requirements.md`。

## 第一次使用

1. 照 `docs/discord-server-setup.md` 和 `docs/discord-bot-setup.md` 準備好 Discord（bot 需要 View Channels、Send Messages、Read Message History、**Add Reactions** 四項權限，並打開 Message Content Intent）。
2. 把 `.env.example` 複製成 `.env`，填入四項：

   | 項目 | 意思 |
   |---|---|
   | `DISCORD_TOKEN` | bot 的密碼。**不能貼給任何人、不能貼進對話、不能 commit** |
   | `CHANNEL_ID` | 要聽的那一個頻道 |
   | `CLAUDE_MODEL` | `claude -p` 用的模型，例如 `sonnet` |
   | `DATA_DIR` | Excel 與照片放的資料夾。建議放在專案資料夾之外；寫相對路徑時從專案資料夾算起 |

3. 確認電腦上的 `claude` 已經登入（在終端機輸入 `claude` 能正常使用）。

## 啟動

```
uv run python -m foodlog
```

第一次執行 uv 會自動安裝需要的套件。看到 `已登入為 …` 和 `正在聽頻道 …` 就是成功了。按 `Ctrl + C` 停止。

啟動後在指定頻道傳一張食物照片：訊息上會先出現 ⏳，處理完 ⏳ 消失，bot 會回覆結果。

結果存在 `DATA_DIR` 底下：

- `food_log.xlsx`：紀錄，一直往下加。**agent 開著時請不要直接打開它**（Windows 會鎖住檔案，agent 會在終端機警告並重試）；要看請先複製一份。
- `photos/`：照片，檔名 `YYYY-MM-DD hh-mm-ss 名稱.副檔名`。
- `agent.log`：執行紀錄。

## Log：看得到每一步，也有紀錄

每張照片從收到到回覆的每個步驟都會寫 log，**同時顯示在終端機、記在 `DATA_DIR/agent.log`**（滿 5 MB 會換新檔，保留 3 份舊的）。同一張照片的每一行都帶同一個標籤 `[訊息ID 第n/m張]`，可以用它從頭追到尾：

```
INFO foodlog.bot: 收到 Penny 的訊息 1234567890：1 張圖片
INFO foodlog.bot: [1234567890 第1/1張] 已加入排隊（排隊與處理中共 1 張）
INFO foodlog.bot: [1234567890 第1/1張] 輪到了，開始處理
INFO foodlog.bot: [1234567890 第1/1張] 已下載照片：312 KB，格式 jpg
INFO foodlog.bot: [1234567890 第1/1張] 呼叫 claude -p 分析（模型 sonnet）
INFO foodlog.bot: [1234567890 第1/1張] 分析結果（8.2 秒）：食物「雞腿便當」成份 4 樣，約 650 公克、920 大卡
INFO foodlog.bot: [1234567890 第1/1張] 照片已存：photos\2026-10-20 14-30-05 雞腿便當.jpg
INFO foodlog.bot: [1234567890 第1/1張] 已寫入 Excel（food_log.xlsx），當日累計 920 大卡
INFO foodlog.bot: [1234567890 第1/1張] 已回覆上傳者 Penny
INFO foodlog.bot: [1234567890 第1/1張] 處理完成，共 9.6 秒
```

出問題時會是 `WARNING`（例如分析失敗、Excel 寫不進去、排隊被拒絕），沒預期到的錯誤是 `ERROR` 並附上詳細原因。log 裡**不會**出現 `DISCORD_TOKEN`，別人取的暱稱或 AI 回的名稱裡的換行也會先換成空白，避免有人假造 log。

## 四段防護在哪裡

每一段都用這種註解標出開始和結束，一開始全部開啟：

```python
# ==== 防護 1：claude -p 的檔案範圍隔離　開始 ====
...
# ==== 防護 1 結束 ====
```

| 防護 | 做什麼 | 檔案與大約行號 |
|---|---|---|
| 防護 1 | `claude -p` 只在「只有這一張照片」的暫存資料夾裡工作，讀不到 `DATA_DIR` | `src/foodlog/analyzer.py` 約第 127–132 行 |
| 防護 2 | 上傳者打的字完全不送進給 `claude -p` 的指令 | `src/foodlog/analyzer.py` 約第 45–48 行 |
| 防護 3 | 食物名稱當檔名前，先清掉 `/` `\` `..` `:` 等字 | `src/foodlog/storage.py` 約第 43–61 行 |
| 防護 4 | 寫進 Excel 的文字若以 `=` `+` `-` `@` 開頭，先處理成純文字 | `src/foodlog/ledger.py` 約第 53–59 行 |

行號是寫成時的位置，改了程式會漂移。要重新找，在專案資料夾執行：

```
Select-String -Path src\foodlog\*.py -Pattern "防護 \d：.*開始|防護 \d 結束"
```

**之後上課要單獨關掉某一段**：把「開始」到「結束」之間的程式碼整段加上 `#` 註解（兩行標記本身留著）。每一段的上一行都留著「沒有防護時」的寫法，所以整段註解掉後程式仍能執行，只是少了那一層保護。

## 測試

```
uv run pytest
```

測試不連 Discord，也不會呼叫真的 `claude -p`，是用假的訊息和假的 AI 回傳內容，檢查流程、JSON 檢查、檔名清洗、Excel 寫入、排隊與四段防護。真的連 Discord 的最後一關要自己在頻道傳照片試。

## 不可以 commit 的東西

`.env`、`DATA_DIR` 裡的照片和 Excel。`.gitignore` 已經擋住 `.env`、`data/`、`photos/`、`*.xlsx`；`DATA_DIR` 如果放在專案資料夾裡又用了別的名字，要自己補進 `.gitignore`。
