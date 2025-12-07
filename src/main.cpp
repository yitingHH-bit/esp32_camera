#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

// ==== WiFi 设置 ====
const char* ssid     = "TP-LINK_697F";
const char* password = "hjc198902165399";

// ==== 后端地址 ====
const char* BACKEND_HOST = "192.168.0.104";  // 这里用你电脑在 ipconfig 看到的 IPv4
const int   BACKEND_PORT = 8000;
const char* BACKEND_PATH = "/status";        // 后端提供聚合接口 /status

void initTFT() {
  pinMode(TFT_BACKLITE, OUTPUT);
  digitalWrite(TFT_BACKLITE, HIGH);

  pinMode(TFT_I2C_POWER, OUTPUT);
  digitalWrite(TFT_I2C_POWER, HIGH);
  delay(10);

  tft.init(135, 240);
  tft.setRotation(3);
  tft.fillScreen(ST77XX_BLACK);
}

// 简单的两个区域：上面显示邮箱，下面显示天气
void drawDashboard(int unread,
                   const char* latestSubject,
                   float temp,
                   const char* weatherDesc) {
  tft.fillScreen(ST77XX_BLACK);

  // 标题
  tft.setCursor(5, 5);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.print("Desk Hub");
  tft.drawFastHLine(0, 20, 240, ST77XX_WHITE);

  // 邮件区域
  tft.setCursor(5, 25);
  tft.setTextColor(ST77XX_CYAN);
  tft.setTextSize(1);
  tft.print("Mail");

  tft.setCursor(5, 40);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.printf("Unread: %d", unread);

  tft.setCursor(5, 65);
  tft.setTextColor(ST77XX_YELLOW);
  tft.setTextSize(1);
  tft.print("Latest:");
  tft.setCursor(5, 78);
  tft.setTextColor(ST77XX_CYAN);
  tft.print(latestSubject);

  // 分隔线
  tft.drawFastHLine(0, 95, 240, ST77XX_BLUE);

  // 天气区域
  tft.setCursor(5, 100);
  tft.setTextColor(ST77XX_GREEN);
  tft.setTextSize(1);
  tft.print("Weather");

  tft.setCursor(5, 115);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.printf("%.1f C", temp);

  tft.setCursor(5, 140);
  tft.setTextColor(ST77XX_MAGENTA);
  tft.setTextSize(1);
  tft.print(weatherDesc);
}

void setup() {
  Serial.begin(115200);
  initTFT();

  tft.setCursor(5, 100);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.print("Connecting WiFi...");

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  tft.fillRect(0, 95, 240, 40, ST77XX_BLACK);
  tft.setCursor(5, 100);
  tft.setTextColor(ST77XX_GREEN);
  tft.print("WiFi OK: ");
  tft.println(WiFi.localIP());
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    // 构造 URL： http://192.168.0.104:8000/status
    String url = String("http://") + BACKEND_HOST + ":" + BACKEND_PORT + BACKEND_PATH;
    Serial.print("Request URL: ");
    Serial.println(url);

    http.begin(url);
    int httpCode = http.GET();
    Serial.print("HTTP code: ");
    Serial.println(httpCode);

    if (httpCode == 200) {
      String payload = http.getString();
      Serial.println("Payload:");
      Serial.println(payload);

      JsonDocument doc;
      DeserializationError error = deserializeJson(doc, payload);
      if (!error) {
        // 根据我们约定的 /status 结构解析
        int unread = doc["email"]["unread"] | 0;
        const char* latestSubject =
            doc["email"]["latest_subject"] | "No mail";

        float temp = doc["weather"]["temp"] | 0.0;
        const char* weatherDesc =
            doc["weather"]["description"] | "N/A";

        drawDashboard(unread, latestSubject, temp, weatherDesc);
      } else {
        Serial.print("JSON error: ");
        Serial.println(error.c_str());
      }
    } else {
      Serial.printf("HTTP error: %d\n", httpCode);
    }

    http.end();
  } else {
    Serial.println("WiFi not connected");
  }

  // 每 30 秒刷新一次
  delay(30000);
}
