import json
import os
from dataclasses import dataclass
from typing import Any, Dict

import discord
from discord.ext import commands, tasks
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    token: str
    weather_api_key: str
    city: str
    units: str
    lang: str
    guild_id: int | None = None


def _coerce_int(raw: Any, *, field_name: str) -> int | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a numeric ID.") from exc
    raise ValueError(f"{field_name} must be a string of digits or an integer.")


def load_config() -> Config:
    raw_config = os.getenv("BOT_CONFIG")
    payload: Dict[str, Any] = {}

    if raw_config:
        try:
            payload = json.loads(raw_config)
        except json.JSONDecodeError as exc:
            raise ValueError("BOT_CONFIG must contain valid JSON.") from exc

    token = payload.get("DISCORD_TOKEN") or os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Missing DISCORD_TOKEN in configuration.")

    api_key = payload.get("WEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise ValueError("Missing WEATHER_API_KEY in configuration.")

    city = payload.get("CITY") or os.getenv("CITY") or "Ho Chi Minh"
    units = payload.get("UNITS") or os.getenv("UNITS") or "metric"
    lang = payload.get("LANG") or os.getenv("LANG") or "vi"

    guild_raw = payload.get("DISCORD_GUILD_ID") or os.getenv("DISCORD_GUILD_ID")
    guild_id = _coerce_int(guild_raw, field_name="DISCORD_GUILD_ID") if guild_raw else None

    return Config(
        token=token,
        weather_api_key=api_key,
        city=city,
        units=units,
        lang=lang,
        guild_id=guild_id,
    )


CONFIG = load_config()

intents = discord.Intents.default()

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

REQUEST_TIMEOUT = 10
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


def fetch_json(endpoint: str, *, params: Dict[str, Any]) -> dict[str, Any]:
    url = f"{OPENWEATHER_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError("Không thể lấy dữ liệu từ OpenWeather.") from exc
    return response.json()


def get_weather() -> dict[str, Any]:
    return fetch_json(
        "/weather",
        params={
            "q": CONFIG.city,
            "appid": CONFIG.weather_api_key,
            "units": CONFIG.units,
            "lang": CONFIG.lang,
        },
    )


def get_forecast() -> dict[str, Any]:
    return fetch_json(
        "/forecast",
        params={
            "q": CONFIG.city,
            "appid": CONFIG.weather_api_key,
            "units": CONFIG.units,
            "lang": CONFIG.lang,
        },
    )

def ensure_success(data: dict[str, Any]) -> None:
    code = data.get("cod")
    if code is not None and str(code) != "200":
        message = data.get("message", "OpenWeather trả về lỗi không xác định.")
        raise RuntimeError(message)


def format_current_weather_message(payload: dict[str, Any]) -> str:
    weather = payload.get("weather", [{}])[0]
    main = payload.get("main", {})
    wind = payload.get("wind", {})
    clouds = payload.get("clouds", {})

    desc = weather.get("description", "Không rõ").capitalize()
    current_temp = main.get("temp")
    feels_like = main.get("feels_like")
    humidity = main.get("humidity")
    wind_speed = wind.get("speed")
    cloudiness = clouds.get("all")

    lines = [f"**Thời tiết hiện tại tại __{CONFIG.city}__**", f"> 🌤️ **Trạng thái:** {desc}"]

    if isinstance(current_temp, (int, float)):
        lines.append(f"> 🌡️ **Nhiệt độ:** `{current_temp:.1f}°C`")
    if isinstance(feels_like, (int, float)):
        lines.append(f"> 🤔 **Cảm giác như:** `{feels_like:.1f}°C`")
    if isinstance(humidity, (int, float)):
        lines.append(f"> 💧 **Độ ẩm:** `{humidity}%`")
    if isinstance(wind_speed, (int, float)):
        lines.append(f"> 🌬️ **Gió:** `{wind_speed:.1f} m/s`")
    if isinstance(cloudiness, (int, float)):
        lines.append(f"> ☁️ **Mây phủ:** `{cloudiness}%`")

    lines.append("> 🔎 Dữ liệu từ OpenWeather")
    return "\n".join(lines)


def format_rain_message(payload: dict[str, Any]) -> str:
    rain_data = payload.get("rain", {})
    weather = payload.get("weather", [{}])[0]

    rain_1h = rain_data.get("1h")
    rain_3h = rain_data.get("3h")
    desc = weather.get("description", "Không rõ").capitalize()

    lines = [f"**Lượng mưa gần đây tại __{CONFIG.city}__**"]

    if isinstance(rain_1h, (int, float)):
        lines.append(f"> ☔ **Trong 1 giờ qua:** `{rain_1h:.1f} mm`")
    elif isinstance(rain_3h, (int, float)):
        lines.append(f"> ☔ **Trong 3 giờ qua:** `{rain_3h:.1f} mm`")
    else:
        lines.append("> ☔ Không ghi nhận lượng mưa trong 3 giờ gần nhất.")

    lines.append(f"> 🌤️ **Trạng thái hiện tại:** {desc}")
    lines.append("> 🔎 Dữ liệu từ OpenWeather")
    return "\n".join(lines)


def format_forecast_message(entries: list[dict[str, Any]]) -> str:
    lines = [f"**📅 Dự báo 6 giờ tới cho __{CONFIG.city}__**"]

    for item in entries:
        dt = item.get("dt")
        time_label = datetime.fromtimestamp(dt).strftime("%H:%M") if dt else "--:--"
        main = item.get("main", {})
        weather = item.get("weather", [{}])[0]
        wind = item.get("wind", {})

        desc = weather.get("description", "Không rõ").capitalize()
        temp = main.get("temp")
        feels_like = main.get("feels_like")
        rain = item.get("rain", {}).get("3h")
        pop = item.get("pop")
        wind_speed = wind.get("speed")

        extras: list[str] = []
        if isinstance(temp, (int, float)):
            extras.append(f"🌡️ {temp:.1f}°C")
        if isinstance(feels_like, (int, float)):
            extras.append(f"🤔 cảm giác {feels_like:.1f}°C")
        if isinstance(rain, (int, float)) and rain > 0:
            extras.append(f"☔ {rain:.1f} mm/3h")
        if isinstance(pop, (int, float)):
            extras.append(f"💧 {int(pop * 100)}% mưa")
        if isinstance(wind_speed, (int, float)):
            extras.append(f"🌬️ {wind_speed:.1f} m/s")

        detail = " • ".join(extras)
        if detail:
            lines.append(f"> 🕒 `{time_label}` • {desc} • {detail}")
        else:
            lines.append(f"> 🕒 `{time_label}` • {desc}")

    lines.append("> 🔎 Dữ liệu từ OpenWeather")
    return "\n".join(lines)


def format_alert_message(payload: dict[str, Any]) -> str:
    weather = payload.get("weather", [{}])[0]
    main = payload.get("main", {})
    wind = payload.get("wind", {})

    desc = weather.get("description", "Không rõ").capitalize()
    temp = main.get("temp")
    feels_like = main.get("feels_like")
    rain = payload.get("rain", {}).get("3h")
    pop = payload.get("pop")
    wind_speed = wind.get("speed")

    lines = [f"**⚠️ Cảnh báo 6 giờ tới cho __{CONFIG.city}__**", f"> 🌤️ **Dự báo:** {desc}"]

    if isinstance(temp, (int, float)):
        lines.append(f"> 🌡️ **Nhiệt độ:** `{temp:.1f}°C`")
    if isinstance(feels_like, (int, float)):
        lines.append(f"> 🤔 **Cảm giác như:** `{feels_like:.1f}°C`")
    if isinstance(rain, (int, float)):
        lines.append(f"> ☔ **Lượng mưa dự kiến:** `{rain:.1f} mm/3h`")
    if isinstance(pop, (int, float)):
        lines.append(f"> 💧 **Xác suất mưa:** `{int(pop * 100)}%`")
    if isinstance(wind_speed, (int, float)):
        lines.append(f"> 🌬️ **Gió trung bình:** `{wind_speed:.1f} m/s`")

    lines.append("> 🔔 Hãy chuẩn bị kế hoạch phù hợp!")
    return "\n".join(lines)


async def send_interaction_response(interaction: discord.Interaction, message: str, *, ephemeral: bool = False) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(message, ephemeral=ephemeral)


# ========== LỆNH SLASH ==========
@bot.tree.command(name="temp", description="Xem thời tiết hiện tại")
async def temp(interaction: discord.Interaction):
    try:
        data = get_weather()
        ensure_success(data)
    except RuntimeError as error:
        await send_interaction_response(interaction, f"⚠️ Không thể lấy dữ liệu thời tiết: {error}", ephemeral=True)
        return

    await send_interaction_response(interaction, format_current_weather_message(data))


@bot.tree.command(name="rain", description="Kiểm tra lượng mưa gần đây")
async def rain(interaction: discord.Interaction):
    try:
        data = get_weather()
        ensure_success(data)
    except RuntimeError as error:
        await send_interaction_response(interaction, f"⚠️ Không thể lấy dữ liệu lượng mưa: {error}", ephemeral=True)
        return

    await send_interaction_response(interaction, format_rain_message(data))


@bot.tree.command(name="forecast", description="Xem dự báo 6 giờ tới")
async def forecast(interaction: discord.Interaction):
    try:
        data = get_forecast()
        ensure_success(data)
    except RuntimeError as error:
        await send_interaction_response(interaction, f"⚠️ Không thể lấy dữ liệu dự báo: {error}", ephemeral=True)
        return

    entries = data.get("list", [])[:3]
    if not entries:
        await send_interaction_response(interaction, "Không có dữ liệu dự báo vào lúc này.", ephemeral=True)
        return

    await send_interaction_response(interaction, format_forecast_message(entries))


# ========== CẢNH BÁO 6 TIẾNG MỘT LẦN ==========
@tasks.loop(hours=6)
async def weather_alert():
    channel = discord.utils.get(bot.get_all_channels(), name="weather-alerts")
    if not channel:
        return

    try:
        data = get_forecast()
        ensure_success(data)
    except RuntimeError:
        return

    entries = data.get("list", [])
    if not entries:
        return

    message = format_alert_message(entries[0])
    await channel.send(message)

@bot.event
async def on_ready():
    if CONFIG.guild_id:
        guild = discord.Object(id=CONFIG.guild_id)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()

    print(f"✅ Bot {bot.user} đã sẵn sàng!")

    if not weather_alert.is_running():
        weather_alert.start()
@tasks.loop(hours=6)
async def weather_alert():
    channel = discord.utils.get(bot.get_all_channels(), name="weather-alerts")
    if not channel:
        return
    data = get_forecast()
    desc = data["list"][0]["weather"][0]["description"].capitalize()
    temp = data["list"][0]["main"]["temp"]
    rain = data["list"][0].get("rain", {}).get("3h", 0)
    msg = f"⚠️ Cảnh báo thời tiết trong 6h tới:\n{desc}, {temp}°C, mưa {rain} mm"
    await channel.send(msg)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} đã sẵn sàng!")
    weather_alert.start()
bot.run(CONFIG.token)
