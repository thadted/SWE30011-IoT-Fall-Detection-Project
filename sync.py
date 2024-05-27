import time
import mysql.connector
from threading import Thread

# Fetch functions
def fetch_local_door_settings(local_cursor):
    local_cursor.execute("SELECT * FROM access_logs")
    return local_cursor.fetchall()

def fetch_rds_door_settings(rds_cursor):
    rds_cursor.execute("SELECT * FROM access_logs")
    return rds_cursor.fetchall()

def fetch_local_door_status(local_cursor):
    local_cursor.execute("SELECT * FROM status_logs WHERE id = 1")
    return local_cursor.fetchone()

def fetch_rds_door_status(rds_cursor):
    rds_cursor.execute("SELECT * FROM status_logs WHERE id = 1")
    return rds_cursor.fetchone()

# Update functions
def update_local_door_settings(local_cursor, settings):
    update_query = """UPDATE access_logs SET rfid = %s, message = %s, timestamp = %s WHERE id = %s"""
    for setting in settings:
        local_cursor.execute(update_query, setting)

def update_rds_door_settings(rds_cursor, settings):
    update_query = """UPDATE access_logs SET rfid = %s, message = %s, timestamp = %s WHERE id = %s"""
    for setting in settings:
        rds_cursor.execute(update_query, setting)

def update_local_door_status(local_cursor, status):
    update_query = """UPDATE status_logs SET door_status = %s, led_status = %s, timestamp = %s, version = %s WHERE id = 1"""
    local_cursor.execute(update_query, status[1:])

def update_rds_door_status(rds_cursor, status):
    update_query = """UPDATE status_logs SET door_status = %s, led_status = %s, timestamp = %s, version = %s WHERE id = 1"""
    rds_cursor.execute(update_query, status[1:])

# Sync functions
def sync_door_settings(local_cursor, rds_cursor, rds_db_connection, local_db_connection):
    local_settings = fetch_local_door_settings(local_cursor)
    rds_settings = fetch_rds_door_settings(rds_cursor)

    if not local_settings or not rds_settings:
        print("Error: Missing door settings data in one of the databases.")
        return

    print("Syncing door settings...")
    update_local_door_settings(local_cursor, rds_settings)
    update_rds_door_settings(rds_cursor, local_settings)

    local_db_connection.commit()
    rds_db_connection.commit()
    print("Door settings synced.")

def sync_door_status(local_cursor, rds_cursor, rds_db_connection, local_db_connection):
    local_status = fetch_local_door_status(local_cursor)
    rds_status = fetch_rds_door_status(rds_cursor)

    if not local_status or not rds_status:
        print("Error: Missing door status data in one of the databases.")
        return

    local_version = local_status[-1]
    rds_version = rds_status[-1]

    print(f"Local door status version: {local_version}, RDS door status version: {rds_version}")

    if local_version < rds_version:
        print("Updating local door status from RDS door status.")
        update_local_door_status(local_cursor, rds_status)
        local_db_connection.commit()
    elif local_version > rds_version:
        print("Updating RDS door status from local door status.")
        update_rds_door_status(rds_cursor, local_status)
        rds_db_connection.commit()
    else:
        print("No updates needed. Both door statuses are up to date.")
        
# Main sync function
def sync_databases():
    local_db_connection = mysql.connector.connect(
        host="localhost",
        user="pi",
        password="pass1234",
        database="sensor_db"
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
            # Sync settings
            sync_door_settings(local_cursor, rds_cursor, rds_db_connection, local_db_connection)

            # Sync status based on the latest version
            sync_door_status(local_cursor, rds_cursor, rds_db_connection, local_db_connection)
            
        except Exception as e:
            print("Error during synchronization:", e)

        time.sleep(5)

if __name__ == "__main__":
    sync_thread = Thread(target=sync_databases)
    sync_thread.start()
