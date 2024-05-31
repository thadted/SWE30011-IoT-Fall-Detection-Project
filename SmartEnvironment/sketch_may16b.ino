// Define the pins for the temperature sensor, gas sensor, buzzer, LED, and ultrasonic sensors
const int tempSensorPin = A0;      // Temperature sensor output pin connected to analog pin A0
const int checkSensorPin = A1;     // Additional sensor connected to analog pin A1
const int gasSensorPin = A2;       // Gas sensor output pin connected to analog pin A2
const int buzzerPin = 13;          // Buzzer connected to digital pin 13
const int livingRoomLightPin = 6;  // Pin for controlling living room light
const int bedroomLightPin = 7;     // Pin for controlling bedroom light

// Define the pins for the ultrasonic sensors
const int trigPinLivingRoom = 4;  // Ultrasonic sensor for living room trigger pin connected to digital pin 4
const int echoPinLivingRoom = 5;  // Ultrasonic sensor for living room echo pin connected to digital pin 5
const int trigPinBedroom = 12;    // Ultrasonic sensor for bedroom trigger pin connected to digital pin 12
const int echoPinBedroom = 11;    // Ultrasonic sensor for bedroom echo pin connected to digital pin 11

// Define the modes for light control
enum LightMode { AUTO,
                 ON,
                 OFF };
LightMode livingRoomMode = AUTO;  // Default mode
LightMode bedroomMode = AUTO;     // Default mode

bool livingRoomTriggered = false;
bool bedroomTriggered = false;
unsigned long livingRoomStartTime = 0;
unsigned long bedroomStartTime = 0;
unsigned long lastDisplayTime = 0;  // Variable to store the last display time

void setup() {
  // Initialize the buzzer pin as an output
  pinMode(buzzerPin, OUTPUT);

  // Initialize the light control pins as outputs
  pinMode(livingRoomLightPin, OUTPUT);
  pinMode(bedroomLightPin, OUTPUT);

  // Initialize the ultrasonic sensor pins
  pinMode(trigPinLivingRoom, OUTPUT);
  pinMode(echoPinLivingRoom, INPUT);
  pinMode(trigPinBedroom, OUTPUT);
  pinMode(echoPinBedroom, INPUT);

  // Begin serial communication for debugging purposes
  Serial.begin(9600);
}

void loop() {
  float temperatureC = readTemperature();
  int gasReading = analogRead(gasSensorPin);
  int checkSensorReading = analogRead(checkSensorPin);

  long distanceLivingRoom = measureDistance(trigPinLivingRoom, echoPinLivingRoom);
  long distanceBedroom = measureDistance(trigPinBedroom, echoPinBedroom);

  handleUltrasonicSensor(distanceLivingRoom, livingRoomLightPin, livingRoomTriggered, livingRoomStartTime, "Living Room", livingRoomMode);
  handleUltrasonicSensor(distanceBedroom, bedroomLightPin, bedroomTriggered, bedroomStartTime, "Bedroom", bedroomMode);

  handleGasSensor(gasReading);
  handleTemperatureSensor(temperatureC);

  displayReadings(temperatureC, gasReading);

  delay(1000);  // Small delay to avoid serial monitor spamming
}

float readTemperature() {
  int tempReading = analogRead(tempSensorPin);
  float voltage = tempReading * (5.0 / 1023.0);
  float temperatureC = voltage * 15;  // Adjust this line according to your temperature sensor's datasheet
  return temperatureC;
}

long measureDistance(int trigPin, int echoPin) {
  long duration, distance;
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  duration = pulseIn(echoPin, HIGH);
  distance = duration * 0.034 / 2;  // Convert duration to distance in cm
  return distance;
}

void handleUltrasonicSensor(long distance, int lightPin, bool &triggered, unsigned long &startTime, const char *roomName, LightMode mode) {
  if (distance < 20) {
    Serial.println(roomName);
    triggered = true;
    startTime = millis();

    // Only control light in AUTO mode
    if (mode == AUTO) {
      digitalWrite(lightPin, HIGH);
    }
  }

  // Only control light in AUTO mode
  if (mode == AUTO && triggered && millis() - startTime >= 180000) {  // 3 minutes = 180,000 milliseconds
    triggered = false;
    digitalWrite(lightPin, LOW);
  }
}

void handleGasSensor(int gasReading) {
  if (gasReading > 450) {
    Serial.println("Gas Detected");
    playGasSiren();
  }
}

void handleTemperatureSensor(float temperatureC) {
  if (temperatureC > 50) {
    Serial.println("High Temperature Detected");
    playTempSiren();
  }

  if (temperatureC <= 50) {
    noTone(buzzerPin);  // Turn off the buzzer if temperature is normal
  }
}

void displayReadings(float temperatureC, int gasReading) {
  if (millis() - lastDisplayTime >= 10000) {  // 10 seconds = 10,000 milliseconds
    Serial.print("Temperature: ");
    Serial.println(temperatureC);
    Serial.print("Gas Level: ");
    Serial.println(gasReading);
    lastDisplayTime = millis();
  }
}

void serialEvent() {
  static String message = "";  // Define a static variable to store the received message

  while (Serial.available()) {
    char incomingByte = Serial.read();

    if (incomingByte != '\n') {
      message += incomingByte;
    } else {
      if (message.equals("DoorbellPressed")) {
        playDoorbellSound();
      }

      if (message.equals("LivingRoomON")) {
        digitalWrite(livingRoomLightPin, HIGH);
        livingRoomMode = ON;
      }

      if (message.equals("LivingRoomOFF")) {
        digitalWrite(livingRoomLightPin, LOW);
        livingRoomMode = OFF;
      }

      if (message.equals("LivingRoomAUTO")) {
        livingRoomMode = AUTO;
      }

      if (message.equals("BedroomON")) {
        digitalWrite(bedroomLightPin, HIGH);
        bedroomMode = ON;
      }

      if (message.equals("BedRoomOFF")) {
        digitalWrite(bedroomLightPin, LOW);
        bedroomMode = OFF;
      }

      if (message.equals("BedRoomAUTO")) {
        bedroomMode = AUTO;
      }
      message = "";
    }
  }
}

// Function to play the doorbell sound
void playDoorbellSound() {
  // Play the "Ding Dong" doorbell sound
  tone(buzzerPin, 880, 200);  // Tone for "Ding"
  delay(200);
  tone(buzzerPin, 784, 400);  // Tone for "Dong"
  delay(400);
}

// Function to play the gas siren on the buzzer
void playGasSiren() {
  for (int i = 0; i < 200; i++) {
    tone(buzzerPin, 1000 + i * 2);  // Increasing frequency
    delay(5);
  }
  for (int i = 200; i > 0; i--) {
    tone(buzzerPin, 1000 + i * 2);  // Decreasing frequency
    delay(5);
  }
}

// Function to play the temperature siren on the buzzer
void playTempSiren() {
  for (int i = 0; i < 5; i++) {
    tone(buzzerPin, 500);  // Low frequency tone
    delay(500);
    tone(buzzerPin, 1500);  // High frequency tone
    delay(500);
  }
  noTone(buzzerPin);  // Turn off the buzzer after the siren pattern
}
