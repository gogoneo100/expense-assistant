# 📱 手機瀏覽與雲端存取完整指南 (Mobile & Cloud Guide)

想隨時隨地用手機查看報表、隨手記帳，或將系統放到雲端 24 小時不間斷運作，有以下 **3 種最佳解決方案**，您可以根據使用情境自由選擇：

---

## 方案一：啟用內建 Telegram 機器人 (最簡單！手機隨手秒記)

系統已經**完整內建 Telegram 雙向記帳機器人**，不需架設任何網站伺服器，手機也不用開瀏覽器！

### 快速設定步驟：
1. 打開手機 Telegram，搜尋 `@BotFather`，發送 `/newbot`，依提示為機器人取名，取得一組 `HTTP API Token`。
2. 在電腦開啟消費管家網頁（[http://127.0.0.1:8080](http://127.0.0.1:8080)），點擊右上角「**設定**」。
3. 勾選「**啟用 Telegram 機器人推播與記帳**」，貼上剛剛取得的 Token，點擊儲存。
4. 在手機 Telegram 找到您的機器人，發送 `/start` 即可完成綁定！

### 手機日常使用：
- **隨手記帳**：在外吃完飯直接傳「`午餐 130`」或「`計程車 220 交通`」，機器人立即入庫並回報今日累計花費。
- **隨時查帳**：輸入「`/today`」立刻列出今日所有信用卡刷卡與手動花費清單。
- **每日提醒**：每晚 21:30 自動將整理好的消費戰報推播到您手機。

---

## 方案二：Cloudflare Tunnel 免費公網通道 (推薦！手機看精美儀表板)

如果您希望在手機上瀏覽完整的圖表、圓餅圖與明細流水帳，可以使用 Cloudflare 提供的免費安全通道（Zero Trust Tunnel），**免固定 IP、免轉發 Port，直接擁有永久安全的 HTTPS 網址**。

### 操作步驟：
1. 下載 Cloudflare 官方通道工具 [cloudflared Windows 版](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)（或透過 PowerShell 快速執行）：
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. 啟動通道（將本地 8080 映射至公網）：
   ```bash
   cloudflared tunnel --url http://localhost:8080
   ```
3. 命令列會顯示一組專屬 HTTPS 網址（例如 `https://random-words.trycloudflare.com`）。
4. 用手機開啟該網址，即可在外面隨時連回家中電腦查看與記帳！

### 📲 手機「加入主畫面」變身獨立 App (PWA)：
本系統已內建 PWA 支援：
- **iPhone (Safari)**：點擊底部的「分享」按鈕 ➔ 選擇「**加入主畫面**」。
- **Android (Chrome)**：點擊右上角三個點 ➔ 選擇「**新增至主畫面 / 安裝應用程式**」。
- 桌面就會出現「**消費管家**」圖示，點開即是無網址列的全螢幕原生 App！

---

## 方案三：部署至免費雲端平台 (電腦免開機，24hr 全自動運作)

若希望家裡電腦關機後，系統仍然能在每天晚上定時爬取 Gmail 刷卡通知並推播提醒，可部署至各大雲端平台（如 **Zeabur**、**Render**、**Fly.io** 或自己的 NAS / VPS）。

專案已準備好 [`Dockerfile`](file:///C:/Users/gogon/.gemini/antigravity/scratch/expense-assistant/Dockerfile) 與 [`docker-compose.yml`](file:///C:/Users/gogon/.gemini/antigravity/scratch/expense-assistant/docker-compose.yml)。

### 推薦推薦平台：Zeabur (繁體中文介面，支援台灣本地)
1. 前往 [zeabur.com](https://zeabur.com) 註冊免費帳號。
2. 將本專案資料夾上傳至您的 GitHub 私人儲存庫（Private Repo）。
3. 在 Zeabur 點選「Create Project」➔ 選擇您的 GitHub Repo。
4. 系統會自動辨識 Dockerfile 並完成建置。
5. 在 Zeabur 後台建立一個「Persistent Volume（持久化磁碟）」，掛載路徑填寫 `/app/data`（確保 SQLite 資料庫不會因重啟遺失）。
6. Zeabur 會自動分配免費 HTTPS 網域（例如 `https://your-expense.zeabur.app`）。
7. 手機直接打開該網址，永不關機、隨時記帳！

---

## 💡 三種方案比較表

| 方案 | 難易度 | 電腦需開機？ | 手機體驗 | 推薦程度 |
| :--- | :---: | :---: | :--- | :---: |
| **方案一：Telegram 機器人** | ⭐ (1分鐘) | 是 (除非部署雲端) | 極佳，隨手打字秒記、自動收到通知 | 🌟🌟🌟🌟🌟 (最實用) |
| **方案二：Cloudflare Tunnel** | ⭐⭐ (3分鐘) | 是 | 完整網頁儀表板，可加到手機主畫面當 App | 🌟🌟🌟🌟 |
| **方案三：雲端託管 (Zeabur/Render)** | ⭐⭐⭐ (10分鐘) | **否 (24hr 自動)** | 完美獨立運作，電腦完全不用開機 | 🌟🌟🌟🌟🌟 (最省心) |
