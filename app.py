from flask import Flask, render_template, jsonify, request
import mysql.connector
from flask import request
from datetime import datetime, timedelta
from pytz import timezone, utc
from threading import Thread, Event
import time
import pytz
app = Flask(__name__)

# Function to establish database connection


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

# # Function to fetch threshold settings from the database
def fetch_thresholds():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM settings")
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
            "SELECT * FROM notifications WHERE read = FALSE ORDER BY timestamp DESC")
    elif filter_option == 'read':
        cursor.execute(
            "SELECT * FROM notifications WHERE read = TRUE ORDER BY timestamp DESC")
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
            "UPDATE notifications SET read = TRUE WHERE id = %s", (notification_id,))

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
        return jsonify({'rfid': rfid, 'message': message})
    else:
        return jsonify({'error': 'No data available'})
    
@app.route('/smartdoor_status')
def get_smartdoor_data():
    data = fetch_smartdoor_status()
    if data:
        door_status = data.get('door_status')
        led_status = data.get('led_status')
        timestamp = data.get('timestamp')
        return jsonify({'door_status': door_status, 'led_status': led_status, 'timestamp': timestamp})
    else:
        return jsonify({'error': 'No data available'})

@app.route('/settings')
def settings():
    return render_template('settings.html')


def get_movement_data():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    # Calculate the timestamp 30 minutes ago
    thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
    cursor.execute(
        'SELECT amp, timestamp FROM sensor_data WHERE timestamp >= %s', (thirty_minutes_ago,))
    data = cursor.fetchall()
    db_connection.close()
    return data

# Function to analyze activity level


def analyze_activity(movement_data):
    if not movement_data:
        return {'average_amplitude': 0}
    total_amplitude = sum(data[0] for data in movement_data)
    average_amplitude = total_amplitude / len(movement_data)
    return {'average_amplitude': average_amplitude}

# Function to notify user by turning on the buzzer


def notify_user():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    # Update the buzzer_activation value to True in the settings table
    cursor.execute("UPDATE settings SET buzzer_activation = 2")
    db_connection.commit()
    db_connection.close()


def generate_recommendations(average_amplitude):
    if average_amplitude < 0.5:
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


@app.route('/insights')
def insights():
    # Get movement data from the database
    movement_data = get_movement_data()

    # Analyze activity level
    activity_metrics = analyze_activity(movement_data)

    # Generate recommendations based on activity level
    recommendations = generate_recommendations(
        activity_metrics['average_amplitude'])

    # Check if activity level is below threshold and notify user
    if activity_metrics['average_amplitude'] < 1:
        notify_user()

    local_timezone = pytz.timezone('Asia/Singapore')

    # Format data for the graph
    activity_data = [
        {'timestamp': data[1].strftime(
            '%Y-%m-%d %H:%M:%S'), 'amp': data[0]}
        for data in movement_data
    ]

    # Render the insights template with the activity metrics, activity data, and recommendations
    return render_template('insights.html', activity_metrics=activity_metrics, activity_data=activity_data, recommendations=recommendations)


@app.route('/get_thresholds')
def get_thresholds():
    thresholds = fetch_thresholds()
    return jsonify(thresholds)


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


@app.route('/history')
def history():
    db_connection = connect_to_database()
    cursor = db_connection.cursor()
    cursor.execute("SELECT amp, hr, spo2, ldr, timestamp FROM sensor_data")
    sensor_data = cursor.fetchall()
    return render_template('history.html', sensor_data=sensor_data)


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


def fetch_data_by_timestamp(timestamp):
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM sensor_data WHERE timestamp = %s', (timestamp,))
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
