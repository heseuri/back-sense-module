// XIAO ESP32-S3 Sense OV2640 / Arduino-ESP32 3.x
// PSRAM: OPI, USB CDC On Boot: Enabled, Flash Size: 8MB
// One viewer at a time. Pi URL: http://192.168.50.2/stream
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_camera.h"
#include "esp_http_server.h"

static httpd_handle_t server = nullptr;
static WiFiUDP radarUdp;
static HardwareSerial radarSerial(1);
static constexpr int RADAR_RX = 44;  // XIAO D7 <- radar TX
static constexpr int RADAR_TX = 43;  // XIAO D6 -> radar RX
static constexpr uint16_t RADAR_PORT = 5005;
static IPAddress piIP(192, 168, 50, 1);
static const char* MODULE_ID = "left"; // right module: "right"
static volatile bool paused = false;
static volatile bool stopped = false; // x: stopped until reset
static bool udpReady = false;
static String radarLine;
static uint32_t radarLastSeen = 0;
static uint32_t radarLastSent = 0;
static uint32_t radarSeq = 0;
static uint32_t radarValidLines = 0;
static bool radarDetected = false;
static float radarDistance = 0;
static float radarSpeed = 0;
static long radarEnergy = 0;

static void startRadar() {
  radarSerial.begin(9600, SERIAL_8N1, RADAR_RX, RADAR_TX);
  delay(150);
  radarSerial.print("sensorStop\r\n");
  delay(150);
  radarSerial.print("setRunApp 1\r\n"); // distance/speed mode
  delay(150);
  radarSerial.print("sensorStart\r\n");
  Serial.println("[RADAR] UART 9600, speed/distance mode requested");
}

static void pollRadar() {
  while (radarSerial.available()) {
    char c = (char)radarSerial.read();
    if (c == '\n') {
      radarLine.trim();
      if (radarLine.startsWith("$DFDMD,")) {
        // $DFDMD,<count>,<target>,<distance>,<speed>,<energy>, ,*
        int count = -1;
        int target = 0;
        float distance = 0, speed = 0;
        long energy = 0;
        if (sscanf(radarLine.c_str(), "$DFDMD,%d", &count) == 1 && count == 0) {
          radarDetected = false;
          radarLastSeen = millis();
          radarValidLines++;
        } else if (sscanf(radarLine.c_str(), "$DFDMD,%d,%d,%f,%f,%ld",
                          &count, &target, &distance, &speed, &energy) == 5
                   && count > 0 && distance >= 0 && distance <= 25) {
          radarDetected = true;
          radarDistance = distance;
          radarSpeed = speed;
          radarEnergy = energy;
          radarLastSeen = millis();
          radarValidLines++;
        }
      }
      radarLine = "";
    } else if (c != '\r') {
      if (radarLine.length() < 180) radarLine += c;
      else radarLine = "";
    }
  }
}

static void sendRadar() {
  if (!udpReady || paused || stopped || WiFi.status() != WL_CONNECTED) return;
  const uint32_t now = millis();
  if (now - radarLastSent < 200) return;
  radarLastSent = now;
  const bool valid = radarValidLines && (now - radarLastSeen < 1500);
  const bool detected = valid && radarDetected;
  char payload[256];
  snprintf(payload, sizeof(payload),
     "{\"module\":\"%s\",\"seq\":%lu,\"timestamp_ms\":%lu,"
     "\"valid\":%s,\"detected\":%s,\"distance_m\":%.3f,"
     "\"speed_mps\":%.3f,\"energy\":%ld}",
     MODULE_ID, (unsigned long)radarSeq++, (unsigned long)now,
     valid ? "true" : "false", detected ? "true" : "false",
     detected ? radarDistance : 0.0f, detected ? radarSpeed : 0.0f,
     detected ? radarEnergy : 0L);
  radarUdp.beginPacket(piIP, RADAR_PORT);
  radarUdp.write((const uint8_t*)payload, strlen(payload));
  radarUdp.endPacket();
}

static void serialCommands() {
  while (Serial.available()) {
    const char c = (char)Serial.read();
    if (c == 'p' || c == 'P') {
      if (!stopped) { paused = true; Serial.println("[CTRL] PAUSED (stream + radar UDP)"); }
    } else if (c == 'r' || c == 'R') {
      if (!stopped) { paused = false; Serial.println("[CTRL] RESUMED"); }
    } else if (c == 'x' || c == 'X') {
      stopped = true;
      paused = true;
      Serial.println("[CTRL] STOPPED. Press RESET to restart; MCU is still powered.");
    }
  }
}

static bool networkConfigured = false;
static bool wasConnected = false;
static uint32_t lastRetry = 0;
static const char *SSID = "Pi5_Capstone";
static const char *PASS = "Capstone1234";

static esp_err_t indexHandler(httpd_req_t *req) {
  const char *html =
    "<!doctype html><meta name='viewport' "
    "content='width=device-width,initial-scale=1'>"
    "<title>ESP32 Camera Test</title>"
    "<h2>ESP32 Camera Test</h2>"
    "<img src='/stream' style='max-width:100%'>";
  httpd_resp_set_type(req, "text/html; charset=utf-8");
  return httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t streamHandler(httpd_req_t *req) {
  esp_err_t res = httpd_resp_set_type(req,
    "multipart/x-mixed-replace;boundary=frame");
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  Serial.println("[STREAM] Client connected");
  while (!paused && !stopped && WiFi.status() == WL_CONNECTED) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[FRAME] STREAM FAIL");
      return ESP_FAIL;
    }
    char head[128];
    int n = snprintf(head, sizeof(head),
      "--frame\r\nContent-Type: image/jpeg\r\n"
      "Content-Length: %u\r\n\r\n", (unsigned)fb->len);
    res = httpd_resp_send_chunk(req, head, n);
    if (res == ESP_OK)
      res = httpd_resp_send_chunk(req,
        (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (res == ESP_OK)
      res = httpd_resp_send_chunk(req, "\r\n", 2);
    if (res != ESP_OK) return res;
    delay(30);
  }
  Serial.println("[STREAM] Stopped or paused");
  return ESP_OK;
}

static bool startServer() {
  httpd_config_t hc = HTTPD_DEFAULT_CONFIG();
  hc.server_port = 80;
  hc.stack_size = 8192;
  hc.send_wait_timeout = 5;
  if (httpd_start(&server, &hc) != ESP_OK) return false;
  httpd_uri_t root = {};
  root.uri = "/";
  root.method = HTTP_GET;
  root.handler = indexHandler;
  httpd_uri_t stream = {};
  stream.uri = "/stream";
  stream.method = HTTP_GET;
  stream.handler = streamHandler;
  if (httpd_register_uri_handler(server, &root) != ESP_OK ||
      httpd_register_uri_handler(server, &stream) != ESP_OK) {
    httpd_stop(server);
    server = nullptr;
    return false;
  }
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n=== ESP32-S3 Camera Test ===");
  if (!psramFound()) {
    Serial.println("[PSRAM] NOT FOUND - select OPI PSRAM");
    return;
  }
  Serial.printf("[PSRAM] OK bytes=%u\n",
                (unsigned)ESP.getPsramSize());
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 15; c.pin_d1 = 17;
  c.pin_d2 = 18; c.pin_d3 = 16;
  c.pin_d4 = 14; c.pin_d5 = 12;
  c.pin_d6 = 11; c.pin_d7 = 48;
  c.pin_xclk = 10; c.pin_pclk = 13;
  c.pin_vsync = 38; c.pin_href = 47;
  c.pin_sccb_sda = 40; c.pin_sccb_scl = 39;
  c.pin_pwdn = -1; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_VGA;
  c.jpeg_quality = 12;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("[CAMERA] INIT FAIL 0x%x\n", err);
    return;
  }
  sensor_t *s = esp_camera_sensor_get();
  Serial.printf("[CAMERA] INIT OK PID=0x%02x\n",
                s ? s->id.PID : 0);
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[FRAME] FAIL");
    return;
  }
  Serial.printf("[FRAME] OK bytes=%u\n", (unsigned)fb->len);
  esp_camera_fb_return(fb);

  startRadar();
  Serial.println("[CTRL] Send p = pause, r = resume, x = stop until RESET");

  // Pi hotspot: 192.168.50.1, ESP32: 192.168.50.2.
  // Both devices use fixed addresses; no DHCP is needed.
  WiFi.mode(WIFI_STA);
  IPAddress local(192, 168, 50, 2);
  IPAddress gateway(192, 168, 50, 1);
  IPAddress mask(255, 255, 255, 0);
  if (!WiFi.config(local, gateway, mask)) {
    Serial.println("[WIFI] Static IP configuration failed");
    return;
  }
  WiFi.setAutoReconnect(true);
  WiFi.setSleep(false);

  WiFi.begin(SSID, PASS);
  networkConfigured = true;
  lastRetry = millis();
  Serial.printf("[WIFI] Connecting to %s ...\n", SSID);
}

void loop() {
  serialCommands();
  pollRadar();
  if (stopped) { delay(25); return; }
  if (!networkConfigured) {
    delay(1000);
    return;
  }
  bool connected = WiFi.status() == WL_CONNECTED;
  if (!connected) {
    if (wasConnected) Serial.println("[WIFI] Disconnected");
    wasConnected = false;
    if (millis() - lastRetry >= 10000) {
      lastRetry = millis();
      Serial.println("[WIFI] Retrying hotspot connection ...");
      WiFi.reconnect();
    }
    delay(100);
    return;
  }
  if (!wasConnected) {
    wasConnected = true;
    Serial.print("[WIFI] Connected IP=");
    Serial.println(WiFi.localIP());
    Serial.print("[WIFI] RSSI=");
    Serial.println(WiFi.RSSI());
    Serial.println("[STREAM] http://192.168.50.2/stream");
  }
  if (!udpReady) {
    udpReady = radarUdp.begin(5006);
    Serial.println(udpReady ? "[UDP] Radar sender ready -> Pi:5005" : "[UDP] Init failed");
  }
  sendRadar();
  if (!server) {
    if (startServer()) Serial.println("[HTTP] READY");
    else {
      Serial.println("[HTTP] FAIL - retrying");
      delay(2000);
    }
  }
  delay(100);
}
