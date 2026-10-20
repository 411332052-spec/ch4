# CLAUDE.md

一個在本機執行的 Discord agent：頻道裡有人傳食物照片，它用 `claude -p` 判斷、估熱量、記進 Excel、存照片並回覆上傳者。

## 開始任何工作前

先讀 `docs/architecture.md`。需求在 `docs/requirements.md`。設計與文件衝突時，先問使用者，不要自己改設計。

## 指令

- 啟動：`uv run python -m foodlog`（會真的連上 Discord、花使用者的 Claude 額度；`.env` 已存在時不要為了「試試看」去啟動它）
- 測試：`uv run pytest`（不連 Discord、不呼叫真的 `claude -p`）

## 四段防護

`docs/architecture.md` 第 12 節定義了四段防護，直接寫在用到它的地方（沒有獨立的 safety 檔案）：

1. 防護 1：隔離 `claude -p` 可讀的範圍 — `src/foodlog/analyzer.py`
2. 防護 2：上傳者的文字只當資料，不當指令 — `src/foodlog/analyzer.py`
3. 防護 3：食物名稱當檔名前先清洗 — `src/foodlog/storage.py`
4. 防護 4：寫進 Excel 的文字防公式注入 — `src/foodlog/ledger.py`

規則：

- 每一段都用註解標出範圍，格式固定（`tests/test_protection_markers.py` 會檢查）：
  `# ==== 防護 N：<一句話說明>　開始 ====`（「開始」前面是全形空白）與 `# ==== 防護 N 結束 ====`。
- 每一段只做一件事，彼此獨立。關掉其中一段（整段加 `#` 註解），其他三段不能受影響，程式仍要能執行。
- 每一段上方保留「沒有防護時」的寫法，這是教學對照用的，不要刪。
- **一開始四段全部開啟。** 不要為了方便測試或除錯而關掉任何一段。
- 改動程式後，`README.md` 的防護行號表要跟著更新。

## 不可以 commit 的東西

- `.env`（內含 `DISCORD_TOKEN`）。只有 `.env.example` 可以進 git。
- `DATA_DIR` 裡的照片和 Excel（`food_log.xlsx`、`photos/`、`agent.log`）。
- 任何地方都不要印出或記錄 `DISCORD_TOKEN`；也不要讀 `.env` 的內容，要確認設定時只取需要的那一項（例如 `DATA_DIR`）。

`git add` 之前先看 `git status`，不要用 `git add -A` 盲加。
