import socket
import threading
import json
import sqlite3

# Server configuration
SERVER_IP = '0.0.0.0'
SERVER_PORT = 5000
DB_FILE = 'flights.db'

# Dictionary to hold live flight data: {uid: {"start_time": ..., "fuel_sum": ..., "count": ...}}
flights = {}
flights_lock = threading.Lock()

def init_db():
    """Initialize the SQLite database and create the flights table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            uid TEXT PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            final_avg_fuel REAL,
            record_count INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_flight_record(uid, start_time, end_time, final_avg, count):
    """Save the completed flight record into the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO flights (uid, start_time, end_time, final_avg_fuel, record_count)
        VALUES (?, ?, ?, ?, ?)
    ''', (uid, start_time, end_time, final_avg, count))
    conn.commit()
    conn.close()
    print(f"Saved flight record for UID {uid}")

def process_client(conn, addr):
    """Handle client connection and process messages."""
    print(f"New connection from {addr}")
    buffer = ""
    uid = None
    start_time = None

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode()
            # Process complete lines separated by newline
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = message.get("type")
                if msg_type == "start":
                    uid = message.get("uid")
                    start_time = message.get("timestamp")
                    with flights_lock:
                        flights[uid] = {"start_time": start_time, "fuel_sum": 0.0, "count": 0}
                    print(f"Started flight {uid} at {start_time}")
                elif msg_type == "data":
                    if uid is None:
                        continue
                    fuel = message.get("fuel")
                    with flights_lock:
                        if uid in flights:
                            flights[uid]["fuel_sum"] += fuel
                            flights[uid]["count"] += 1
                            running_avg = flights[uid]["fuel_sum"] / flights[uid]["count"]
                            print(f"Flight {uid}: Received fuel {fuel}. Running average: {running_avg:.2f}")
                elif msg_type == "end":
                    if uid is None:
                        continue
                    end_time = message.get("timestamp")
                    with flights_lock:
                        record = flights.pop(uid, None)
                    if record and record["count"] > 0:
                        final_avg = record["fuel_sum"] / record["count"]
                    else:
                        final_avg = 0.0
                    print(f"Flight {uid} ended at {end_time}. Final average fuel: {final_avg:.2f}")
                    save_flight_record(uid, start_time, end_time, final_avg, record["count"] if record else 0)
                else:
                    print("Received unknown message type.")
        except ConnectionResetError:
            break

    conn.close()
    print(f"Connection from {addr} closed")

def start_server():
    """Initialize database and start the server to accept incoming client connections."""
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(5)
    print(f"Server listening on {SERVER_IP}:{SERVER_PORT}")
    
    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(target=process_client, args=(conn, addr))
        client_thread.daemon = True
        client_thread.start()

if __name__ == '__main__':
    start_server()