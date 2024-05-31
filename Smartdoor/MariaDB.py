import datetime
import time
import serial
import mysql.connector
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from threading import Thread

# Define Arduino serial port
device = '/dev/ttyACM0'  # Update this to your correct serial port
arduino = serial.Serial(device, 9600)
arduino.reset_input_buffer()

# Connect to the database
mydb = mysql.connector.connect(
    host="localhost",
    user="pi",  # Replace with your MySQL username
    password="pass1234",  # Replace with your MySQL password
    database="sensor_db"  # Ensure this is your database name
)

def reconnect_local_db():
    return mysql.connector.connect(
        host="localhost",
        user="pi",
        password="pass1234",
        database="sensor_db"
    )

# Create a cursor object
cursor = mydb.cursor()

# Create the rfid_access table if it doesn't exist
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rfid_access (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(255) UNIQUE NOT NULL
        )
    """)
    print("Table 'rfid_access' created successfully.")
except mysql.connector.Error as err:
    print("Error creating table: ", err)

# Create the access_logs table if it doesn't exist
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            rfid VARCHAR(255),
            message VARCHAR(255),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("Table 'access_logs' created successfully.")
except mysql.connector.Error as err:
    print("Error creating table: ", err)

# Create the status_logs table if it doesn't exist
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_logs (
            id INT PRIMARY KEY,
            door_status VARCHAR(255),
            led_status VARCHAR(255),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            version INT(11) DEFAULT 1
        )
    """)
    print("Table 'status_logs' created successfully.")
except mysql.connector.Error as err:
    print("Error creating table: ", err)

# Ensure there's always a record to update
try:
    cursor.execute("""
        INSERT INTO status_logs (id, door_status, led_status) VALUES (1, 'Closed', 'Closed')
        ON DUPLICATE KEY UPDATE id=id;
    """)
    mydb.commit()
    print("Initial record ensured in status_logs table.\n")
except mysql.connector.Error as err:
    print("Error ensuring initial record: ", err)

def update_door_status(status):
    try:
        cursor.execute("""
            UPDATE status_logs
            SET door_status = %s
            WHERE id = 1
        """, (status,))
        # Fetch the current version number
        cursor.execute(
            "SELECT version FROM status_logs ORDER BY version DESC LIMIT 1")
        current_version = cursor.fetchone()[0]
        new_version = current_version + 1
        
        cursor.execute("UPDATE status_logs SET version = %s", (new_version,))
        
    # Update the version number
        mydb.commit()
    except mysql.connector.Error as err:
        print("Error updating door status: ", err)

# Function to check the current door status from the database
def get_door_status():
    try:
        cursor.execute("SELECT door_status FROM status_logs WHERE id = 1")
        result = cursor.fetchone()
        return result[0] if result else None
    except mysql.connector.Error as err:
        print("Error fetching door status: ", err)
        return None
    
def get_led_status():
    try:
        cursor.execute("SELECT led_status FROM status_logs WHERE id = 1")
        result = cursor.fetchone()
        return result[0] if result else None
    except mysql.connector.Error as err:
        print("Error fetching led status: ", err)
        return None
    
def get_rfid_access():
    try:
        cursor.execute("SELECT * FROM rfid_access")
        result = cursor.fetchall()
        
        # Check if any results were fetched
        if not result:
            return []
        
        # Assuming the column names are id, rfid_code, access_level, timestamp
        column_names = [desc[0] for desc in cursor.description]
        
        # Creating a list of dictionaries, each dictionary represents a row
        rfid_access_list = []
        for row in result:
            row_dict = dict(zip(column_names, row))
            rfid_access_list.append(row_dict)
        
        # Return the list of dictionaries
        return rfid_access_list

    except mysql.connector.Error as err:
        print("Error fetching RFID access: ", err)
        return []
    
# Callback function to process incoming messages
def message_callback(client, userdata, message):
    print("Received a new message:")
    print(message.payload.decode('utf-8'))
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")
    
    # If the message indicates a fall detected, open the door
    if '"fall_detected": true' in message.payload.decode('utf-8'):
        # Update door status to "Open"
        update_door_status("Open")
        print("Door Status: Open")
        arduino.write(b"dooropen\n")
    else:
        # Update door status to "Closed"
        update_door_status("Closed")
        print("Door Status: Closed")
        arduino.write(b"doorclose\n")
        
# Initialize AWS IoT MQTT client
myMQTTClient = AWSIoTMQTTClient("Wilson")
myMQTTClient.configureEndpoint(
    "a3gax6b93xkabz-ats.iot.us-east-1.amazonaws.com", 8883)
myMQTTClient.configureCredentials("/home/pi/swe30011/certWilson/AmazonRootCA1.pem", "/home/pi/swe30011/certWilson/ca5dabe6a2b5b5f0cd626543aa9bd8b430e322fd943bf3b4027460df6666945e-private.pem.key",
                                  "/home/pi/swe30011/certWilson/ca5dabe6a2b5b5f0cd626543aa9bd8b430e322fd943bf3b4027460df6666945e-certificate.pem.crt")
# Infinite offline Publish queueing
myMQTTClient.configureOfflinePublishQueueing(-1)
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect to AWS IoT Core
myMQTTClient.connect()

current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Subscribe to the topic
myMQTTClient.subscribe("fall_sensor/fall_detection", 1, message_callback)
print("Subscribed to topic 'fall_sensor/fall_detection'")

payload = '{"door_bell": true, "timestamp": "' + current_time + '"}'
myMQTTClient.publish("smart_door/doorbell_detection", payload, 0)

doorbell = False

def arduino_loop():
    previousLdrStatus = -1
    global doorbell
    door_status = ""
    led_status = ""
    # Variable to store previous LDR status (-1 means uninitialized)
    while True:
        # Read data from Arduino
        try:
            
            global mydb, cursor
            mydb = reconnect_local_db()
            cursor = mydb.cursor()
            
            # Fetch authorized RFIDs from the database
            cursor.execute("SELECT * FROM rfid_access")
            authorized_rfids = [str(row[1]).strip() for row in cursor.fetchall()]

            line = arduino.readline().decode('utf-8', errors='ignore').strip()
            door_status = get_door_status()
            led_status = get_led_status()
            authorized_rfids = get_rfid_access()
            
            if door_status == "Open":
                arduino.write(b'dooropen\n')  
            else:
                arduino.write(b'doorclose\n')
                
            if led_status == "Open":
                arduino.write(b'ledopen\n')
            elif led_status == "Closed":
                arduino.write(b'ledclose\n')
            else:
                arduino.write(b'auto\n')

            if line.startswith("UID tag:"):
                # Parse the RFID and message from the Arduino output
                parts = line.split()
                rfid = " ".join(parts[2:]).strip()  # Extract the UID part and strip whitespace
                message_line = arduino.readline().decode('utf-8', errors='ignore').strip()
                message_parts = message_line.split(":")
                message = message_parts[1].strip() if len(message_parts) > 1 else ""

                # Print the required output
                print(f"UID tag: {rfid}")
                print(f"Message: {message}\n")

                # Log the access attempt
                cursor.execute(
                    "INSERT INTO access_logs (rfid, message) VALUES (%s, %s)", (rfid, message))
                mydb.commit()

                # Check if the RFID is authorized
                if rfid in [entry['uid'] for entry in authorized_rfids]:
                    print("Authorized access granted.\n")
                    arduino.write(b'Authorized\n')
                    update_door_status("Open")
                    print("Door Status: Open")
                
                # Optionally, you can add a delay here if needed
                    time.sleep(2)  # Wait for 5 seconds

                # Update door status to "Closed" after the delay
                    update_door_status("Closed")
                    print("Door Status: Closed")
                else:
                    print("Unauthorized access denied.\n")
                    arduino.write(b"Unauthorized\n")
                    update_door_status("Closed")
                   
        
    # Debug: Print the UID and authorization message before inserting into the database
                print(f"Inserting into access_logs: UID = {rfid}, Message = {message}")

    # Insert data into the access_logs table
                sql = "INSERT INTO access_logs (rfid, message) VALUES (%s, %s)"
                val = (rfid, message)
                cursor.execute(sql, val)
                mydb.commit()
                 
            elif line == "Button Pressed":
                    if not doorbell:
                        doorbell = True
                        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        payload = '{"door_bell": true, "timestamp": "' + current_time + '"}'
                        myMQTTClient.publish("smart_door/doorbell_detection", payload, 1)
                        print("Door bell sent:", payload)
                    else:
                        doorbell = False
            
            elif line == "Button2 Pressed":
                # Log entry with empty RFID and message "Outside"
                sql = "INSERT INTO access_logs (rfid, message) VALUES (%s, %s)"
                val = ("", "Outside")
                cursor.execute(sql, val)
                mydb.commit()
                
                # Update door status to "Open"
                update_door_status("Open")
                print("Door Status: Open")
                
                # Optionally, you can add a delay here if needed
                time.sleep(5)  # Wait for 5 seconds

                # Update door status to "Closed" after the delay
                update_door_status("Closed")
                print("Door Status: Closed")
                        
            elif line.startswith("LDR Value:"):
                
                if led_status != "Open" or led_status != "Closed":
                    # Parse the LDR value from the Arduino output
                    ldr_value = int(line.split(":")[1].strip())

                    # Update the led_status in the status_logs table
                    sql = """
                        UPDATE status_logs
                        SET led_status = %s
                        WHERE id = 1
                    """
                    val = (led_status,)
                    cursor.execute(sql, val)
                    mydb.commit()

        except (mysql.connector.Error, ValueError) as err:
            print("Error processing data:", err)

# Run the arduino loop in a separate thread
arduino_thread = Thread(target=arduino_loop)
arduino_thread.start()

# Keep the script running to receive messages
while True:
    pass