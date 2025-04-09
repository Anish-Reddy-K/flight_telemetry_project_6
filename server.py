import socket
import threading
import json
import sqlite3
import time
import os
from datetime import datetime
import psutil

# Server configuration
SERVER_IP = '0.0.0.0'
SERVER_PORT = 8000
DB_FILE = 'flights.db'

# Dictionary to hold live flight data: {uid: {...}}
flights = {}
flights_lock = threading.Lock()

# Initialize SQLite database
def init_db():
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
    print(f"New connection from {addr}")
    buffer = ""
    uid = None
    start_time = None

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode()
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
    except ConnectionResetError:
        print(f"ConnectionResetError from {addr}")
    finally:
        if uid is not None:
            with flights_lock:
                record = flights.pop(uid, None)
            if record:
                final_avg = record["fuel_sum"] / record["count"] if record["count"] > 0 else 0.0
                end_time = time.strftime("%H:%M:%S")
                print(f"Connection for flight {uid} closed unexpectedly at {end_time}. Final average fuel: {final_avg:.2f}")
                save_flight_record(uid, record["start_time"], end_time, final_avg, record["count"])
        conn.close()
        print(f"Connection from {addr} closed")

# 🔍 Performance monitoring with psutil
def monitor_performance(interval=1):
    process = psutil.Process(os.getpid())
    while True:
        cpu = process.cpu_percent()
        mem = process.memory_info().rss / 1024 ** 2
        print(f"[PERF] CPU: {cpu:.2f}% | RAM: {mem:.2f} MB")
        time.sleep(interval)

def start_server():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(5)
    print(f"Server listening on {SERVER_IP}:{SERVER_PORT}")

    # Start performance monitor in a background thread
    threading.Thread(target=monitor_performance, daemon=True).start()

    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(target=process_client, args=(conn, addr))
        client_thread.daemon = True
        client_thread.start()

if __name__ == '__main__':
    start_server()