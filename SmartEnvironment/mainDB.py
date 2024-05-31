import serial
import mysql.connector
from datetime import datetime
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# AWS IoT MQTT Configuration
# Add your AWS IoT endpoint, root CA, private key, and certificate paths here
AWS_IOT_ENDPOINT = "a3gax6b93xkabz-ats.iot.us-east-1.amazonaws.com"
AWS_IOT_PORT = 8883
AWS_IOT_ROOT_CA = "/home/pi/swe30011/cert/AmazonRootCA1.pem"
AWS_IOT_PRIVATE_KEY = "/home/pi/swe30011/cert/31368caa38edae254c0f2d0e94d8d984f0698c5a3d4d6c1c4c28e121511995ae-private.pem.key"
AWS_IOT_CERTIFICATE = "/home/pi/swe30011/cert/31368caa38edae254c0f2d0e94d8d984f0698c5a3d4d6c1c4c28e121511995ae-certificate.pem.crt"

# MySQL Configuration
DB_HOST = "localhost"
DB_USER = "pi"
DB_PASSWORD = "abcd1234"
DB_NAME = "sensor_db"

# MQTT Topics
MQTT_TOPIC_HIGH_TEMPERATURE_DETECTED = "sensor/high_temperature_detected"
MQTT_TOPIC_GAS_DETECTED = "sensor/gas_detected"
MQTT_TOPIC_DOORBELL_PRESSED = "smart_door/doorbell_detection"

# Connect to MySQL database
try:
    db = mysql.connector.connect(
        host="localhost",
        user="pi",
        password="abcd1234",
        database="sensor_db"
    )
    cursor = db.cursor()
except mysql.connector.Error as err:
    print(f"Error: {err}")
    exit(1)

# Open serial port
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600)  # Adjust port and baudrate as needed
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit(1)

# Initialize AWS IoT MQTT client
myMQTTClient = AWSIoTMQTTClient("Jason")
myMQTTClient.configureEndpoint(AWS_IOT_ENDPOINT, AWS_IOT_PORT)
myMQTTClient.configureCredentials(AWS_IOT_ROOT_CA, AWS_IOT_PRIVATE_KEY, AWS_IOT_CERTIFICATE)
myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

def message_callback(client, userdata, message):
    print("Received a new message:")
    print(message.payload.decode('utf-8'))
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")
    
    if message.topic == MQTT_TOPIC_DOORBELL_PRESSED:
        try:
            doorbell_info = json.loads(message.payload.decode('utf-8'))
            if doorbell_info.get("door_bell"):
                trigger_doorbell_sound()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
        except Exception as e:
            print(f"Error handling doorbell pressed message: {e}")

# Connect to AWS IoT Core
myMQTTClient.connect()

# Subscribe to the topic
myMQTTClient.subscribe(MQTT_TOPIC_DOORBELL_PRESSED, 1, message_callback)
print(f"Subscribed to topic '{MQTT_TOPIC_DOORBELL_PRESSED}'")

def trigger_doorbell_sound():
    try:
        ser.write(b'DoorbellPressed\n')  # Send command to Arduino to trigger doorbell sound
        print("Doorbell sound triggered on Arduino.")
    except Exception as e:
        print(f"Error triggering doorbell sound on Arduino: {e}")

# Function to trigger living room light on
def trigger_living_room_light_on():
    try:
        ser.write(b'LivingRoomON\n')  # Send command to Arduino to turn on Living Room light
        print("Living Room light turned on.")
    except Exception as e:
        print(f"Error triggering Living Room light on: {e}")

# Function to trigger living room light off
def trigger_living_room_light_off():
    try:
        ser.write(b'LivingRoomOFF\n')  # Send command to Arduino to turn off Living Room light
        print("Living Room light turned off.")
    except Exception as e:
        print(f"Error triggering Living Room light off: {e}")

# Function to trigger living room light auto detect
def trigger_living_room_light_auto():
    try:
        ser.write(b'LivingRoomAUTO\n')  # Send command to Arduino to trigger auto detection for Living Room light
        print("Living Room light set to auto detect mode.")
    except Exception as e:
        print(f"Error triggering Living Room light auto detect: {e}")
        
# Function to trigger bedroom light on
def trigger_bedroom_light_on():
    try:
        ser.write(b'BedroomON\n')  # Send command to Arduino to turn on Bedroom light
        print("Bedroom light turned on.")
    except Exception as e:
        print(f"Error triggering Bedroom light on: {e}")

# Function to trigger bedroom light off
def trigger_bedroom_light_off():
    try:
        ser.write(b'BedRoomOFF\n')  # Send command to Arduino to turn off Bedroom light
        print("Bedroom light turned off.")
    except Exception as e:
        print(f"Error triggering Bedroom light off: {e}")

# Function to trigger bedroom light auto detect
def trigger_bedroom_light_auto():
    try:
        ser.write(b'BedRoomAUTO\n')  # Send command to Arduino to trigger auto detection for Bedroom light
        print("Bedroom light set to auto detect mode.")
    except Exception as e:
        print(f"Error triggering Bedroom light auto detect: {e}")

# Function to insert alert data into the database
def insert_alert_data(alert_type):
    try:
        cursor.execute("INSERT INTO alert_data (alert_type) VALUES (%s)", (alert_type,))
        db.commit()
    except mysql.connector.Error as err:
        print(f"Error inserting alert data: {err}")

# Function to insert location data into the database
def insert_location_data(location_type):
    try:
        cursor.execute("INSERT INTO location_data (location_type) VALUES (%s)", (location_type,))
        cursor.execute("INSERT INTO location_data_counts (location_type, data_count) VALUES (%s, 1) "
                       "ON DUPLICATE KEY UPDATE data_count = data_count + 1", (location_type,))
        db.commit()
    except mysql.connector.Error as err:
        print(f"Error inserting location data: {err}")

# Function to insert temperature data into the database
def insert_temperature_data(temperature):
    try:
        cursor.execute("INSERT INTO temperature_data (temperature) VALUES (%s)", (temperature,))
        db.commit()
    except mysql.connector.Error as err:
        print(f"Error inserting temperature data: {err}")
        
# Function to insert gas data into the database
def insert_gas_data(gas_value):
    try:
        cursor.execute("INSERT INTO gas_data (gas_value) VALUES (%s)", (gas_value,))
        db.commit()
    except mysql.connector.Error as err:
        print(f"Error inserting gas data: {err}")
        
# Function to update light status in the database
def update_light_status(room, status):
    try:
        cursor.execute("UPDATE light_status SET Status = %s, LastUpdated = NOW() WHERE Room = %s", (status, room))
        db.commit()
    except mysql.connector.Error as err:
        print(f"Error updating light status: {err}")

# Function to fetch light status from the database
def fetch_light_status(room):
    try:
        cursor.execute("SELECT Status FROM light_status WHERE Room = %s", (room,))
        result = cursor.fetchone()
        return result[0] if result else None
    except mysql.connector.Error as err:
        print(f"Error fetching light status: {err}")
        return None

try:
    while True:
        line = ser.readline().decode('utf-8').strip()

        if line:
            print(f"Received: {line}")

            # Check for temperature data
            if "Temperature:" in line:
                try:
                    temperature_str = line.split("Temperature: ")[1]
                    temperature = float(temperature_str)
                    insert_temperature_data(temperature)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = json.dumps({"temperature": temperature, "timestamp": timestamp})
                    myMQTTClient.publish("sensor/temperature", payload, 1)
                except (ValueError, IndexError) as e:
                    print(f"Error parsing temperature data: {e}")

            # Check for gas data
            elif "Gas Level:" in line:
                try:
                    gas_value_str = line.split("Gas Level: ")[1]
                    gas_value = int(gas_value_str)
                    insert_gas_data(gas_value)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = json.dumps({"gas_value": gas_value, "timestamp": timestamp})
                    myMQTTClient.publish("sensor/gas", payload, 1)
                except (ValueError, IndexError) as e:
                    print(f"Error parsing gas data: {e}")

            elif "Gas Detected" in line:
                insert_alert_data("Gas Detected")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = json.dumps({"alert": "Gas Detected", "timestamp": timestamp})
                myMQTTClient.publish(MQTT_TOPIC_GAS_DETECTED, payload, 1)

            elif "High Temperature Detected" in line:
                insert_alert_data("High Temperature Detected")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = json.dumps({"alert": "High Temperature Detected", "timestamp": timestamp})
                myMQTTClient.publish(MQTT_TOPIC_HIGH_TEMPERATURE_DETECTED, payload, 1)

            elif "Living Room" in line:
                insert_location_data("Living Room")
                status = fetch_light_status("Living Room")
                if status == "ON":
                    trigger_living_room_light_on()
                elif status == "OFF":
                    trigger_living_room_light_off()
                elif status == "AUTO":
                    trigger_living_room_light_auto()

            elif "Bedroom" in line:
                insert_location_data("Bedroom")
                status = fetch_light_status("Bedroom")
                if status == "ON":
                    trigger_bedroom_light_on()
                elif status == "OFF":
                    trigger_bedroom_light_off()
                elif status == "AUTO":
                    trigger_bedroom_light_auto()

except KeyboardInterrupt:
    print("Terminating the script...")

finally:
    cursor.close()
    db.close()
    ser.close()
    myMQTTClient.disconnect()
    ser.close()
    myMQTTClient.disconnect()
