
import time
import mysql.connector
from threading import Thread

# Fetch functions for local database
def fetch_local_alert_data(local_cursor):
    local_cursor.execute("SELECT * FROM alert_data")
    return local_cursor.fetchall()

def fetch_local_location_data(local_cursor):
    local_cursor.execute("SELECT * FROM location_data")
    return local_cursor.fetchall()

def fetch_local_location_data_counts(local_cursor):
    local_cursor.execute("SELECT * FROM location_data_counts")
    return local_cursor.fetchall()

def fetch_local_temperature_data(local_cursor):
    local_cursor.execute("SELECT * FROM temperature_data")
    return local_cursor.fetchall()

def fetch_local_gas_data(local_cursor):
    local_cursor.execute("SELECT * FROM gas_data")
    return local_cursor.fetchall()

# Fetch functions for RDS database
def fetch_rds_alert_data(rds_cursor):
    rds_cursor.execute("SELECT * FROM alert_data")
    return rds_cursor.fetchall()

def fetch_rds_location_data(rds_cursor):
    rds_cursor.execute("SELECT * FROM location_data")
    return rds_cursor.fetchall()

def fetch_rds_location_data_counts(rds_cursor):
    rds_cursor.execute("SELECT * FROM location_data_counts")
    return rds_cursor.fetchall()

def fetch_rds_temperature_data(rds_cursor):
    rds_cursor.execute("SELECT * FROM temperature_data")
    return rds_cursor.fetchall()

def fetch_rds_gas_data(rds_cursor):
    rds_cursor.execute("SELECT * FROM gas_data")
    return rds_cursor.fetchall()

    # Update functions for RDS database
def update_rds_alert_data(rds_cursor, settings):
    update_query = """INSERT INTO alert_data (alert_type, timestamp) VALUES (%s, %s)"""
    for setting in settings:
        rds_cursor.execute(update_query, (setting[1], setting[2]))
    print(f"Inserted {len(settings)} new records into alert_data.")

def update_rds_location_data(rds_cursor, settings):
    update_query = """INSERT INTO location_data (location_type, timestamp) VALUES (%s,%s)"""
    for setting in settings:
        rds_cursor.execute(update_query, (setting[1], setting[2]))
    print(f"Inserted {len(settings)} new records into location_data.")

def update_rds_location_data_counts(rds_cursor, settings):
    update_query = """INSERT INTO location_data_counts (location_type, data_count) VALUES (%s, %s) ON DUPLICATE KEY UPDATE data_count = VALUES(data_count)"""
    for setting in settings:
        rds_cursor.execute(update_query, (setting[1], setting[2]))
    print(f"Inserted {len(settings)} new records into location_data_counts.")

def update_rds_temperature_data(rds_cursor, settings):
    update_query = """INSERT INTO temperature_data (temperature, timestamp) VALUES (%s, %s)"""
    for setting in settings:
        rds_cursor.execute(update_query, (setting[1], setting[2]))
    print(f"Inserted {len(settings)} new records into temperature_data.")

def update_rds_gas_data(rds_cursor, settings):
    update_query = """INSERT INTO gas_data (gas_value, timestamp) VALUES (%s,%s)"""
    for setting in settings:
        rds_cursor.execute(update_query, (setting[1], setting[2]))
    print(f"Inserted {len(settings)} new records into gas_data.")
    
# Comparison and sync functions
def compare_and_sync_data(local_data, rds_data, update_rds_function, rds_cursor):
    if not rds_data:
        update_rds_function(rds_cursor, local_data)
        print(f"Inserted {len(local_data)} new records into RDS.")
        return

    # Example: assuming data has a timestamp at index 1, adjust as needed
    latest_rds_timestamp = max(record[-1] for record in rds_data)
    new_data = [record for record in local_data if record[-1] > latest_rds_timestamp]

    if new_data:
        update_rds_function(rds_cursor, new_data)
        print(f"Inserted {len(new_data)} new records into RDS.")

# Sync functions
def sync_alert_data(local_cursor, rds_cursor):
    local_data = fetch_local_alert_data(local_cursor)
    rds_data = fetch_rds_alert_data(rds_cursor)
    compare_and_sync_data(local_data, rds_data, update_rds_alert_data, rds_cursor)

def sync_location_data(local_cursor, rds_cursor):
    local_data = fetch_local_location_data(local_cursor)
    rds_data = fetch_rds_location_data(rds_cursor)
    compare_and_sync_data(local_data, rds_data, update_rds_location_data, rds_cursor)

def sync_location_data_counts(local_cursor, rds_cursor):
    local_data = fetch_local_location_data_counts(local_cursor)
    rds_data = fetch_rds_location_data_counts(rds_cursor)
    compare_and_sync_data(local_data, rds_data, update_rds_location_data_counts, rds_cursor)

def sync_temperature_data(local_cursor, rds_cursor):
    local_data = fetch_local_temperature_data(local_cursor)
    rds_data = fetch_rds_temperature_data(rds_cursor)
    compare_and_sync_data(local_data, rds_data, update_rds_temperature_data, rds_cursor)

def sync_gas_data(local_cursor, rds_cursor):
    local_data = fetch_local_gas_data(local_cursor)
    rds_data = fetch_rds_gas_data(rds_cursor)
    compare_and_sync_data(local_data, rds_data, update_rds_gas_data, rds_cursor)
    
   # Fetch functions for local light status
def fetch_local_light_status_livingRoom(local_cursor):
    local_cursor.execute('SELECT * FROM light_status WHERE Room = "Living Room"')
    return local_cursor.fetchone()

def fetch_local_light_status_bedRoom(local_cursor):
    local_cursor.execute('SELECT * FROM light_status WHERE Room = "Bedroom"')
    return local_cursor.fetchone()

# Fetch functions for light status from RDS
def fetch_rds_light_status_livingRoom(rds_cursor):
    rds_cursor.execute('SELECT * FROM light_status WHERE Room = "Living Room"')
    return rds_cursor.fetchone()

def fetch_rds_light_status_bedRoom(rds_cursor):
    rds_cursor.execute('SELECT * FROM light_status WHERE Room = "Bedroom"')
    return rds_cursor.fetchone()

# Sync functions for light status from RDS to local
def sync_light_status_from_rds(local_cursor, rds_cursor):
    living_room_rds = fetch_rds_light_status_livingRoom(rds_cursor)
    if living_room_rds:
        update_local_light_status(local_cursor, living_room_rds)

    bedroom_rds = fetch_rds_light_status_bedRoom(rds_cursor)
    if bedroom_rds:
        update_local_light_status(local_cursor, bedroom_rds)

def update_local_light_status(local_cursor, settings):
    update_query = """INSERT INTO light_status (Room, Status, LastUpdated) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE Status = VALUES(Status), LastUpdated = VALUES(LastUpdated)"""
    local_cursor.execute(update_query, settings)
    print(f"Inserted/Updated light status record in local database.")


# Main sync function
def sync_databases():
    def reconnect_local_db():
        return mysql.connector.connect(
            host="localhost",
            user="pi",
            password="abcd1234",
            database="sensor_db"
        )

    def reconnect_rds_db():
        return mysql.connector.connect(
            host="database-1.cjdvhndhcwh8.us-east-1.rds.amazonaws.com",
            user="admin",
            password="12345678",
            database="fall_sensor"
        )

    while True:
        try:
            local_db_connection = reconnect_local_db()
            local_cursor = local_db_connection.cursor()

            rds_db_connection = reconnect_rds_db()
            rds_cursor = rds_db_connection.cursor()

            # Sync all data
            sync_alert_data(local_cursor, rds_cursor)
            sync_temperature_data(local_cursor, rds_cursor)
            sync_gas_data(local_cursor, rds_cursor)
            sync_light_status_from_rds(local_cursor, rds_cursor)
            sync_location_data(local_cursor, rds_cursor)
            sync_location_data_counts(local_cursor, rds_cursor)

# Commit changes
            local_db_connection.commit()
            rds_db_connection.commit()

            local_cursor.close()
            local_db_connection.close()
            rds_cursor.close()
            rds_db_connection.close()
        except Exception as e:
            print("Error during synchronization:", e)

        time.sleep(5)

if __name__ == "__main__":
    sync_thread = Thread(target=sync_databases)
    sync_thread.start()

