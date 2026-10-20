/*
 * Node sensor ESP32: PM2.5 (PMS5003) + suhu/kelembapan (DHT22) + okupansi (PIR)
 * + daya listrik (PZEM-004T v3, opsional) -> MQTT JSON.
 * Library: PubSubClient, DHT sensor library (Adafruit)
 * Wiring: PMS5003 TX->GPIO16 (RX2) | DHT22 data->GPIO4 | PIR out->GPIO27
 */
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

const char* WIFI_SSID = "GANTI_SSID";
const char* WIFI_PASS = "GANTI_PASSWORD";
const char* MQTT_HOST = "192.168.1.10";
const char* ROOM      = "lab_komputer";
const unsigned long PUBLISH_MS = 5UL * 60UL * 1000UL;  // tiap 5 menit

#define PIN_DHT 4
#define PIN_PIR 27
DHT dht(PIN_DHT, DHT22);
WiFiClient wifi;
PubSubClient mqtt(wifi);
HardwareSerial pmsSerial(2);

int readPM25() {
  // Frame PMS5003 = 32 byte, header 0x42 0x4D; PM2.5 atmosferik di byte 12-13
  unsigned long t0 = millis();
  while (millis() - t0 < 2000) {
    if (pmsSerial.available() >= 32 && pmsSerial.peek() == 0x42) {
      uint8_t buf[32];
      pmsSerial.readBytes(buf, 32);
      if (buf[1] != 0x4D) continue;
      uint16_t sum = 0;
      for (int i = 0; i < 30; i++) sum += buf[i];
      if (sum != (uint16_t)((buf[30] << 8) | buf[31])) continue;   // cek checksum
      return (buf[12] << 8) | buf[13];
    } else if (pmsSerial.available()) pmsSerial.read();
  }
  return -1;
}

void connectAll() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) delay(500);
  }
  while (!mqtt.connected()) {
    if (!mqtt.connect(ROOM)) delay(2000);
  }
}

void setup() {
  Serial.begin(115200);
  pmsSerial.begin(9600, SERIAL_8N1, 16, -1);
  pinMode(PIN_PIR, INPUT);
  dht.begin();
  mqtt.setServer(MQTT_HOST, 1883);
}

void loop() {
  connectAll();
  mqtt.loop();
  static unsigned long last = 0;
  static int occupied = 0;
  if (digitalRead(PIN_PIR)) occupied = 1;       // ada gerakan dalam jendela publish
  if (millis() - last >= PUBLISH_MS || last == 0) {
    last = millis();
    int pm = readPM25();
    float t = dht.readTemperature(), h = dht.readHumidity();
    float power = 0;  // TODO: baca PZEM-004T via UART bila terpasang
    char topic[64], payload[160];
    snprintf(topic, sizeof(topic), "building/%s/telemetry", ROOM);
    snprintf(payload, sizeof(payload),
             "{\"pm25\":%d,\"temp_c\":%.1f,\"humidity\":%.1f,\"occupancy\":%d,\"power_w\":%.0f}",
             pm, t, h, occupied, power);
    mqtt.publish(topic, payload);
    Serial.println(payload);
    occupied = 0;
  }
}
