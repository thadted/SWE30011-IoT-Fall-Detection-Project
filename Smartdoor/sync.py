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

def fetch_all_rfid_access_rds(rds_cursor):
    rds_cursor.execute("SELECT * FROM rfid_access")
    return rds_cursor.fetchall()

def fetch_local_door_status(local_cursor):
    local_cursor.execute("SELECT * FROM status_logs WHERE id = 1")
    return local_cursor.fetchone()

def fetch_rds_door_status(rds_cursor):
    rds_cursor.execute("SELECT * FROM status_logs WHERE id = 1")
    return rds_cursor.fetchone()

# Insert functions
def insert_local_door_settings(local_cursor, settings):
    insert_query = """INSERT INTO access_logs (rfid, message, timestamp) VALUES (%s, %s, %s)"""
    for setting in settings:
        local_cursor.execute(insert_query, (setting[1], setting[2], setting[3]))

def insert_rds_door_settings(rds_cursor, settings):
    insert_query = """INSERT INTO access_logs (rfid, message, timestamp) VALUES (%s, %s, %s)"""
    for setting in settings:
        rds_cursor.execute(insert_query, (setting[1], setting[2], setting[3]))

def insert_local_rfid_access(local_cursor, access_data):
    for access in access_data:
        uid = access[1]
        # Check if the UID already exists in the database
        local_cursor.execute("SELECT * FROM rfid_access WHERE uid = %s", (uid,))
        existing_entry = local_cursor.fetchone()
        if not existing_entry:
            # If UID doesn't exist, insert it into the database
            insert_query = "INSERT INTO rfid_access (uid) VALUES (%s)"
            local_cursor.execute(insert_query, (uid,))

def update_local_door_status(local_cursor, status):
    update_query = """UPDATE status_logs SET door_status = %s, led_status = %s, timestamp = %s, version = %s WHERE id = 1"""
    local_cursor.execute(update_query, status[1:])

def update_rds_door_status(rds_cursor, status):
    update_query = """UPDATE status_logs SET door_status = %s, led_status = %s, timestamp = %s, version = %s WHERE id = 1"""
    rds_cursor.execute(update_query, status[1:])

def update_rds_rfid_access(local_cursor, access):
    local_cursor.execute(("INSERT INTO rfid_access (uid) VALUES (%s)", (access,)))
    
# Comparison function
def compare_and_sync_settings(local_settings, rds_settings, rds_cursor):
    if not rds_settings:
        # If RDS settings are empty, insert all local settings
        insert_rds_door_settings(rds_cursor, local_settings)
        print(f"Inserted {len(local_settings)} new settings into RDS.")
        return

    latest_rds_timestamp = max(setting[3] for setting in rds_settings)

    new_settings = [setting for setting in local_settings if setting[3] > latest_rds_timestamp]

    if new_settings:
        insert_rds_door_settings(rds_cursor, new_settings)
        print(f"Inserted {len(new_settings)} new settings into RDS.")

# Sync functions
def sync_door_settings(local_cursor, rds_cursor, rds_db_connection, local_db_connection):
    local_settings = fetch_local_door_settings(local_cursor)
    rds_settings = fetch_rds_door_settings(rds_cursor)

    if not local_settings:
        print("Error: Missing door settings data in local database.")
        return

    print("Local door settings fetched:", local_settings)
    print("RDS door settings fetched:", rds_settings)

    print("Syncing door settings...")
    compare_and_sync_settings(local_settings, rds_settings, rds_cursor)
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
        
def sync_rfid_access(local_cursor, rds_cursor, local_db_connection):
    rfid_access_data = fetch_all_rfid_access_rds(rds_cursor)

    if not rfid_access_data:
        print("No RFID access data found in RDS database.")
        return

    print("RFID access data fetched from RDS:", rfid_access_data)

    # Get UIDs present in the local database
    local_cursor.execute("SELECT uid FROM rfid_access")
    local_uids = [row[0] for row in local_cursor.fetchall()]

    # Get UIDs present in the RDS database
    rds_uids = [row[1] for row in rfid_access_data]

    # Delete UIDs from local database that are not present in RDS database
    uids_to_delete = set(local_uids) - set(rds_uids)
    for uid in uids_to_delete:
        local_cursor.execute("DELETE FROM rfid_access WHERE uid = %s", (uid,))

    # Insert or update RFID access data in local database
    for access in rfid_access_data:
        uid = access[1]
        # Check if the UID already exists in the local database
        local_cursor.execute("SELECT * FROM rfid_access WHERE uid = %s", (uid,))
        existing_entry = local_cursor.fetchone()
        if existing_entry:
            # If UID exists, update its UID value
            update_query = "UPDATE rfid_access SET uid = %s WHERE uid = %s"
            local_cursor.execute(update_query, (uid, uid))
        else:
            # If UID doesn't exist, insert it into the database
            insert_query = "INSERT INTO rfid_access (uid) VALUES (%s)"
            local_cursor.execute(insert_query, (uid,))

    local_db_connection.commit()
    print("RFID access data synced to local database.")
    
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
            
            def reconnect_local_db():
                return mysql.connector.connect(
                    host="localhost",
                    user="pi",
                    password="pass1234",
                    database="sensor_db"
        )

            def reconnect_rds_db():
                return mysql.connector.connect(
                    host="database-1.cjdvhndhcwh8.us-east-1.rds.amazonaws.com",
                    user="admin",
                    password="12345678",
                    database="fall_sensor"
        )

            # Usage in the main sync function
            local_db_connection = reconnect_local_db()
            local_cursor = local_db_connection.cursor()

            rds_db_connection = reconnect_rds_db()
            rds_cursor = rds_db_connection.cursor()

            # Sync settings
            sync_door_settings(local_cursor, rds_cursor, rds_db_connection, local_db_connection)

            # Sync status based on the latest version
            sync_door_status(local_cursor, rds_cursor, rds_db_connection, local_db_connection)
            
            sync_rfid_access(local_cursor, rds_cursor, local_db_connection)
               
        except Exception as e:
            print("Error during synchronization:", e)

        time.sleep(5)

if __name__ == "__main__":
    sync_thread = Thread(target=sync_databases)
    sync_thread.start()