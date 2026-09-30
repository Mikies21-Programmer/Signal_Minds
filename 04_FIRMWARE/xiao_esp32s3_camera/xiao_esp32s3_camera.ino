#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>

// ===========================
// Select camera model in board_config.h
// ===========================
#include "board_config.h"

// Access Point Credentials as requested
const char *ap_ssid = "SENA_CORRECTA_CAM";
const char *ap_password = "SenaCam2026";

void startCameraServer();
void setupLedFlash();

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n==================================================");
  Serial.println("INDIVISA INGENIUM 2026 — XIAO ESP32-S3 SENSE CAM");
  Serial.println("==================================================");

  // Check PSRAM
  if (psramFound()) {
    Serial.printf("[PSRAM] Detectada y activa: %d MB\n", (int)(ESP.getPsramSize() / (1024 * 1024)));
  } else {
    Serial.println("[PSRAM] ALERTA: PSRAM no detectada!");
  }

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_VGA;      // 640x480 pre-alloc
  config.pixel_format = PIXFORMAT_JPEG;   // for streaming
  config.grab_mode = CAMERA_GRAB_LATEST;  // freshest frame, minimal latency
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;               // 10-12: good quality and high speed
  config.fb_count = 2;                    // double buffer in PSRAM

  if (!psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.fb_count = 1;
  }

  // Camera init
  Serial.println("[CAM] Inicializando sensor de camara...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] ERROR CRITICO: esp_camera_init fallo con codigo 0x%x\n", err);
    return;
  }
  Serial.println("[CAM] Camera init success!");

  // Detect and configure sensor specifics
  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL) {
    Serial.printf("[CAM] Sensor detectado PID: 0x%04x\n", s->id.PID);
    if (s->id.PID == OV3660_PID) {
      Serial.println("[CAM] Sensor identificado como OV3660");
      s->set_vflip(s, 1);
      s->set_brightness(s, 1);
      s->set_saturation(s, -2);
    } else if (s->id.PID == OV2640_PID) {
      Serial.println("[CAM] Sensor identificado como OV2640");
      s->set_vflip(s, 1);
      s->set_hmirror(s, 0);
    }
    s->set_framesize(s, FRAMESIZE_QVGA);
    Serial.println("[CAM] Resolucion inicial fijada a QVGA (320x240)");
  }

  // Dedicated SoftAP Mode
  Serial.println("[WIFI] Iniciando Punto de Acceso dedicado (SoftAP)...");
  WiFi.mode(WIFI_AP);
  IPAddress local_ip(192, 168, 4, 1);
  IPAddress gateway(192, 168, 4, 1);
  IPAddress subnet(255, 255, 255, 0);
  WiFi.softAPConfig(local_ip, gateway, subnet);
  
  bool ap_ok = WiFi.softAP(ap_ssid, ap_password, 1); // Channel 1
  if (ap_ok) {
    Serial.println("[WIFI] SoftAP iniciado exitosamente!");
    Serial.printf("[WIFI] SSID: %s\n", ap_ssid);
    Serial.printf("[WIFI] Password: %s\n", ap_password);
    Serial.printf("[WIFI] IP: %s\n", WiFi.softAPIP().toString().c_str());
  } else {
    Serial.println("[WIFI] ERROR al iniciar SoftAP!");
  }

  // Start HTTP / MJPEG servers
  Serial.println("[HTTP] Iniciando servidores de streaming y control...");
  startCameraServer();

  Serial.println("==================================================");
  Serial.println("ESTADO LISTO:");
  Serial.printf("Web UI:    http://%s/\n", WiFi.softAPIP().toString().c_str());
  Serial.printf("Snapshot:  http://%s/capture\n", WiFi.softAPIP().toString().c_str());
  Serial.printf("Stream:    http://%s:81/stream\n", WiFi.softAPIP().toString().c_str());
  Serial.println("==================================================");
}

void loop() {
  delay(10000);
}
