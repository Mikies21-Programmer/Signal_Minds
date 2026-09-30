#include <Arduino.h>
#include <Wire.h>
#include <math.h>

// ==============================================================================
// INDIVISA INGENIUM 2026 — FIRMWARE SENSOR ORIENTACIÓN DE MANO (MPU6050)
// Microcontrolador: ESP32-S3 (Dedicado)
// Hardware: MPU6050 6-DOF (Dorso de la palma de la mano)
// Conexiones: SDA=GPIO4, SCL=GPIO5, VCC=3.3V, GND=GND
// Protocolo: USB-Serial @ 115200 baud, 50 Hz
// ==============================================================================

#define I2C_SDA_PIN      4
#define I2C_SCL_PIN      5
#define I2C_FREQ_HZ      100000  // 100 kHz para máxima robustez

#define MPU6050_SMPLRT_DIV   0x19
#define MPU6050_CONFIG       0x1A
#define MPU6050_GYRO_CONFIG  0x1B
#define MPU6050_ACCEL_CONFIG 0x1C
#define MPU6050_ACCEL_XOUT_H 0x3B
#define MPU6050_PWR_MGMT_1   0x6B
#define MPU6050_WHO_AM_I     0x75

// Estado de hardware
uint8_t mpu_address = 0;
bool mpu_connected = false;
bool is_calibrated = false;

// Referencias de calibración (RAM)
float roll_ref = 0.0f;
float pitch_ref = 0.0f;
float gyro_bias_x = 0.0f;
float gyro_bias_y = 0.0f;
float gyro_bias_z = 0.0f;

// Ángulos filtrados
float filtered_roll = 0.0f;
float filtered_pitch = 0.0f;
bool first_sample = true;

// Temporizadores
unsigned long last_telemetry_time = 0;
unsigned long last_sample_time = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 20; // 50 Hz

// Buffer serie de comandos
String serial_cmd_buffer = "";

// ------------------------------------------------------------------------------
// Detección I2C del sensor
// ------------------------------------------------------------------------------
uint8_t detectMPU6050() {
  uint8_t candidate_addresses[2] = {0x68, 0x69};
  for (int i = 0; i < 2; i++) {
    uint8_t addr = candidate_addresses[i];
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();
    if (error == 0) {
      // Leer WHO_AM_I
      Wire.beginTransmission(addr);
      Wire.write(MPU6050_WHO_AM_I);
      if (Wire.endTransmission(false) == 0) {
        Wire.requestFrom(addr, (uint8_t)1);
        if (Wire.available()) {
          uint8_t who = Wire.read();
          Serial.printf("[MPU6050] I2C 0x%02X respondió WHO_AM_I: 0x%02X\n", addr, who);
          if (who == 0x68 || who == 0x70 || who == 0x72) {
            return addr;
          }
        }
      }
    }
  }
  return 0;
}

// ------------------------------------------------------------------------------
// Inicialización del MPU6050
// ------------------------------------------------------------------------------
bool initMPU6050(uint8_t addr) {
  // Despertar el sensor y usar PLL con referencia Gyro X
  Wire.beginTransmission(addr);
  Wire.write(MPU6050_PWR_MGMT_1);
  Wire.write(0x01); // Clock Source: PLL with X Gyro
  if (Wire.endTransmission() != 0) return false;

  delay(10);

  // Filtro Digital Paso Bajo (DLPF): 44 Hz Accel, 42 Hz Gyro (modo 3)
  Wire.beginTransmission(addr);
  Wire.write(MPU6050_CONFIG);
  Wire.write(0x03);
  if (Wire.endTransmission() != 0) return false;

  // Sample Rate Divider = 4 -> 1 kHz / (1 + 4) = 200 Hz internal
  Wire.beginTransmission(addr);
  Wire.write(MPU6050_SMPLRT_DIV);
  Wire.write(0x04);
  if (Wire.endTransmission() != 0) return false;

  // Accel Config: ±2g (16384 LSB/g)
  Wire.beginTransmission(addr);
  Wire.write(MPU6050_ACCEL_CONFIG);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) return false;

  // Gyro Config: ±250 °/s (131.0 LSB/°/s)
  Wire.beginTransmission(addr);
  Wire.write(MPU6050_GYRO_CONFIG);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) return false;

  return true;
}

// ------------------------------------------------------------------------------
// Lectura de datos crudos de 6 ejes
// ------------------------------------------------------------------------------
bool readRawMPU6050(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  if (mpu_address == 0) return false;

  Wire.beginTransmission(mpu_address);
  Wire.write(MPU6050_ACCEL_XOUT_H);
  if (Wire.endTransmission(false) != 0) {
    mpu_connected = false;
    return false;
  }

  uint8_t bytes_read = Wire.requestFrom(mpu_address, (uint8_t)14);
  if (bytes_read != 14) {
    mpu_connected = false;
    return false;
  }

  int16_t raw_ax = (Wire.read() << 8) | Wire.read();
  int16_t raw_ay = (Wire.read() << 8) | Wire.read();
  int16_t raw_az = (Wire.read() << 8) | Wire.read();
  Wire.read(); Wire.read(); // Saltear temperatura
  int16_t raw_gx = (Wire.read() << 8) | Wire.read();
  int16_t raw_gy = (Wire.read() << 8) | Wire.read();
  int16_t raw_gz = (Wire.read() << 8) | Wire.read();

  // Conversión a unidades físicas (g y °/s)
  ax = (float)raw_ax / 16384.0f;
  ay = (float)raw_ay / 16384.0f;
  az = (float)raw_az / 16384.0f;

  gx = ((float)raw_gx - gyro_bias_x) / 131.0f;
  gy = ((float)raw_gy - gyro_bias_y) / 131.0f;
  gz = ((float)raw_gz - gyro_bias_z) / 131.0f;

  mpu_connected = true;
  return true;
}

// ------------------------------------------------------------------------------
// Procedimiento de Calibración
// ------------------------------------------------------------------------------
void performCalibration() {
  Serial.println("[CALIB] Iniciando calibración de orientación de mano...");
  Serial.println("[CALIB] Por favor mantén la mano en POSE DE REFERENCIA (palma frente a cámara, muñeca recta)");

  const int SAMPLES = 200;
  float sum_roll = 0.0f;
  float sum_pitch = 0.0f;
  float sum_raw_gx = 0.0f;
  float sum_raw_gy = 0.0f;
  float sum_raw_gz = 0.0f;
  int valid_samples = 0;

  for (int i = 0; i < SAMPLES; i++) {
    float ax, ay, az, gx, gy, gz;
    if (readRawMPU6050(ax, ay, az, gx, gy, gz)) {
      // Fórmulas especificadas
      float roll_acc = atan2(ay, az) * 180.0f / (float)M_PI;
      float pitch_acc = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0f / (float)M_PI;

      sum_roll += roll_acc;
      sum_pitch += pitch_acc;
      sum_raw_gx += (gx * 131.0f + gyro_bias_x);
      sum_raw_gy += (gy * 131.0f + gyro_bias_y);
      sum_raw_gz += (gz * 131.0f + gyro_bias_z);
      valid_samples++;
    }
    delay(15); // ~3 segundos en total
  }

  if (valid_samples > 100) {
    roll_ref = sum_roll / valid_samples;
    pitch_ref = sum_pitch / valid_samples;
    gyro_bias_x = sum_raw_gx / valid_samples;
    gyro_bias_y = sum_raw_gy / valid_samples;
    gyro_bias_z = sum_raw_gz / valid_samples;
    is_calibrated = true;
    filtered_roll = roll_ref;
    filtered_pitch = pitch_ref;

    Serial.printf("[CALIB] CALIBRATION_OK,roll_ref=%.2f,pitch_ref=%.2f,samples=%d\n", roll_ref, pitch_ref, valid_samples);
  } else {
    Serial.println("[CALIB] ERROR_CALIBRATION_FAILED: sensor inestable o desconectado");
  }
}

// ------------------------------------------------------------------------------
// SETUP
// ------------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==================================================");
  Serial.println("INDIVISA INGENIUM 2026 — MPU6050 HAND IMU (ESP32-S3)");
  Serial.println("Pines I2C: SDA=GPIO4, SCL=GPIO5 | Baud=115200 | 50Hz");
  Serial.println("==================================================");

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_FREQ_HZ);
  delay(100);

  // Escanear I2C
  Serial.println("[I2C] Escaneando bus para MPU6050...");
  mpu_address = detectMPU6050();

  if (mpu_address != 0) {
    Serial.printf("[I2C] Sensor MPU6050 encontrado en dirección 0x%02X\n", mpu_address);
    if (initMPU6050(mpu_address)) {
      mpu_connected = true;
      Serial.println("[MPU6050] Configuración completada exitosamente.");
    } else {
      Serial.println("[MPU6050] ERROR al configurar registros.");
    }
  } else {
    Serial.println("[I2C] ALERTA: No se detectó MPU6050 en 0x68 ni 0x69.");
    Serial.println("[I2C] Verifique conexiones físicas (VCC 3.3V, GND, SDA GPIO4, SCL GPIO5).");
  }

  last_sample_time = millis();
}

// ------------------------------------------------------------------------------
// LOOP PRINCIPAL
// ------------------------------------------------------------------------------
void loop() {
  unsigned long now = millis();

  // 1. Escuchar comandos serie (por ejemplo CALIBRATE)
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      serial_cmd_buffer.trim();
      if (serial_cmd_buffer.equalsIgnoreCase("CALIBRATE") || serial_cmd_buffer.equalsIgnoreCase("CALIB")) {
        performCalibration();
      } else if (serial_cmd_buffer.equalsIgnoreCase("PING")) {
        Serial.printf("PONG,MPU6050,addr=0x%02X,connected=%s,calibrated=%s\n",
                      mpu_address, mpu_connected ? "true" : "false", is_calibrated ? "true" : "false");
      }
      serial_cmd_buffer = "";
    } else {
      serial_cmd_buffer += c;
    }
  }

  // 2. Reintentar conexión si no está conectado
  if (!mpu_connected && (now - last_telemetry_time >= 1000)) {
    mpu_address = detectMPU6050();
    if (mpu_address != 0 && initMPU6050(mpu_address)) {
      mpu_connected = true;
      Serial.printf("[MPU6050] Reconectado exitosamente en 0x%02X\n", mpu_address);
    }
  }

  // 3. Telemetría a 50 Hz (20 ms)
  if (now - last_telemetry_time >= TELEMETRY_INTERVAL_MS) {
    float dt = (float)(now - last_sample_time) / 1000.0f;
    last_sample_time = now;
    last_telemetry_time = now;

    if (dt <= 0.0f || dt > 0.2f) dt = 0.020f;

    float ax = 0.0f, ay = 0.0f, az = 0.0f;
    float gx = 0.0f, gy = 0.0f, gz = 0.0f;

    if (readRawMPU6050(ax, ay, az, gx, gy, gz)) {
      // Fórmulas requeridas
      float roll_acc = atan2(ay, az) * 180.0f / (float)M_PI;
      float pitch_acc = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0f / (float)M_PI;

      if (first_sample) {
        filtered_roll = roll_acc;
        filtered_pitch = pitch_acc;
        first_sample = false;
      } else {
        // Filtro complementario: 96% integración de giro + 4% acelerómetro
        filtered_roll = 0.96f * (filtered_roll + gx * dt) + 0.04f * roll_acc;
        filtered_pitch = 0.96f * (filtered_pitch + gy * dt) + 0.04f * pitch_acc;
      }

      // Protocolo IMU:
      // IMU,<timestamp_ms>,<roll>,<pitch>,<gx>,<gy>,<gz>,<yaw_valid>
      // yaw_valid=false porque MPU6050 no tiene magnetómetro para yaw absoluto
      Serial.printf("IMU,%lu,%.2f,%.2f,%.2f,%.2f,%.2f,false\n",
                    now, filtered_roll, filtered_pitch, gx, gy, gz);
    } else {
      // Reporte de desconexión sin bloquear
      Serial.printf("IMU_ERROR,%lu,DISCONNECTED\n", now);
    }
  }
}
