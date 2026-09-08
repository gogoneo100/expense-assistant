@echo off
chcp 65001 >nul
echo ============================================================
echo 🌐 智能消費管家 - Cloudflare 公網加密通道啟動器
echo ============================================================
echo.
echo 正在將本機 http://127.0.0.1:8080 映射至全球安全 HTTPS 網址...
echo.
cloudflared tunnel --url http://127.0.0.1:8080
pause
