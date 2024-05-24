import time
import mysql.connector
from threading import Thread
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import datetime

# Initialize AWS IoT MQTT client
myMQTTClient = AWSIoTMQTTClient("myClientID")
myMQTTClient.configureEndpoint(
    "a3gax6b93xkabz-ats.iot.us-east-1.amazonaws.com", 8883)
myMQTTClient.configureCredentials("/home/pi/SWE30011/cert/AmazonRootCA1.pem",
                                  "/home/pi/SWE30011/cert/f1df5937da03365fbdb7c793d5a4d8e094be7a2edad7781245ebdee29fdf5465-private.pem.key",
                                  "/home/pi/SWE30011/cert/f1df5937da03365fbdb7c793d5a4d8e094be7a2edad7781245ebdee29fdf5465-certificate.pem.crt")
# Infinite offline Publish queueing
myMQTTClient.configureOfflinePublishQueueing(-1)
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect to AWS IoT Core
myMQTTClient.connect()
previous_fall_status = None


def fetch_local_settings(local_cursor):
    local_cursor.execute("SELECT * FROM settings")
    return local_cursor.fetchone()


def fetch_rds_settings(rds_cursor):
    rds_cursor.execute("SELECT * FROM settings")
    return rds_cursor.fetchone()


def update_local_settings(local_cursor, settings):
    new_version = settings[-1]
    update_query = """UPDATE settings SET
                        low_hr = %s, low_spo2 = %s, fall_threshold = %s, fall_check_duration = %s,
                        fall_change_threshold = %s, high_spo2 = %s, spo2_unusual_max_time = %s,
                        high_hr = %s, heart_rate_unusual_max_time = %s, low_ldr = %s, buzzer_activation = %s,
                        led_activation = %s, version = %s"""
    local_cursor.execute(update_query, (*settings[1:-1], new_version))


def update_rds_settings(rds_cursor, settings):
    new_version = settings[-1]
    update_query = """UPDATE settings SET
                        low_hr = %s, low_spo2 = %s, fall_threshold = %s, fall_check_duration = %s,
                        fall_change_threshold = %s, high_spo2 = %s, spo2_unusual_max_time = %s,
                        high_hr = %s, heart_rate_unusual_max_time = %s, low_ldr = %s, buzzer_activation = %s,
                        led_activation = %s, version = %s"""
    rds_cursor.execute(update_query, (*settings[1:-1], new_version))


def fetch_local_status(local_cursor):
    local_cursor.execute("SELECT * FROM status WHERE id = 1")
    return local_cursor.fetchone()


def fetch_rds_status(rds_cursor):
    rds_cursor.execute("SELECT * FROM status WHERE id = 1")
    return rds_cursor.fetchone()


def update_local_status(local_cursor, status):
    update_query = """UPDATE status SET
                        fall = %s, hr_unusual = %s, spo2_unusual = %s, version = %s WHERE id = 1"""
    local_cursor.execute(
        update_query, (status[0], status[1], status[2], status[-1]))


def update_rds_status(rds_cursor, status):
    update_query = """UPDATE status SET
                        fall = %s, hr_unusual = %s, spo2_unusual = %s, version = %s WHERE id = 1"""
    rds_cursor.execute(
        update_query, (status[0], status[1], status[2], status[-1]))


def sync_settings(local_cursor, rds_cursor, rds_db_connection, local_db_connection):
    local_settings = fetch_local_settings(local_cursor)
    rds_settings = fetch_rds_settings(rds_cursor)

    if not local_settings or not rds_settings:
        print("Error: Missing settings data in one of the databases.")
        return

    local_version = local_settings[-1]
    rds_version = rds_settings[-1]

    print(
        f"Local settings version: {local_version}, RDS settings version: {rds_version}")

    if local_version < rds_version:
        print("Updating local settings from RDS settings.")
        update_local_settings(local_cursor, rds_settings)
        local_db_connection.commit()
    elif local_version > rds_version:
        print("Updating RDS settings from local settings.")
        update_rds_settings(rds_cursor, local_settings)
        rds_db_connection.commit()
    else:
        print("No updates needed. Both settings are up to date.")


def message_callback(client, userdata, message):
    print("Received a new message:")
    print(message.payload.decode('utf-8'))
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

    # If the message indicates a high temperature detected, activate the buzzer
    if '"alert": "High Temperature Detected"' in message.payload.decode('utf-8') or '"alert": "Gas Detected"' in message.payload.decode('utf-8'):
        local_db_connection = mysql.connector.connect(
            host="localhost",
            user="pi",
            password="Koishino.1",
            database="fall_sensor"
        )
        local_cursor = local_db_connection.cursor()

        # Fetch the current version
        local_cursor.execute("SELECT version FROM settings")
        current_version = local_cursor.fetchone()[0]

        # Update the settings
        new_version = current_version + 1
        local_cursor.execute(
            "UPDATE settings SET buzzer_activation = 1, version = %s", (new_version,))
        local_db_connection.commit()
        local_cursor.close()
        local_db_connection.close()


def sync_status(local_cursor, rds_cursor, rds_db_connection, local_db_connection):
    global previous_fall_status
    local_status = fetch_local_status(local_cursor)
    rds_status = fetch_rds_status(rds_cursor)

    if not local_status or not rds_status:
        print("Error: Missing status data in one of the databases.")
        return

    local_version = local_status[-1]
    rds_version = rds_status[-1]

    print(
        f"Local status version: {local_version}, RDS status version: {rds_version}")

    if local_version < rds_version:
        print("Updating local status from RDS status.")
        update_local_status(local_cursor, rds_status)
        local_db_connection.commit()
    elif local_version > rds_version:
        print("Updating RDS status from local status.")
        update_rds_status(rds_cursor, local_status)
        rds_db_connection.commit()
    else:
        print("No updates needed. Both status are up to date.")

    # Check fall status and send MQTT message
    fall_status = local_status[0]  # Assuming fall is the first column
    if fall_status != previous_fall_status:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if fall_status == 1:
            payload = '{"fall_detected": true, "timestamp": "' + \
                current_time + '"}'
        else:
            payload = '{"fall_detected": false, "timestamp": "' + \
                current_time + '"}'
        myMQTTClient.publish("fall_sensor/fall_detection",
                             payload, 1)  # Use QoS 1
        previous_fall_status = fall_status


def sync_sensor_data(local_cursor, rds_cursor, rds_db_connection, local_db_connection):
    local_cursor.execute("SELECT * FROM sensor_data_changes")
    changes = local_cursor.fetchall()

    for change in changes:
        if change[1] == 'INSERT':
            rds_cursor.execute("INSERT INTO sensor_data (id, amp, hr, spo2, ldr, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                               (change[2], change[3], change[4], change[5], change[6], change[7]))
        elif change[1] == 'UPDATE':
            rds_cursor.execute("UPDATE sensor_data SET amp=%s, hr=%s, spo2=%s, ldr=%s, timestamp=%s WHERE id=%s",
                               (change[3], change[4], change[5], change[6], change[7], change[2]))

    rds_db_connection.commit()
    local_cursor.execute("DELETE FROM sensor_data_changes")
    local_db_connection.commit()
    print("Local sensor data synced to RDS")


def sync_databases():
    local_db_connection = mysql.connector.connect(
        host="localhost",
        user="pi",
        password="Koishino.1",
        database="fall_sensor"
    )
    local_cursor = local_db_connection.cursor()

    rds_db_connection = mysql.connector.connect(
        host="database-1.cjdvhndhcwh8.us-east-1.rds.amazonaws.com",
        user="admin",
        password="12345678",
        database="fall_sensor"
    )
    rds_cursor = rds_db_connection.cursor()

    while True:
        try:
            # Sync settings based on the latest timestamp
            sync_settings(local_cursor, rds_cursor,
                          rds_db_connection, local_db_connection)

            # Sync status based on the latest timestamp
            sync_status(local_cursor, rds_cursor,
                        rds_db_connection, local_db_connection)

            # Sync sensor data
            sync_sensor_data(local_cursor, rds_cursor,
                             rds_db_connection, local_db_connection)
            myMQTTClient.subscribe(
                "sensor/high_temperature_detected", 1, message_callback)
            myMQTTClient.subscribe("sensor/gas_detected", 1, message_callback)
        except Exception as e:
            print("Error during synchronization:", e)

        time.sleep(5)


if __name__ == "__main__":
    sync_thread = Thread(target=sync_databases)
    sync_thread.start()
