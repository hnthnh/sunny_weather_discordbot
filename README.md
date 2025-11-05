# Discord Weather Bot

Bot thời tiết cho Discord sử dụng OpenWeather và trả kết quả bằng tiếng Việt, hỗ trợ slash commands và cảnh báo định kỳ.

## Yêu cầu
- Python 3.10 trở lên
- Discord bot token (bot cần được mời với scope `bot` + `applications.commands`)
- OpenWeather API key (gói miễn phí là đủ cho nhu cầu cơ bản)

## Cấu hình secrets
1. Sao chép file mẫu và chỉnh sửa:
   ```bash
   cp .env.example .env
   ```
2. Mở `.env` và cập nhật biến `BOT_CONFIG` (JSON một dòng). Ví dụ:
   ```env
   BOT_CONFIG='{"DISCORD_TOKEN":"abc","WEATHER_API_KEY":"xyz","CITY":"Ho Chi Minh","LANG":"vi","UNITS":"metric"}'
   ```
3. Giải thích các khoá:
   - `DISCORD_TOKEN`: token của bot Discord.
   - `WEATHER_API_KEY`: API key của OpenWeather.
   - `CITY`: tên thành phố (ví dụ `Ho Chi Minh`, `Hanoi`, `Tokyo`).
   - `LANG`: ngôn ngữ trả lời (`vi`, `en`, ...).
   - `UNITS`: đơn vị (`metric`, `imperial`, `standard`).
   - Tuỳ chọn `DISCORD_GUILD_ID`: (chuỗi số) giúp slash commands được đồng bộ ngay trong server chỉ định.

> Nếu bạn quen dùng từng biến riêng (`DISCORD_TOKEN=...`, `WEATHER_API_KEY=...`, ...), code vẫn hỗ trợ backward compatibility.

## Cài đặt (macOS / Linux)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

## Cài đặt trên Windows
- Nhấn đúp `run_bot.bat` để tự động:
  - Tạo virtualenv `.venv` nếu chưa có
  - Cài đặt dependencies
  - Chạy `python bot.py`
- Hoặc thao tác bằng Command Prompt/PowerShell:
  ```bat
  python -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt
  python bot.py
  ```

## Slash commands & cảnh báo
- Bot cung cấp các lệnh `/temp`, `/rain`, `/forecast`.
- Khi bot online, slash commands sẽ được Discord đăng ký tự động (mất vài giây nếu không khai báo `DISCORD_GUILD_ID`).
- Tạo channel tên `weather-alerts` để nhận cảnh báo 6 giờ một lần.

## Lưu ý
- `.env`, `.venv/`, file biên dịch tạm (`*.pyc`) đã nằm trong `.gitignore` để tránh lộ secrets.
- `requirements.txt` bao gồm `audioop-lts` để bảo đảm hoạt động trên Python 3.13.
# sunny_weather_discordbot
