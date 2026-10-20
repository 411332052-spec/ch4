# Discord Bot 設定步驟

這份文件帶你做：

1. 在 Discord Developer Portal 建立一個 application 和 bot
2. 打開 Message Content Intent（一定要）
3. 拿到 bot token
4. 設定權限，並把 bot 邀進你自己的 Server

請先完成 `docs/discord-server-setup.md`（你要先有 Server 和 `# food-log` 頻道）。

> **適用環境**：Windows 電腦，用瀏覽器（Chrome、Edge 都可以）操作網頁。
> Discord 偶爾會改畫面，如果某個按鈕的位置或字樣和下面寫的稍有不同，請找名稱最接近的選項。
> 下面用「**粗體**」標示畫面上要點的字。

**名詞先解釋**

- **Developer Portal（開發者後台）**：Discord 給開發者管理自己程式的網站，網址是 `discord.com/developers/applications`。
- **application**：你在 Discord 登記的一個「程式身分」。一個 application 底下可以有一個 bot。
- **bot**：在 Discord 裡看起來像一個會員的程式帳號。我們的 agent 就是用這個 bot 的身分，去讀頻道的訊息和回覆。
- **token（權杖）**：bot 的密碼。拿到 token 的人，可以完全冒充你的 bot。

---

## ⚠️ 先看這一段：bot token 的鐵則

> ### bot token 絕對不能：
> - ❌ **貼給任何人**（包含同學、朋友、老師、客服）
> - ❌ **貼進這個對話**（也就是和 Claude 的對話視窗，連一小段都不行）
> - ❌ **commit 進 git**，也不能 push 到 GitHub
> - ❌ 貼進 Discord 任何頻道、LINE、Email、截圖
>
> token 應該只存在你電腦上一個叫 `.env` 的設定檔裡（`.env` 已經被 `.gitignore` 擋住，不會被 commit）。
>
> **如果不小心洩漏了**：馬上回到 Developer Portal 的 Bot 頁，按 **「Reset Token」** 重新產生一組，舊的那組會立刻失效。洩漏過的 token 永遠不要再用。
>
> Claude 在這個專案裡也不會要你把 token 貼給它。如果有任何對話或網頁要你貼 token，那就是不對勁的，請停下來。

---

## 一、建立 application 和 bot

1. 用瀏覽器打開 `https://discord.com/developers/applications`，用你的 Discord 帳號登入（如果跳出「授權」畫面，點 **「授權」**）。
2. 點畫面右上角的藍色按鈕 **「New Application」**（新增應用程式）。
3. 在「Name」欄位輸入名稱，例如 `food-log-bot`。這個名字會成為 bot 在 Discord 裡顯示的名字。
4. 勾選下方的同意條款（「I agree to the Discord Developer Terms of Service and Developer Policy」），點 **「Create」**。
5. 進到這個 application 的設定頁。看畫面**左邊的選單**，找到 **「Bot」**，點它。
6. 在 Bot 頁面，往下捲，找到兩個開關，確認如下：
   - **「Public Bot」**：**關閉**。（關閉後只有你自己能把這個 bot 邀進 Server，別人邀請不了。）
   - **「Requires OAuth2 Code Grant」**：**關閉**（預設就是關閉）。

> 你不需要自己「新增 bot」。新版 Developer Portal 建立 application 時，bot 已經自動附在裡面，Bot 頁面就能看到它。

---

## 二、打開 Message Content Intent（一定要）

**為什麼一定要打開**

Discord 預設不讓 bot 看見訊息的「內容」，包含**附件（照片）**。這是為了保護隱私。我們的 agent 需要從訊息裡找出照片附件，所以必須打開 **Message Content Intent**（訊息內容權限）。沒有打開的話，agent 連上線後會看到每一則訊息都沒有附件，等於看不到任何照片，也就不會有任何反應。

**步驟**

1. 仍在左邊選單的 **「Bot」** 頁面。
2. 往下捲到 **「Privileged Gateway Intents」** 這一區（特權 Gateway 權限）。
3. 找到 **「Message Content Intent」**，把右邊的開關**打開**（變成藍色／綠色）。
4. 另外兩個（**Presence Intent**、**Server Members Intent**）**保持關閉**，我們用不到，少開比較安全。
5. 頁面下方（或上方）會跳出「儲存變更」的提示列，點 **「Save Changes」**（儲存變更）。一定要按，沒按的話設定不會生效。

> 只要你的 bot 加入的 Server 少於 100 個，這個權限可以直接自己打開，不需要向 Discord 申請。

---

## 三、拿到 bot token

1. 仍在 **「Bot」** 頁面，往上捲到 bot 名稱那一區，找到 **「Token」** 這一欄。
2. 點 **「Reset Token」**（重設權杖）。
3. 跳出確認視窗，點 **「Yes, do it!」**。如果 Discord 要你輸入密碼或兩步驟驗證碼，照做。
4. 畫面會顯示一長串字元，**這就是 token，而且只會顯示這一次**。
5. 點旁邊的 **「Copy」**（複製）。
6. **立刻**把它存到安全的地方。建議做法（擇一）：
   - 存進密碼管理員（例如 Windows 的瀏覽器密碼管理、Bitwarden 等）。
   - 暫時貼進一個**不在 `C:\Users\Penny\ch4` 底下**的記事本檔案，等之後寫 `.env` 時使用，用完就刪。
7. **不要截圖、不要貼到任何對話或頻道。**

> 沒複製到、或忘了存？沒關係，再按一次 **「Reset Token」** 重新產生一組就好（舊的會作廢）。

之後寫 `.env` 時，token 會填在 `DISCORD_TOKEN=` 後面。這個動作會在寫程式的階段一起做，現在先把 token 留好。

---

## 四、設定權限，並把 bot 邀進你的 Server

### 4-1. 我們要給 bot 哪些權限

只給「剛好夠用」的四項，**不要給管理員**：

| 權限（畫面上的英文） | 為什麼需要 |
|---|---|
| **View Channels** | 看得見 `# food-log` 頻道，才讀得到訊息 |
| **Send Messages** | 能在頻道裡回覆「處理中」和結果 |
| **Read Message History** | 回覆時要接在原本那張照片底下，需要能讀到那則訊息 |
| **Add Reactions** | 收到照片時，要在那則訊息上加一個 ⏳ 反應，表示「收到、排隊中」 |

> bot 修改（編輯）自己發出的訊息，不需要額外權限，所以「把處理中改成結果」不需要再多開。
> 這四項之外的（Administrator、Manage Server、Manage Messages 等）一律**不要勾**。

### 4-2. 產生邀請連結

1. 仍在 Developer Portal，看左邊選單，找到 **「OAuth2」**，點它。
2. 往下捲到 **「OAuth2 URL Generator」**（OAuth2 網址產生器）這一區。
3. 在 **「SCOPES」**（範圍）清單裡，只勾 **`bot`**。其他（例如 `applications.commands`）不要勾。
4. 勾了 `bot` 之後，下面會多出一區 **「BOT PERMISSIONS」**（bot 權限）。在裡面只勾這四項：
   - **View Channels**（在「General Permissions」分類下）
   - **Send Messages**（在「Text Permissions」分類下）
   - **Read Message History**（在「Text Permissions」分類下）
   - **Add Reactions**（在「Text Permissions」分類下）
5. 捲到頁面最下方，**「GENERATED URL」**（產生的網址）欄位會出現一串 `https://discord.com/oauth2/authorize?...` 的網址。點旁邊的 **「Copy」**。

> 這個網址裡沒有 token，不是機密，但它只用來邀請你自己的 bot，不用轉貼給別人。

### 4-3. 把 bot 邀進你的 Server

1. 把剛剛複製的網址貼到瀏覽器的網址列，按 **Enter**。
2. 出現「新增至伺服器」（Add to Server）畫面，在下拉選單選你**自己建立的那個 Server**（例如 `食物記錄測試`）。
3. 點 **「繼續」**（Continue）。
4. 下一個畫面會列出 bot 要求的權限，確認**只有那四項**（檢視頻道、傳送訊息、讀取訊息歷史、新增反應）。如果多了別的，回到 4-2 檢查勾選。
5. 點 **「授權」**（Authorize）。
6. 可能會要你勾選「我不是機器人」的驗證，照著做完。
7. 看到「已授權」／Authorized 的畫面就完成了。

### 4-4. 回 Discord 確認

1. 回到 Discord，打開你的 Server。
2. 看畫面**最右邊的成員清單**（如果沒有顯示，點右上角的人像圖示）。
3. 你應該會在「離線」（Offline）那一區看到你的 bot 名字（例如 `food-log-bot`），旁邊有一個「BOT」標籤。
   - 現在是離線是正常的，因為 agent 還沒寫、還沒執行。等 agent 開始執行後它才會變成上線（綠點）。
4. 確認 bot 看得到 `# food-log` 頻道：
   - 如果 `# food-log` 是公開頻道（照 `docs/discord-server-setup.md` 的做法），bot 就自動看得到，不需要額外設定。
   - 如果你曾把它改成私人頻道，要對頻道按右鍵 → **「編輯頻道」**（Edit Channel） → **「權限」**（Permissions） → 新增這個 bot，並開啟上面四項權限。

---

## 完成檢查表

- [ ] 我在 Developer Portal 建好了 application，Bot 頁面裡的 **Public Bot 已關閉**
- [ ] **Message Content Intent 已打開，而且按了 Save Changes**
- [ ] 我已經複製 token 並存在安全的地方（**沒有**貼進對話、頻道，也沒有放進專案資料夾）
- [ ] 邀請連結只勾了 `bot` 這個 scope，權限只有 View Channels、Send Messages、Read Message History、Add Reactions
- [ ] 我在自己的 Server 成員清單看到 bot（離線是正常的）

做完之後，你會擁有兩樣之後要填進 `.env` 的東西：

| 設定項目 | 從哪裡來 |
|---|---|
| `DISCORD_TOKEN` | 這份文件第三步拿到的 token（**機密**） |
| `CHANNEL_ID` | `docs/discord-server-setup.md` 第三步拿到的那串數字 |

另外兩項（`CLAUDE_MODEL`、`DATA_DIR`）等寫程式時再一起設定。

---

## 補充：之前已經邀請過 bot，現在要加 Add Reactions

這個權限是後來才加的。如果你**已經**照舊版步驟把 bot 邀進 Server 了，不用重新邀請，兩種方法擇一：

- **方法 A（最快）**：重新跑一次 4-2、4-3，用新產生的網址再「授權」一次，Discord 會把權限更新成四項。
- **方法 B**：在 Discord 開啟 Server → 點 Server 名稱 →「伺服器設定」→「身分組」→ 找到跟 bot 同名的身分組 → 「權限」→ 打開 **「新增反應」**（Add Reactions）→ 儲存。

沒有這個權限的話，agent 仍然會處理照片、回覆結果，只是訊息上不會出現 ⏳（終端機會有一行警告）。

---

## 常見問題

**Q：我打開了 Message Content Intent，之後 agent 還是看不到照片？**
回到 Bot 頁面確認開關是開的，而且有按 **Save Changes**。改完要重新啟動 agent。

**Q：bot 邀進去了，但頻道裡看不到它，也無法回覆？**
通常是頻道權限問題。確認頻道不是私人頻道，或已把 bot 加進私人頻道的權限（見 4-4 第 4 點）。

**Q：授權時沒看到我的 Server 選項？**
你必須在那個 Server 有「管理伺服器」權限。自己建立的 Server 預設就有，請確認瀏覽器登入的是同一個 Discord 帳號。

**Q：token 好像外洩了怎麼辦？**
到 Bot 頁面按 **Reset Token** 重新產生，舊的會立刻失效；然後把新的 token 換進 `.env`。
