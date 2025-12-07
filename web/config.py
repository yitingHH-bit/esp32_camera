# config.py

# ---------- 1) Google API（Gmail + Calendar） ----------

# 从 Google Cloud Console 下载的 OAuth 客户端文件
# （我们之前说的 credentials.json）
GOOGLE_CREDENTIALS_FILE = "credentials.json"

# 第一次跑授权脚本（google_auth_setup.py）后生成
GOOGLE_TOKEN_FILE = "token.json"

# 需要的权限：Gmail 只读 + Calendar 只读
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# ---------- 2) Open-Meteo 天气（完全免费，无 Key） ----------

# 你要显示天气的地理位置（这里先用 Kuopio 大概坐标）
OPENMETEO_LAT = 62.9
OPENMETEO_LON = 27.7

# ---------- 3) Notion （以后接 Todo 用，先占位） ----------

# Notion internal integration token（暂时可以先留空或写 "TODO"）
NOTION_API_TOKEN = "secret_xxx"

# 你的 TODO 数据库 ID（暂时占位）
NOTION_TODO_DATABASE_ID = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
