#include <Wire.h>
#include "MPU6050.h"
#include "MAX30105.h"
#include "heartRate.h"
#include "spo2_algorithm.h"
#include <avr/wdt.h>

#define BUFFER_SIZE 20
#define MAX_MESSAGE_LENGTH 20

uint16_t irBuffer[BUFFER_SIZE]; //infrared LED sensor data
uint16_t redBuffer[BUFFER_SIZE]; //red LED sensor data

MPU6050 mpu;
MAX30105 particleSensor;

int16_t AcX, AcY, AcZ, Tmp, GyX, GyY, GyZ;
float ax = 0, ay = 0, az = 0;
const int buzzerPin = 11;
const int buttonPin = 10;
const int sosbuttonPin = 8;
bool buzzerOn = false;
bool buzzerToneOn = false;
int32_t spo2;
int8_t validSPO2;
int32_t heartRate;
int8_t validHeartRate;

const int ldr = A0;
int ldrvalue = 0;

int led = 3;
bool ledOn = false;


const int melody[] = {
  262, 294, 330, 349, 392, 440, 494, 523
};

const int noteDurations[] = {
  4, 4, 4, 4, 4, 4, 4, 4
};

void setup() {
  Serial.begin(9600);
  mpu.initialize();
  pinMode(buzzerPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP); 
  pinMode(sosbuttonPin, INPUT); 
  pinMode(led, OUTPUT);
  wdt_disable(); 
  delay(1000);
  wdt_enable(WDTO_2S);

  // Initialize sensor
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30105 was not found. Please check wiring/power. ");
  }

  byte ledBrightness = 60; //Options: 0=Off to 255=50mA
  byte sampleAverage = 4; //Options: 1, 2, 4, 8, 16, 32
  byte ledMode = 2; //Options: 1 = Red only, 2 = Red + IR, 3 = Red + IR + Green
  byte sampleRate = 100; //Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
  int pulseWidth = 411; //Options: 69, 118, 215, 411
  int adcRange = 4096; //Options: 2048, 4096, 8192, 16384

  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange); 
}

void loop() {
  for (int i = 0; i < BUFFER_SIZE; i++){
    redBuffer[i] = particleSensor.getRed();
    irBuffer[i] = particleSensor.getIR();
    particleSensor.nextSample();

  int Amp = getAmplitude();

  Serial.print("Amp=");
  Serial.println(Amp);

  ldrvalue = analogRead(ldr);
  Serial.print("LDR=");
  Serial.println(ldrvalue); 

  if (digitalRead(buttonPin) == HIGH && buzzerOn) {
    buzzerOn = false;
    Serial.println("stop");
  }

  if (digitalRead(sosbuttonPin) == HIGH) {
    Serial.println("SOS_BUTTON_PRESSED");
  }
  
  digitalWrite(led, ledOn ? HIGH : LOW);
  if (buzzerOn) {
    tone(buzzerPin, 1000); // Frequency set to 1000 Hz
  } else {
    noTone(buzzerPin);
  }
  
  if (buzzerToneOn) {
    for (int i = 0; i < 8; i++) {
    int noteDuration = 1000 / noteDurations[i];
    tone(buzzerPin, melody[i], noteDuration);
    int pauseBetweenNotes = noteDuration * 1.30;
    delay(pauseBetweenNotes);
    noTone(buzzerPin);
    }
  }

  maxim_heart_rate_and_oxygen_saturation(irBuffer, BUFFER_SIZE, redBuffer, &spo2, &validSPO2, &heartRate, &validHeartRate);

  Serial.print(F("HR="));
  Serial.print(heartRate);
  Serial.print(F(", HRvalid="));
  Serial.println(validHeartRate);
  Serial.print(F("SPO2="));
  Serial.print(spo2);
  Serial.print(F(", SPO2Valid="));
  Serial.println(validSPO2);
  }

  wdt_reset();

}

void serialEvent() {
  static char message[MAX_MESSAGE_LENGTH]; // Define a char array to store the received message
  static byte index = 0; // Index for incoming characters
  
  while (Serial.available()) {
    char incomingByte = Serial.read();

    if (incomingByte != '\n' && index < MAX_MESSAGE_LENGTH - 1) {
      // Append the incoming character to the message
      message[index++] = incomingByte;
    } else {
      message[index] = '\0'; // Null-terminate the string
      
      if (strcmp(message, "On") == 0) {
        buzzerOn = true;
      } else if (strcmp(message, "Dark") == 0) {
        ledOn = true;
      } else if (strcmp(message, "Bright") == 0) {
        ledOn = false;
      } else if (strcmp(message, "Off") == 0) {
        buzzerOn = false;
      } else if (strcmp(message, "1") == 0) {
        buzzerToneOn = true; // Use the new variable
      } else {
        
      }

      index = 0; // Reset index for the next message
    }
  }
}

int getAmplitude() {
  ax = (AcX - 2050) / 16384.00;
  ay = (AcY - 77) / 16384.00;
  az = (AcZ - 1947) / 16384.00;
  // Read accelerometer data and calculate amplitude
  mpu_read();
  float Raw_Amp = pow(pow(ax, 2) + pow(ay, 2) + pow(az, 2), 0.5);
  return Raw_Amp * 10;
}

void mpu_read() {
  Wire.beginTransmission(0x68); // MPU6050 address
  Wire.write(0x3B);  // starting with register 0x3B (ACCEL_XOUT_H)
  Wire.endTransmission(false);
  Wire.requestFrom(0x68, 14, true); // request a total of 14 registers
  AcX = Wire.read() << 8 | Wire.read(); // 0x3B (ACCEL_XOUT_H) & 0x3C (ACCEL_XOUT_L)
  AcY = Wire.read() << 8 | Wire.read(); // 0x3D (ACCEL_YOUT_H) & 0x3E (ACCEL_YOUT_L)
  AcZ = Wire.read() << 8 | Wire.read(); // 0x3F (ACCEL_ZOUT_H) & 0x40 (ACCEL_ZOUT_L)
  Tmp = Wire.read() << 8 | Wire.read(); // 0x41 (TEMP_OUT_H) & 0x42 (TEMP_OUT_L)
  GyX = Wire.read() << 8 | Wire.read(); // 0x43 (GYRO_XOUT_H) & 0x44 (GYRO_XOUT_L)
  GyY = Wire.read() << 8 | Wire.read(); // 0x45 (GYRO_YOUT_H) & 0x46 (GYRO_YOUT_L)
  GyZ = Wire.read() << 8 | Wire.read(); // 0x47 (GYRO_ZOUT_H) & 0x48 (GYRO_ZOUT_L)
}