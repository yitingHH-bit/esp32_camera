from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config

# 如果已经安装了 google 的库，就可以用真正的 Gmail + Calendar
# 没装的话，先在 requirements 里注释掉这些 import 也可以。
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


app = FastAPI()

# 允许局域网内 ESP32 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#  Google 通用认证工具
# ============================================================

def get_google_creds() -> Credentials:
    """
    从 token.json / credentials.json 获取可用的 Credentials。
    如果 token 过期且有 refresh_token，则自动刷新。
    """
    creds: Credentials | None = None

    if os.path.exists(config.GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            config.GOOGLE_TOKEN_FILE, config.GOOGLE_SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 自动刷新
            creds.refresh(Request())
        else:
            # 一般只在第一次、或者 token.json 丢失时需要走浏览器
            flow = InstalledAppFlow.from_client_secrets_file(
                config.GOOGLE_CREDENTIALS_FILE, config.GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(config.GOOGLE_TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


# ============================================================
#  1) Gmail：未读 + 最新主题
# ============================================================

def get_mail_status() -> Dict[str, Any]:
    """
    从 Gmail API 获取：
    - 未读邮件数量
    - 最新一封未读邮件的主题
    """
    try:
        creds = get_google_creds()
        service = build("gmail", "v1", credentials=creds)

        # 查未读邮件（最多 10 个，看个大概）
        res = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=10,
        ).execute()

        messages = res.get("messages", [])
        unread_count = res.get("resultSizeEstimate", 0)

        latest_subject = "No unread mail"

        if messages:
            msg_id = messages[0]["id"]
            msg = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["Subject"],
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            for h in headers:
                if h.get("name") == "Subject":
                    latest_subject = h.get("value", latest_subject)
                    break

        return {
            "unread": unread_count,
            "latest_subject": latest_subject,
        }

    except Exception as e:
        # 失败时返回占位值，ESP32 那边会显示错误字符串
        return {
            "unread": -1,
            "latest_subject": f"Mail error: {e.__class__.__name__}",
        }


# ============================================================
#  2) Google Calendar：最近一个事件
# ============================================================

def get_next_calendar_event() -> Dict[str, Any]:
    """
    从 Google Calendar 获取最近一条未来事件：
    - summary: 标题
    - start:   开始时间（ISO / date）
    - location: 地点
    """
    try:
        creds = get_google_creds()
        service = build("calendar", "v3", credentials=creds)

        now = datetime.now(timezone.utc).isoformat()

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=1,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        if not events:
            return {
                "summary": "No upcoming events",
                "start": "",
                "location": "",
            }

        event = events[0]
        summary = event.get("summary", "(no title)")
        start = event["start"].get("dateTime") or event["start"].get("date")
        location = event.get("location", "")

        return {
            "summary": summary,
            "start": start,
            "location": location,
        }

    except Exception as e:
        return {
            "summary": f"Cal error: {e.__class__.__name__}",
            "start": "",
            "location": "",
        }


# ============================================================
#  3) 天气：Open-Meteo（完全免费，无需 API key）
# ============================================================

def _weather_code_to_text(code: int | None) -> str:
    """把 Open-Meteo 的 weather_code 映射成人类可读文字。"""
    if code is None:
        return "Unknown"
    if code == 0:
        return "Clear sky"
    if code in (1, 2):
        return "Partly cloudy"
    if code == 3:
        return "Overcast"
    if 51 <= code <= 57:
        return "Drizzle"
    if 61 <= code <= 67:
        return "Rain"
    if 71 <= code <= 77:
        return "Snow"
    if 80 <= code <= 82:
        return "Rain showers"
    if 95 <= code <= 99:
        return "Thunderstorm"
    return f"Code {code}"


def get_weather() -> Dict[str, Any]:
    """
    使用 Open-Meteo 当前天气 API，不需要 API key。
    返回:
      { "temp": float | None, "description": str }
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": config.OPENMETEO_LAT,
            "longitude": config.OPENMETEO_LON,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
        }

        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            return {
                "temp": None,
                "description": f"Wea HTTP error: {r.status_code}",
            }

        data = r.json()
        current = data.get("current", {})
        temp = current.get("temperature_2m", None)
        code = current.get("weather_code", None)

        desc = _weather_code_to_text(code)

        return {
            "temp": temp,
            "description": desc,
        }

    except Exception as e:
        return {
            "temp": None,
            "description": f"Wea error: {e.__class__.__name__}",
        }


# ============================================================
#  4) Todos：先用假数据占位（以后接 Notion）
# ============================================================

def get_todos() -> Dict[str, Any]:
    """
    目前用假数据占位。
    以后可以用 config.NOTION_API_TOKEN + NOTION_TODO_DATABASE_ID
    去调用 Notion API。
    """
    try:
        # TODO: 以后换成真正的 Notion 查询
        return {
            "count": 2,
            "top": "Finish ESP32 dashboard",
        }
    except Exception as e:
        return {
            "count": -1,
            "top": f"Todo error: {e.__class__.__name__}",
        }


# ============================================================
#  给 ESP32 用的聚合接口
# ============================================================

@app.get("/status")
def get_status() -> Dict[str, Any]:
    """
    聚合所有模块数据：
    - email
    - calendar
    - weather
    - todos
    结构和你 ESP32 端解析的是一一对应的。
    """
    return {
        "email": get_mail_status(),
        "calendar": get_next_calendar_event(),
        "weather": get_weather(),
        "todos": get_todos(),
    }


if __name__ == "__main__":
    import uvicorn
    # 0.0.0.0 方便局域网访问；ESP32 用 http://<你的电脑IP>:8000/status
    uvicorn.run(app, host="0.0.0.0", port=8000)
