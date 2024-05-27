import serial
import time
import datetime  # Import datetime module
from collections import deque
import mysql.connector
import requests

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Initialize AWS IoT MQTT client
myMQTTClient = AWSIoTMQTTClient("myClientID")
myMQTTClient.configureEndpoint(
    "a3gax6b93xkabz-ats.iot.us-east-1.amazonaws.com", 8883)
myMQTTClient.configureCredentials("/home/pi/SWE30011/cert/AmazonRootCA1.pem", "/home/pi/SWE30011/cert/f1df5937da03365fbdb7c793d5a4d8e094be7a2edad7781245ebdee29fdf5465-private.pem.key",
                                  "/home/pi/SWE30011/cert/f1df5937da03365fbdb7c793d5a4d8e094be7a2edad7781245ebdee29fdf5465-certificate.pem.crt")
# Infinite offline Publish queueing
myMQTTClient.configureOfflinePublishQueueing(-1)
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect to AWS IoT Core
myMQTTClient.connect()

# Establish database connection
print("Connecting to the database...")
db_connection = mysql.connector.connect(
    host="localhost",
    user="pi",
    password="Koishino.1",
    database="fall_sensor"
)

# Create cursor object
cursor = db_connection.cursor()


def send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


bot_token = '6716374792:AAFjcuTDMuzO5ZGSM2zsWy1gKg4AihLlV54'
chat_id = '5067176118'


def fetch_thresholds():
    cursor.execute("SELECT * FROM settings")
    settings = cursor.fetchone()
    return settings


def fetch_settings_version():
    cursor.execute("SELECT version FROM settings")
    return cursor.fetchone()[0]


def update_settings_version(new_version):
    cursor.execute("UPDATE settings SET version = %s", (new_version,))
    db_connection.commit()
# Function to check movement based on amplitude change


def check_movement(current_amp, prev_amp):
    movement_threshold = 5
    if abs(current_amp - prev_amp) >= movement_threshold:
        print("Person is moving")

# Function to insert data into the database


def insert_data(amp, hr, spo2, ldr):
    if amp != 0 and hr != 0 and spo2 != 0 and ldr != 0:  # Check if values are not 0
        insert_query = "INSERT INTO sensor_data (amp, hr, spo2, ldr) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (amp, hr, spo2, ldr))
        db_connection.commit()
        print("Data inserted into database")
    else:
        print("Some values are 0, data not inserted")


def update_fall_status():
    cursor.execute("UPDATE status SET fall = 1")
    cursor.execute("UPDATE status SET version = version + 1 WHERE id = 1")
    db_connection.commit()
    # Update fall status with timestamp
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = 'We have detect a potential fall in the smartband at ' + current_time

    response = send_message(bot_token, chat_id, message)
    print(response)


def on_buzzer():
    cursor.execute("UPDATE settings SET buzzer_activation = 1")
    db_connection.commit()
    update_settings_version(fetch_settings_version() + 1)

# Function to update the database when heart rate is unusual


def update_hr_status():
    cursor.execute("UPDATE status SET hr_unusual = 1")
    cursor.execute("UPDATE status SET version = version + 1 WHERE id = 1")
    db_connection.commit()

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = 'We have detect a unusual heart rate activity in the smartband at ' + \
        current_time

    response = send_message(bot_token, chat_id, message)
    print(response)
# Function to update the database when SpO2 is unusual


def update_spo2_status():
    cursor.execute("UPDATE status SET spo2_unusual = 1")
    cursor.execute("UPDATE status SET version = version + 1 WHERE id = 1")
    db_connection.commit()

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = 'We have detect a unusual SpO2 activity in the smartband at ' + \
        current_time

    response = send_message(bot_token, chat_id, message)
    print(response)


# Establish serial connection with Arduino
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
ser.reset_input_buffer()

# Define variables and arrays for sensor data and thresholds
ampArraylen = 10
ampArray = []
potential_fall_detected = False
heart_rate_low_start_time = 0
spo2_low_start_time = 0
heart_rate_array = deque(maxlen=10)
spo2_array = deque(maxlen=10)
ldr_array = deque(maxlen=10)
min_data_points = 10
avg_heart_rate = 0
avg_spo2 = 0
avg_ldr = 0
i = 0
prev_amp = None
dark = False

while True:
    # Re-establish database connection inside the loop to ensure freshness of data
    db_connection = mysql.connector.connect(
        host="localhost",
        user="pi",
        password="Koishino.1",
        database="fall_sensor"
    )

    # Re-initialize cursor object
    cursor = db_connection.cursor()

    # Fetch threshold values from the database
    settings = fetch_thresholds()
    low_hr, low_spo2, fallThreshold, fallCheckDuration, fallChangeThreshold, high_spo2, spo2_unusual_time, high_hr, hr_unusual_time, low_ldr, buzzer_state_database, led_state_database, movement_state = settings[
        1], settings[2], settings[3], settings[4], settings[5], settings[6], settings[7], settings[8], settings[9], settings[10], settings[11], settings[12], settings[13]

    try:
        # Read data from serial port
        data = ser.readline().strip().decode('utf-8')
        # print(data)
        if buzzer_state_database == 1:
            ser.write(b'On\n')
        else:
            ser.write(b'Off\n')

        # Check and control LED state based on database setting
        if led_state_database == 1:
            ser.write(b'Dark\n')
        elif led_state_database == 0:
            ser.write(b'Bright\n')
        elif led_state_database == 2 and dark == True:
            ser.write(b'Dark\n')
        else:
            ser.write(b'Bright\n')

        if movement_state == 1:
            ser.write(b'Notify\n')
        else:
            ser.write(b'StopNotify|n')

        # Process sensor data received from Arduino
        if data.startswith("Amp="):
            try:
                Amp = int(data.split('=')[1])
                if prev_amp is not None:
                    check_movement(Amp, prev_amp)
                prev_amp = Amp

                if not potential_fall_detected:
                    if Amp >= fallThreshold:
                        insert_data(prev_amp, avg_heart_rate,
                                    avg_spo2, avg_ldr)
                        print("\tPotential fall detected")
                        potential_fall_detected = True
                else:
                    ampArray.append(Amp)
                    if (len(ampArray) * 100) >= fallCheckDuration:
                        totalChange = sum(abs(Amp - x) for x in ampArray)
                        averageChange = totalChange / len(ampArray)
                        print("Average change in amplitude:", averageChange)
                        if averageChange < fallChangeThreshold:
                            print("Fall Detected")
                            update_fall_status()
                            on_buzzer()
                        else:
                            print("False fall detected")
                        ampArray = []
                        potential_fall_detected = False
            except ValueError as e:
                print("Error parsing data as integer:", e)

        elif data.startswith("HR="):
            try:
                parts = data.split(', ')
                hr_part = parts[0].split('=')[1]
                hr_valid_part = parts[1].split('=')[1]
                heart_rate = int(hr_part)
                heart_rate_valid = int(hr_valid_part)
                if heart_rate_valid == 1 and 10 < heart_rate < 180:
                    heart_rate_array.append(heart_rate)
                    if len(heart_rate_array) >= min_data_points:
                        avg_heart_rate = sum(
                            heart_rate_array) / len(heart_rate_array)
                    print("Bpm:", avg_heart_rate)
                    if low_hr < avg_heart_rate < high_hr:
                        if heart_rate_low_start_time == 0:
                            heart_rate_low_start_time = time.time()
                        elif time.time() - heart_rate_low_start_time > hr_unusual_time:
                            update_hr_status()
                            print("Unusual heart rate detected")
                            on_buzzer()
                            heart_rate_low_start_time = 0
                    else:
                        heart_rate_low_start_time = 0
            except ValueError as e:
                print("Error parsing data as integer:", e)

        elif data.startswith("SPO2="):
            try:
                parts = data.split(', ')
                spo2_part = parts[0].split('=')[1]
                spo2_valid_part = parts[1].split('=')[1]
                spo2 = int(spo2_part)
                spo2_valid = int(spo2_valid_part)
                if spo2_valid == 1 and 70 < spo2 < 100:
                    spo2_array.append(spo2)
                    if len(spo2_array) >= min_data_points:
                        avg_spo2 = sum(spo2_array) / len(spo2_array)
                        print("Average SpO2:", avg_spo2)
                    if low_spo2 < avg_spo2 < high_spo2:
                        if spo2_low_start_time == 0:
                            spo2_low_start_time = time.time()
                        elif time.time() - spo2_low_start_time > spo2_unusual_time:
                            print("Unusual spo2 detected")
                            update_spo2_status()
                            on_buzzer()
                            spo2_low_start_time = 0
                    else:
                        spo2_low_start_time = 0
            except ValueError as e:
                print("Error parsing data as integer:", e)

        elif data.startswith("LDR="):
            try:
                ldr_value = int(data.split('=')[1])
                ldr_array.append(ldr_value)
                if len(ldr_array) >= min_data_points:
                    avg_ldr = sum(ldr_array) / len(ldr_array)
                    if avg_ldr < low_ldr:
                        print("Dark")
                        dark = True
                    else:
                        dark = False
            except ValueError as e:
                print("Error parsing data as integer:", e)

        elif data == "SOS_BUTTON_PRESSED":
            update_fall_status()
            print("SOS button pressed")
            on_buzzer()

        elif data == "stop":
            cursor.execute("UPDATE settings SET buzzer_activation = 0")
            db_connection.commit()
            update_settings_version(fetch_settings_version() + 1)

        # Insert data into the database every 300 iterations
        if i == 1000:
            insert_data(prev_amp, avg_heart_rate, avg_spo2, avg_ldr)
            i = 0
        else:
            i += 1

    except Exception as e:
        print("Error reading data from serial port:", e)
