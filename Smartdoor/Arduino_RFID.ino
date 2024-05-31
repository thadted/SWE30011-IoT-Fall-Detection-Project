#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>

// Define pins
#define pinLDR A0
#define pinServo 2
#define pinLED 3
#define pinBuzzer 4
#define pinServo2 5
#define pinButton2 7
#define pinButton 8  
#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc522(SS_PIN, RST_PIN); // Create MFRC522 instance
Servo myServo; // Define servo name
Servo myServo2;

int previousLdrStatus = -1; // Variable to store previous LDR status (-1 means uninitialized)
bool doorOpen = false; // Variable to track door status
bool ledOpen = false;
bool Auto = false;
bool authorized = false;
bool buzzer = false;
bool buttonPressed = false;
bool button2Pressed = false;

void setup() {
  Serial.begin(9600); // Initiate a serial communication
  SPI.begin(); // Initiate SPI bus
  mfrc522.PCD_Init(); // Initiate MFRC522
  
  // Initialize servos
  myServo.attach(pinServo);
  myServo.write(0); // Servo start position
  myServo2.attach(pinServo2);
  myServo2.write(150); // Servo start position
  
  // Initialize other pins
  pinMode(pinLED, OUTPUT);
  pinMode(pinBuzzer, OUTPUT);
  pinMode(pinButton, INPUT);
  pinMode(pinButton2, INPUT);
  noTone(pinBuzzer);
  
  // Welcome message
  Serial.println("Put your card to the reader...");
  Serial.println();
}

void handleCommand(String command) {

  if (command.equalsIgnoreCase("dooropen")) {

    myServo.write(150);
    myServo2.write(0);
    doorOpen = true;
    Serial.print("Door Status: ");
    Serial.println(doorOpen ? "Open" : "Closed");
  } 
  
  else if (command.equalsIgnoreCase("doorclose")) {
    
    myServo.write(0); 
    myServo2.write(150);
    doorOpen = false;
    Serial.print("Door Status: ");
    Serial.println(doorOpen ? "Open" : "Closed");
  } 

  else if (command.equalsIgnoreCase("ledopen")) {
    Auto = false;
    digitalWrite(pinLED, HIGH);
    ledOpen = true;
    Serial.print("LED Status: ");
    Serial.println(ledOpen ? "Open" : "Closed");
  } 

  else if (command.equalsIgnoreCase("ledclose")) {
    Auto = false;
    digitalWrite(pinLED, LOW);
    ledOpen = false;
    Serial.print("LED Status: ");
    Serial.println(ledOpen ? "Open" : "Closed");
  } 

  else if(command.equalsIgnoreCase("Authorized")){
    authorized = true;
    Serial.println("Authorized access");
    Serial.println();
    delay(500);
    tone(pinBuzzer, 500);
    delay(300);
    noTone(pinBuzzer);
    myServo.write(150);
    myServo2.write(0);
    doorOpen = true;
    Serial.print("Door Status: ");
    Serial.println(doorOpen ? "Open" : "Closed");
    delay(8000);
    myServo.write(0);
    myServo2.write(150);
    doorOpen = false;
    Serial.print("Door Status: ");
    Serial.println(doorOpen ? "Open" : "Closed");
  }

  else if(command.equalsIgnoreCase("Unauthorized")){
    buzzer = true;
    tone(pinBuzzer, 500);
    delay(300);
    noTone(pinBuzzer);
   }

  else if(command.equalsIgnoreCase("auto")){
    Auto = true;
  }
  
  else {
    Serial.println("Unknown command. Please enter 'open' or 'close'.");
  }
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    handleCommand(command);
  }

  // Check the button state
  if (digitalRead(pinButton) == HIGH) {
    if (!buttonPressed) {
      buttonPressed = true;
      digitalWrite(pinBuzzer, HIGH);
      Serial.println("Button Pressed");
    }
  } else {
    if (buttonPressed) {
      buttonPressed = false;
      digitalWrite(pinBuzzer, LOW);
    }
  }

  // Check the button2 state
  if (digitalRead(pinButton2) == HIGH) {
    if (!button2Pressed) {
      button2Pressed = true;
      Serial.println("Button2 Pressed");
      tone(pinBuzzer, 500);
      delay(300);
      noTone(pinBuzzer);
      myServo.write(150);
      myServo2.write(0);
      delay(5000);
    }
  } else {
    if (button2Pressed) {
      button2Pressed = false;
      myServo.write(0);
      myServo2.write(150);
    }
  }

 if(Auto == true){

    // Read LDR value
  int ldrValue = analogRead(pinLDR);

  // Check if LDR value is below threshold
  int ldrStatus = (ldrValue < 400) ? 1 : 0;

  // Update LED based on LDR status
  digitalWrite(pinLED, ldrStatus == 1 ? HIGH : LOW);
  
  // Check if the LDR status has changed
  if (ldrStatus != previousLdrStatus) {
    // Send LDR value and status to serial
    Serial.print("LDR Value: ");
    Serial.print(ldrValue);
    Serial.print("\n");
    Serial.print("LED Status: ");
    Serial.println(ldrStatus == 1 ? "Open" : "Closed");
    Serial.print("\n");
    previousLdrStatus = ldrStatus;
  }
 }


  // Look for new cards
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // Select one of the cards
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

   // Show UID on serial monitor
Serial.print("UID tag: ");
String content = "";
for (byte i = 0; i < mfrc522.uid.size; i++) {
  Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
  Serial.print(mfrc522.uid.uidByte[i], HEX);
  content.concat(String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : ""));
  content.concat(String(mfrc522.uid.uidByte[i], HEX));
}

Serial.println();



  // Halt PICC and stop encryption on PCD
  mfrc522.PICC_HaltA(); // Halt PICC
  mfrc522.PCD_StopCrypto1(); // Stop encryption on PCD
  delay(1000); // Add delay to avoid reading the same card multiple times
}