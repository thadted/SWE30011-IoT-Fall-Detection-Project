from flask import Flask, render_template, jsonify, request
import mysql.connector
from flask import request
from datetime import datetime, timedelta
from pytz import timezone, utc
from threading import Thread, Event
import time
import pytz
import threading
app = Flask(__name__)
import requests
# Function to establish database connection


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
chat_id = '-4213740719'

def connect_to_database():
    return mysql.connector.connect(
        host="database-1.cjdvhndhcwh8.us-east-1.rds.amazonaws.com",
        user="admin",
        password="12345678",
        database="fall_sensor"
    )

# Function to fetch data from the database


def fetch_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    cursor.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1')
    data = cursor.fetchone()
    db_connection.close()
    return data


def fetch_status():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM status WHERE id = 1")
    status_data = cursor.fetchone()
    cursor.close()
    db_connection.close()
    return status_data


def fetch_smartdoor_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 1")
    status_data = cursor.fetchone()
    db_connection.close()
    return status_data


def fetch_smartdoor_status():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM status_logs ORDER BY timestamp DESC LIMIT 1")
    status_data = cursor.fetchone()
    db_connection.close()
    return status_data

# Function to fetch data from the temperature_data table


@app.route('/temperature_data')
def fetch_temperature_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM temperature_data ORDER BY timestamp DESC LIMIT 1')
    data = cursor.fetchone()
    db_connection.close()
    return data

# Function to fetch data from the gas_data table


@app.route('/gas_data')
def fetch_gas_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM gas_data ORDER BY timestamp DESC LIMIT 1')
    data = cursor.fetchone()
    db_connection.close()
    return data

# Function to fetch data from the location_data table


@app.route('/location_data')
def fetch_location_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM location_data ORDER BY timestamp DESC LIMIT 1')
    data = cursor.fetchone()
    db_connection.close()
    return data


#light

# Function to fetch LED status from the database
def fetch_led_status(room):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute('SELECT Status FROM light_status WHERE Room = %s', (room,))
        result = cursor.fetchone()
        db_connection.close()
        return result['Status'] if result else None
    except Exception as e:
        print(f"Error fetching LED status: {str(e)}")
        return None

# Function to update LED status in the database
def update_led_status(room, status):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute('UPDATE light_status SET Status = %s WHERE Room = %s', (status, room))
        db_connection.commit()
        db_connection.close()
        return True, "LED status updated successfully."
    except Exception as e:
        return False, f"Error updating LED status: {str(e)}"

@app.route('/change_status', methods=['POST'])
def change_status():
    room = request.form.get('room')
    status = request.form.get('status')

    # Fetch the current LED status from the database
    current_status = fetch_led_status(room)
    
    if current_status is None:
        return "Room not found in the database.", 404

    if current_status == status:
        return f"LED status for room '{room}' is already '{status}'."

    # Update the LED status in the database
    success, message = update_led_status(room, status)
    
    if success:
        return message
    else:
        return message, 500  # Return a server error status code if the update fails


# # Function to fetch threshold settings from the database

def fetch_thresholds():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM settings")
    thresholds = cursor.fetchone()
    cursor.close()
    return thresholds

def fetch_thresholds_door():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM status_logs")
    thresholds = cursor.fetchone()
    cursor.close()
    return thresholds
    
# # Function to save threshold value


def save_threshold(name, value):
    db_connection = connect_to_database()
    cursor = db_connection.cursor()

    # Update the threshold value
    cursor.execute(f"UPDATE settings SET {name} = %s", (value,))

    # Fetch the current version number
    cursor.execute(
        "SELECT version FROM settings ORDER BY version DESC LIMIT 1")
    current_version = cursor.fetchone()[0]
    new_version = current_version + 1

    # Update the version number
    cursor.execute("UPDATE settings SET version = %s", (new_version,))

    db_connection.commit()
    cursor.close()
    db_connection.close()

    return 'Threshold value saved successfully'

def save_threshold_environment(name, value):
    db_connection = connect_to_database()
    cursor = db_connection.cursor()

    # Update the threshold value
    cursor.execute(f"UPDATE settings SET {name} = %s", (value,))

    # Fetch the current version number
    cursor.execute(
        "SELECT version FROM settings ORDER BY version DESC LIMIT 1")
    current_version = cursor.fetchone()[0]
    new_version = current_version + 1

    # Update the version number
    cursor.execute("UPDATE settings SET version = %s", (new_version,))

    db_connection.commit()
    cursor.close()
    db_connection.close()

    return 'Threshold value saved successfully'


def save_threshold_door(name, value):
    db_connection = connect_to_database()
    cursor = db_connection.cursor()

    # Update the threshold value
    cursor.execute(f"UPDATE status_logs SET {name} = %s", (value,))

    # Fetch the current version number
    cursor.execute(
        "SELECT version FROM status_logs ORDER BY version DESC LIMIT 1")
    current_version = cursor.fetchone()[0]
    new_version = current_version + 1

    # Update the version number
    cursor.execute("UPDATE status_logs SET version = %s", (new_version,))

    db_connection.commit()
    cursor.close()
    db_connection.close()

    return 'Threshold value saved successfully'


def save_rfid(name, value):
    db_connection = connect_to_database()
    cursor = db_connection.cursor()

    try:
        # Insert the RFID value
        cursor.execute("INSERT INTO rfid_access (uid) VALUES (%s)", (value,))
        db_connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return 'Failed to save the RFID value'
    finally:
        cursor.close()
        db_connection.close()

    return 'RFID value saved successfully'


def fetch_previous_status():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT fall, hr_unusual, spo2_unusual FROM status WHERE id = 1")
    previous_status = cursor.fetchone()
    cursor.close()
    db_connection.close()
    return previous_status


def insert_notification(type, status):
    db_connection = connect_to_database()
    cursor = db_connection.cursor()

    # Define the local timezone
    local_timezone = pytz.timezone('Asia/Singapore')

    # Get the current UTC time
    utc_time = datetime.utcnow()

    # Convert UTC time to local time
    local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_timezone)

    # Format the local time as a string
    formatted_time = local_time.strftime('%Y-%m-%d %H:%M:%S')

    # Construct the message based on the notification type and local time
    if type == 'fall':
        message = f"We detected a fall in the smartband at {formatted_time}"
    elif type == 'hr_unusual':
        message = f"We detected unusual heart rate activity in the smartband at {formatted_time}"
    elif type == 'spo2_unusual':
        message = f"We detected unusual SpO2 activity in the smartband at {formatted_time}"

    # Insert the notification into the database
    cursor.execute(
        "INSERT INTO notifications (type, message, status, timestamp) VALUES (%s, %s, %s, %s)", (type, message, status, formatted_time))

    # Commit the transaction and close the cursor and database connection
    db_connection.commit()
    cursor.close()
    db_connection.close()


def detect_and_notify_changes():
    previous_status = fetch_previous_status()

    while not stop_event.is_set():
        current_status = fetch_status()

        # Check for fall status change
        if current_status['fall'] == 1 and (previous_status is None or previous_status['fall'] != 1):
            insert_notification('fall', 1)
            # Update immediately after inserting notification
            previous_status['fall'] = 1

        # Check for unusual heart rate status change
        if current_status['hr_unusual'] == 1 and (previous_status is None or previous_status['hr_unusual'] != 1):
            insert_notification('hr_unusual', 1)
            # Update immediately after inserting notification
            previous_status['hr_unusual'] = 1

        # Check for unusual SpO2 status change
        if current_status['spo2_unusual'] == 1 and (previous_status is None or previous_status['spo2_unusual'] != 1):
            insert_notification('spo2_unusual', 1)
            # Update immediately after inserting notification
            previous_status['spo2_unusual'] = 1

        # Reset the previous status fields that have returned to normal (0)
        if current_status['fall'] == 0:
            previous_status['fall'] = 0
        if current_status['hr_unusual'] == 0:
            previous_status['hr_unusual'] = 0
        if current_status['spo2_unusual'] == 0:
            previous_status['spo2_unusual'] = 0

        time.sleep(10)  # Check every 10 seconds


@app.route('/')
def index():
    status_data = fetch_status()
    return render_template('index.html', status_data=status_data)


@app.route('/smartband')
def smartband():
    status_data = fetch_status()
    return render_template('smartband.html', status_data=status_data)


@app.route('/smartdoor')
def smartdoor():
    status_data = fetch_smartdoor_data()
    return render_template('smartdoor.html', status_data=status_data)


@app.route('/home')
def home():
    status_data = fetch_status()
    return render_template('index.html', status_data=status_data)


def fetch_notifications(filter_option):
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)

    if filter_option == 'unread':
        cursor.execute(
            "SELECT * FROM notifications WHERE `read` = FALSE ORDER BY timestamp DESC")
    elif filter_option == 'read':
        cursor.execute(
            "SELECT * FROM notifications WHERE `read` = TRUE ORDER BY timestamp DESC")
    else:
        cursor.execute("SELECT * FROM notifications ORDER BY timestamp DESC")

    notifications_data = cursor.fetchall()
    cursor.close()
    db_connection.close()
    return notifications_data

# Route to display notifications
@app.route('/notifications')
def notifications():
    filter_option = request.args.get('filter', 'all')
    notifications_data = fetch_notifications(filter_option)

    return render_template('notifications.html', notifications=notifications_data, filter_option=filter_option)


@app.route('/mark_read/<int:notification_id>', methods=['POST'])
def mark_read(notification_id):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor()

        # Fetch the notification type to determine which status field to update
        cursor.execute(
            "SELECT type FROM notifications WHERE id = %s", (notification_id,))
        notification_type = cursor.fetchone()[0]

        # Update the respective status field based on the notification type
        if notification_type == 'fall':
            cursor.execute("UPDATE status SET fall = 0 WHERE id = 1")

        elif notification_type == 'hr_unusual':
            cursor.execute("UPDATE status SET hr_unusual = 0 WHERE id = 1")
        elif notification_type == 'spo2_unusual':
            cursor.execute("UPDATE status SET spo2_unusual = 0 WHERE id = 1")

        cursor.execute("UPDATE status SET version = version + 1 WHERE id = 1")
        # Mark the notification as read
        cursor.execute(
            "UPDATE notifications SET `read` = TRUE WHERE id = %s", (notification_id,))

        db_connection.commit()
        cursor.close()
        db_connection.close()

        return jsonify(status='success')
    except Exception as e:
        return str(e), 500


@app.route('/delete_notification/<int:notification_id>', methods=['POST'])
def delete_notification(notification_id):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor()
        cursor.execute("DELETE FROM notifications WHERE id = %s",
                       (notification_id,))
        db_connection.commit()
        cursor.close()
        db_connection.close()
        return 'Notification deleted successfully'
    except Exception as e:
        return str(e), 500


@app.route('/acknowledge_status', methods=['POST'])
def acknowledge_status():
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor()
        cursor.execute(
            "UPDATE status SET fall = 0, hr_unusual = 0, spo2_unusual = 0")
        db_connection.commit()
        cursor.close()
        db_connection.close()
        return 'Status acknowledged successfully'
    except Exception as e:
        # Return the error message with status code 500 (Internal Server Error)
        return str(e), 500


@app.route('/status_data')
def status_data():
    status_data = fetch_status()
    return jsonify(status_data)


@app.route('/data')
def get_data():
    data = fetch_data()
    if data:
        amp, heart_rate, spo2, ldr_value = data[1], data[2], data[3], data[4]
        return jsonify({'amp': amp, 'heart_rate': heart_rate, 'spo2': spo2, 'ldr_value': ldr_value})
    else:
        return jsonify({'error': 'No data available'})


@app.route('/smartdoor_data')
def get_smartdoor_data():
    data = fetch_smartdoor_data()
    if data:
        rfid = data.get('rfid')
        message = data.get('message')
        timestamp = data.get('timestamp')
        return jsonify({'rfid': rfid, 'message': message, 'timestamp': timestamp})
    else:
        return jsonify({'error': 'No data available'})


@app.route('/smartdoor_status')
def get_smartdoor_status():
    data = fetch_smartdoor_status()
    if data:
        door_status = data.get('door_status')
        led_status = data.get('led_status')
        return jsonify({'door_status': door_status, 'led_status': led_status})
    else:
        return jsonify({'error': 'No data available'})

@app.route('/get_uids', methods=['GET'])
def get_uids():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT uid FROM rfid_access")
    uids = cursor.fetchall()
    cursor.close()
    db_connection.close()
    return jsonify(uids)

@app.route('/delete_uid/<uid>', methods=['DELETE'])
def delete_uid(uid):
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM rfid_access WHERE uid = %s", (uid,))
    db_connection.commit()
    cursor.close()
    db_connection.close()
    return jsonify({'message': 'UID deleted successfully'})
    
@app.route('/settings')
def settings():
    return render_template('settings.html')


def get_movement_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)

    # Define the local timezone
    local_timezone = pytz.timezone('Asia/Singapore')

    # Get the current UTC time and convert it to the local time
    utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)
    local_time = utc_time.astimezone(local_timezone)

    # Calculate the timestamp 30 minutes ago in local time
    thirty_minutes_ago_local = local_time - timedelta(minutes=30)

    # Convert 30 minutes ago local time back to UTC for the database query
    thirty_minutes_ago_utc = thirty_minutes_ago_local.astimezone(pytz.utc)

    # Query the database for data in the last 30 minutes
    cursor.execute(
        'SELECT amp, timestamp FROM sensor_data WHERE timestamp >= %s',
        (thirty_minutes_ago_utc,)
    )
    data = cursor.fetchall()

    db_connection.close()
    return data



# Function to analyze activity level


def analyze_activity(movement_data):
    if not movement_data:
        return {'average_amplitude': 0, 'movement_detected': False}

    # Calculate the differences between consecutive amplitude values
    amplitude_changes = [
        abs(movement_data[i]['amp'] - movement_data[i - 1]['amp'])
        for i in range(1, len(movement_data))
    ]

    # Calculate the average change in amplitude
    average_change = sum(amplitude_changes) / \
        len(amplitude_changes) if amplitude_changes else 0

    # Define a threshold for detecting movement
    movement_threshold = 0.2  # You can adjust this value based on your sensor's sensitivity

    # Determine if movement is detected
    movement_detected = average_change > movement_threshold

    return {
        'average_amplitude': average_change,
        'movement_detected': movement_detected
    }



def turn_off_buzzer():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    cursor.execute("UPDATE settings SET movement = 0")
    db_connection.commit()

    cursor.execute(
        "SELECT version FROM settings ORDER BY version DESC LIMIT 1")
    current_version = cursor.fetchone()[0]
    new_version = current_version + 1

    # Update the version number
    cursor.execute("UPDATE settings SET version = %s", (new_version,))
    db_connection.commit()
    db_connection.close()

# Function to notify user by turning on the buzzer


def notify_user():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    cursor.execute("UPDATE settings SET movement = 1")

    cursor.execute(
        "SELECT version FROM settings ORDER BY version DESC LIMIT 1")
    current_version = cursor.fetchone()[0]
    new_version = current_version + 1

    cursor.execute("UPDATE settings SET version = %s", (new_version,))
    db_connection.commit()
    db_connection.close()

    threading.Timer(5, turn_off_buzzer).start()


def check_movement():
    movement_data = get_movement_data()
    activity_metrics = analyze_activity(movement_data)

    if activity_metrics['average_amplitude'] < 1:
        notify_user()

    # Schedule the next check after 30 minutes
    threading.Timer(30 * 60, check_movement).start()


def generate_recommendations(average_amplitude):
    if average_amplitude < 1:
        return [
            "Take a short walk every hour.",
            "Do some stretching exercises.",
            "Try a quick workout routine.",
            "Engage in light physical activities like cleaning or organizing."
        ]
    else:
        return [
            "Great job! Keep up the good activity level.",
            "Consider incorporating some strength training exercises.",
            "Try a new fitness class or activity to keep things interesting.",
            "Maintain regular movement breaks throughout your day."
        ]
        
#location analyze
def get_location_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM location_data WHERE timestamp >= NOW() - INTERVAL 1 HOUR')
    data = cursor.fetchall()
    db_connection.close()
    return data

#location analyze
def get_time_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM access_logs WHERE timestamp >= NOW() - INTERVAL 1 HOUR')
    data = cursor.fetchall()
    db_connection.close()
    return data


@app.route('/last_access_per_day')
def last_access_per_day():
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT DATE(timestamp) as date, MAX(timestamp) as last_access_time FROM access_logs GROUP BY DATE(timestamp)"
        )
        results = cursor.fetchall()

        # Calculate average access time in seconds since midnight
        total_seconds = 0
        count = len(results)
        dates_with_access = {entry['date'] for entry in results}

        # Get the date range
        if results:
            start_date = min(dates_with_access)
            end_date = max(dates_with_access)
        else:
            start_date = end_date = datetime.today().date()

        # Check for missing days
        missing_days = []
        current_date = start_date
        while current_date <= end_date:
            if current_date not in dates_with_access:
                missing_days.append(current_date)
            current_date += timedelta(days=1)

        # Send a Telegram message if there are missing days
        if missing_days:
            message = f"No access logs found for the following days: {', '.join(map(str, missing_days))}"
            send_message(message)

        for entry in results:
            time = entry['last_access_time']
            if isinstance(time, str):
                time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
            seconds = time.hour * 3600 + time.minute * 60 + time.second
            total_seconds += seconds

        average_seconds = total_seconds / count if count > 0 else 0
        average_time = (
            datetime.min + timedelta(seconds=average_seconds)).time()

        cursor.close()
        db_connection.close()

        # Formatting the results properly for JSON response
        formatted_results = [
            {
                'date': entry['date'].strftime('%Y-%m-%d'),
                'last_access_time': entry['last_access_time'].strftime('%Y-%m-%d %H:%M:%S')
            } for entry in results
        ]

        return jsonify({
            'average_access_time': average_time.strftime("%H:%M:%S"),
            'data': formatted_results
        })

    except Exception as e:
        # Return error message if any exception occurs
        return jsonify({'error': str(e)}), 500

@app.route('/insights')
def insights():
    # Get movement data from the database
    movement_data = get_movement_data()

    # Analyze activity level
    activity_metrics = analyze_activity(movement_data)

    # Generate recommendations based on activity level
    recommendations = generate_recommendations(
        activity_metrics['average_amplitude'])

    # Format data for the graph
    activity_data = [
        {'timestamp': data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'), 'amp': data['amp']}
        for data in movement_data
    ]

    # Fetch location analysis data
    location_data = get_location_data()

    # Fetch location analysis data
    time_data = get_time_data()

    # Format location data for the graph
    formatted_location_data = [
        {'timestamp': data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'), 'location_type': data['location_type']}
        for data in location_data
    ]

    # Format location data for the graph
    formatted_time_data = [
        {'timestamp': data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'), 'message': data['message']}
        for data in time_data
    ]

    # Render the insights template with the activity metrics, activity data, recommendations, and location analysis data
    return render_template('insights.html', activity_metrics=activity_metrics, activity_data=activity_data, recommendations=recommendations, location_data=location_data, formatted_location_data=formatted_location_data, time_data=time_data, formatted_time_data=formatted_time_data)

# Function to fetch LED status from the database
def fetch_led_status(room):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute('SELECT Status FROM light_status WHERE Room = %s', (room,))
        result = cursor.fetchone()
        db_connection.close()
        return result['Status'] if result else None
    except Exception as e:
        print(f"Error fetching LED status: {str(e)}")
        return None

# Function to update LED status in the database
def update_led_status(room, status):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute('UPDATE light_status SET Status = %s WHERE Room = %s', (status, room))
        db_connection.commit()
        db_connection.close()
        return True, "LED status updated successfully."
    except Exception as e:
        return False, f"Error updating LED status: {str(e)}"

@app.route('/change_status', methods=['POST'])
def change_status():
    room = request.form.get('room')
    status = request.form.get('status')

    # Fetch the current LED status from the database
    current_status = fetch_led_status(room)
    
    if current_status is None:
        return "Room not found in the database.", 404

    if current_status == status:
        return f"LED status for room '{room}' is already '{status}'."

    # Update the LED status in the database
    success, message = update_led_status(room, status)
    
    if success:
        return message
    else:
        return message, 500  # Return a server error status code if the update fails
    
#Smartband
@app.route('/get_thresholds')
def get_thresholds():
    thresholds = fetch_thresholds()
    return jsonify(thresholds)

#Environment
@app.route('/get_thresholds_environment')
def get_thresholds_environment():
    thresholds = fetch_thresholds()
    return jsonify(thresholds)

#Smartdoor
@app.route('/get_thresholds_door')
def get_thresholds_door():
    thresholds = fetch_thresholds_door()
    return jsonify(thresholds)


check_movement()

#Smartband
@app.route('/save_threshold', methods=['POST'])
def save_threshold_route():
    try:
        name = request.form['name']
        value = request.form['value']
        save_threshold(name, value)
        return 'Threshold value saved successfully'
    except Exception as e:
        # Return the error message with status code 500 (Internal Server Error)
        return str(e), 500

#Environment
@app.route('/save_threshold_environment', methods=['POST'])
def save_threshold_route_environment():
    try:
        name = request.form['name']
        value = request.form['value']
        save_threshold_environment(name, value)
        return 'Threshold value saved successfully'
    except Exception as e:
        # Return the error message with status code 500 (Internal Server Error)
        return str(e), 500
    
#Smartdoor
@app.route('/save_threshold_door', methods=['POST'])
def save_threshold_route_door():
    try:
        name = request.form['name']
        value = request.form['value']
        save_threshold_door(name, value)
        return 'Threshold value saved successfully'
    except Exception as e:
        # Return the error message with status code 500 (Internal Server Error)
        return str(e), 500

@app.route('/save_rfid', methods=['POST'])
def save_threshold_rfid():
    try:
        name = request.form['name']
        value = request.form['value']
        save_rfid(name, value)
        return 'Threshold value saved successfully'
    except Exception as e:
        # Return the error message with status code 500 (Internal Server Error)
        return str(e), 500
    
@app.route('/actuator_status')
def get_actuator_status():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    cursor.execute("SELECT buzzer_activation, led_activation FROM settings")
    buzzer_state, led_state = cursor.fetchone()

    # Convert LED activation value to appropriate string
    if led_state == 2:
        led_state = "Auto"
    else:
        led_state = bool(led_state)

    db_connection.close()
    return jsonify({'buzzer_state': bool(buzzer_state), 'led_state': led_state})

#All
@app.route('/history')
def history():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()

    # Fetching sensor data
    cursor.execute("SELECT amp, hr, spo2, ldr, timestamp FROM sensor_data")
    sensor_data = cursor.fetchall()
    
    # Fetching environment data (assuming temperature and gas values)
    cursor.execute("SELECT temperature, timestamp FROM temperature_data")
    temperature_data = cursor.fetchall()
    
    cursor.execute("SELECT gas_value, timestamp FROM gas_data")
    gas_data = cursor.fetchall()
    
    # Fetching RFID data
    cursor.execute("SELECT rfid, message, timestamp FROM access_logs")
    rfid_data = cursor.fetchall()
    
    return render_template('history.html', sensor_data=sensor_data, temperature_data=temperature_data, gas_data=gas_data, rfid_data=rfid_data)

#Smartband
@app.route('/sensor_data')
def sensor_data():
    start_timestamp = request.args.get('start_timestamp')
    end_timestamp = request.args.get('end_timestamp')

    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)

    if start_timestamp and end_timestamp:
        # Convert start and end timestamps to datetime objects
        start_datetime = datetime.fromisoformat(start_timestamp)
        end_datetime = datetime.fromisoformat(end_timestamp)

        # Convert start and end datetime objects to UTC
        start_utc = start_datetime.astimezone(utc)
        end_utc = end_datetime.astimezone(utc)

        # Filter data based on the timestamp range
        cursor.execute(
            "SELECT amp, hr, spo2, ldr, timestamp FROM sensor_data WHERE timestamp BETWEEN %s AND %s", (start_utc, end_utc))
    else:
        # Otherwise, fetch all data
        cursor.execute("SELECT amp, hr, spo2, ldr, timestamp FROM sensor_data")

    sensor_data = cursor.fetchall()
    cursor.close()
    db_connection.close()
    return jsonify(sensor_data)

#Smartdoor
@app.route('/door_data')
def sensor_data3():
    start_timestamp = request.args.get('start_timestamp')
    end_timestamp = request.args.get('end_timestamp')

    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)

    if start_timestamp and end_timestamp:
        # Convert start and end timestamps to datetime objects
        start_datetime = datetime.fromisoformat(start_timestamp)
        end_datetime = datetime.fromisoformat(end_timestamp)

        # Convert start and end datetime objects to UTC
        start_utc = start_datetime.astimezone(utc)
        end_utc = end_datetime.astimezone(utc)

        # Filter data based on the timestamp range
        cursor.execute(
            "SELECT rfid, message, timestamp FROM access_logs WHERE timestamp BETWEEN %s AND %s", (start_utc, end_utc))
    else:
        # Otherwise, fetch all data
        cursor.execute("SELECT rfid, message, timestamp FROM access_logs")

    sensor_data = cursor.fetchall()
    cursor.close()
    db_connection.close()
    return jsonify(sensor_data)

#Environment
@app.route('/environment_data')
def environment_data():
    start_timestamp = request.args.get('start_timestamp')
    end_timestamp = request.args.get('end_timestamp')

    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)

    if start_timestamp and end_timestamp:
        # Convert start and end timestamps to datetime objects
        start_datetime = datetime.fromisoformat(start_timestamp)
        end_datetime = datetime.fromisoformat(end_timestamp)

        # Convert start and end datetime objects to UTC
        start_utc = start_datetime.astimezone()
        end_utc = end_datetime.astimezone()

        # Fetch temperature data within the timestamp range
        cursor.execute(
            "SELECT temperature, timestamp FROM temperature_data WHERE timestamp BETWEEN %s AND %s",
            (start_utc, end_utc)
        )
        temperature_data = cursor.fetchall()

        # Fetch gas data within the timestamp range
        cursor.execute(
            "SELECT gas_value, timestamp FROM gas_data WHERE timestamp BETWEEN %s AND %s",
            (start_utc, end_utc)
        )
        gas_data = cursor.fetchall()
    else:
        # Fetch all temperature data
        cursor.execute("SELECT temperature, timestamp FROM temperature_data")
        temperature_data = cursor.fetchall()

        # Fetch all gas data
        cursor.execute("SELECT gas_value, timestamp FROM gas_data")
        gas_data = cursor.fetchall()

    cursor.close()
    db_connection.close()

    # Combine temperature and gas data
    combined_data = []
    temp_dict = {entry['timestamp']: entry['temperature'] for entry in temperature_data}
    gas_dict = {entry['timestamp']: entry['gas_value'] for entry in gas_data}

    all_timestamps = set(temp_dict.keys()).union(gas_dict.keys())
    for timestamp in sorted(all_timestamps):
        combined_data.append({
            'timestamp': timestamp,
            'temperature': temp_dict.get(timestamp),
            'gas_value': gas_dict.get(timestamp)
        })

    return jsonify(combined_data)

@app.route('/environment')
def environment():
    temperature_data = fetch_temperature_data()
    gas_data = fetch_gas_data()
    location_data = fetch_location_data()
    return render_template('environment.html', temperature_data=temperature_data, gas_data=gas_data, location_data=location_data)

#Smartband
def fetch_data_by_timestamp(timestamp):
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM sensor_data WHERE timestamp = %s', (timestamp,))
    data = cursor.fetchall()
    db_connection.close()
    return data

#Environment
def fetch_data_by_timestamp2(timestamp):
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM sensor_data WHERE timestamp = %s', (timestamp,))
    data = cursor.fetchall()
    db_connection.close()
    return data

#Smartdoor
def fetch_data_by_timestamp3(timestamp):
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM access_logs WHERE timestamp = %s', (timestamp,))
    data = cursor.fetchall()
    db_connection.close()
    return data


if __name__ == '__main__':
    stop_event = Event()
    monitor_thread = Thread(target=detect_and_notify_changes)
    monitor_thread.start()
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    finally:
        stop_event.set()
        monitor_thread.join()
