# 💳 智能消費管家 (Daily Gmail & Expense Assistant)

一套為個人打造的智慧記帳與消費彙整系統：**每日自動整理 Gmail 信用卡刷卡通知、智慧分類、支援其他費用隨手申報，並於每晚定時產生消費戰報與貼心提醒。**

---

## ✨ 核心特色

1. **Gmail 信用卡刷卡自動整理**
   - 支援台灣各大主流銀行（國泰世華、中國信託、玉山銀行、台北富邦、台新銀行、聯邦、星展等）之即時消費通知與授權確認信件。
   - 內建智慧通用正則回退機制，即便是其他銀行或國外信用卡消費通知亦能自動提取金額、特店名稱、卡號與消費時間。
   - 具備重複信件防重機制（以 Message-ID 及交易特徵去重，絕不重複計帳）。

2. **多維度費用分類 (智慧商家分類庫)**
   - 內建台灣常見商家資料庫（飲食、交通、購物、娛樂、居家帳單、醫療保健、學習教育等）。
   - 支援動態學習與自訂規則：可隨時在介面上新增「商家關鍵字 → 目標分類」映射。

3. **隨手費用申報 (非信用卡花費)**
   - **自然語言智慧記帳**：直接輸入 `午餐 120`、`計程車 250 交通`、`全聯採買 540 購物`，系統自動解析金額與項目。
   - **標準表單記帳**：提供金額、日期、分類、備註等細項快速錄入。

4. **每日彙整與貼心提醒 (戰報推播)**
   - 每日定時自動彙整今日總支出、信用卡 vs 手動申報比例、分類佔比排行榜。
   - 支援 **Telegram Bot** 雙向互動：晚上定時推播日報，亦可在聊天視窗直接傳文字記帳或輸入 `/today` 查詢花費。
   - 介面提供一鍵預覽、複製與即時手動推播。

5. **現代視覺化儀表板**
   - 包含今日總覽、本月累計、動態甜甜圈佔比圖、交易流水帳多維度過濾（來源、分類、關鍵字搜尋）。

---

## 🚀 快速開始

### 1. 安裝與啟動

本專案無需複雜設定，使用 Python 3.10+ 即可運行：

```bash
# 進入專案目錄
cd expense-assistant

# 安裝相依套件 (若已安裝可略過)
py -m pip install -r requirements.txt

# 啟動系統
py run.py
```

啟動後，開啟瀏覽器造訪控制台：
👉 **`http://127.0.0.1:8080`**

---

## ⚙️ Gmail 應用程式密碼設定教學 (3 分鐘完成)

為了讓系統能安全讀取 Gmail 內的刷卡通知信件，請依照以下步驟取得「應用程式密碼」：

1. 前往 Google 帳號管理：[https://myaccount.google.com/security](https://myaccount.google.com/security)
2. 確認已開啟 **「兩步驟驗證」**。
3. 在搜尋列搜尋 **「應用程式密碼」** (或造訪 [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))。
4. 應用程式名稱可自訂（例如：`消費管家`），點擊 **「建立」**。
5. Google 會顯示一組 **16 位英文字母密碼**（例如：`abcd efgh ijkl mnop`）。
6. 開啟系統網頁右上角「**設定**」，填入您的 Gmail 帳號與這組 16 位密碼並儲存即可！

---

## 🤖 Telegram 機器人推播與隨手記帳 (選配)

若希望在手機 Telegram 直接收到每日提醒與隨手打字記帳：

1. 在 Telegram 搜尋 `@BotFather`，發送 `/newbot` 依提示建立一個屬於您的專屬機器人。
2. 複製取得的 `HTTP API Token`。
3. 開啟網頁右上角「**設定**」，開啟 Telegram 功能並貼上 Token。
4. 在 Telegram 找到您的機器人，發送 `/start` 即可完成綁定！

### Telegram 記帳指令範例：
- 隨手記帳：傳送 `晚餐 250` 或 `高鐵 1490 交通`
- 查詢今日：輸入 `/today`
- 觸發抓信：輸入 `/sync`

---

## 📱 手機瀏覽與雲端存取指南

想在手機上查看圖表、隨手記帳或 24 小時雲端全自動運作？
請參閱詳細教學：👉 **[`CLOUD_MOBILE_GUIDE.md`](file:///C:/Users/gogon/.gemini/antigravity/scratch/expense-assistant/CLOUD_MOBILE_GUIDE.md)**

- **方案 A（最簡單）**：開啟內建 Telegram 機器人，手機直接打字秒記帳與查帳。
- **方案 B（最推薦）**：透過 Cloudflare Tunnel 免費公網通道，將網頁「加入手機主畫面」當作原生 App。
- **方案 C（免開電腦）**：利用專案內附的 `Dockerfile` 部署至免費雲端平台（如 Zeabur 或 Render）。

---

## 📁 專案目錄結構

```text
expense-assistant/
├── app/
│   ├── config.py             # 系統全域設定與持久化
│   ├── database.py           # SQLite 核心、交易 CRUD 與統計函數
│   ├── models.py             # Transaction, Category, CategoryRule 模型
│   ├── classifier.py         # 智能分類與自然語言記帳解析
│   ├── mail_service.py       # Gmail IMAP 抓取、解析、去重與示範資料
│   ├── reminder_service.py   # 每日日報戰報產製與 Telegram 推播
│   ├── bot_service.py        # Telegram Bot Long Polling 服務
│   ├── scheduler.py          # 定時任務排程器 (定時抓信 + 每日提醒)
│   └── parsers/
│       ├── base.py           # 基礎解析器介面
│       └── banks.py          # 國泰、中信、玉山、富邦、台新與通用解析器
├── web/
│   ├── server.py             # FastAPI 後端 API 服務
│   └── static/
│       ├── index.html        # 現代視覺化響應式介面
│       └── app.js            # 前端 Chart.js 圖表與非同步操作邏輯
├── tests/                    # 完整單元測試與整合測試 (10 個測試全數通過)
├── run.py                    # 一鍵啟動入口腳本
└── requirements.txt          # 相依套件清單
```
