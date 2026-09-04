#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* BACKEND_URL = "http://YOUR_COMPUTER_IP:8000/api/sensors/data";
const char* NODE_ID = "NODE_01";

float readVoltage() { return 0.0; } // Replace with calibrated voltage-sensor reading.
float readCurrent() { return 0.0; } // Replace with calibrated current-sensor reading.

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  for (int i = 0; WiFi.status() != WL_CONNECTED && i < 30; i++) delay(500);
}

void setup() { Serial.begin(115200); connectWifi(); }
void loop() {
  connectWifi();
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(BACKEND_URL);
    http.addHeader("Content-Type", "application/json");
    String body = "{\"device_id\":\"" + String(NODE_ID) + "\",\"voltage\":" + String(readVoltage(), 2) + ",\"current\":" + String(readCurrent(), 2) + "}";
    int status = http.POST(body);
    Serial.printf("Telemetry POST status: %d\n", status);
    http.end();
  }
  delay(2000);
}
