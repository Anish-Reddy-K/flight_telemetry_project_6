"""
Memory-optimized version of server.py using asyncio with performance logging.
Run with: python server_optimized_with_logging.py
"""
import asyncio
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
LOG_FILE = 'server_performance_optimized_endurance.csv'

# Dictionary to hold live flight data: {uid: {...}}
flights = {}

# Track active client connections
active_clients = 0

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

# Initialize performance log file
def init_log_file():
    # Create header if file doesn't exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("timestamp,cpu_percent,mem_mb,num_threads,active_clients\n")

def save_flight_record(uid, start_time, end_time, final_avg, count):
    # Use a connection pool or connection per request to avoid SQLite contention
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO flights (uid, start_time, end_time, final_avg_fuel, record_count)
        VALUES (?, ?, ?, ?, ?)
    ''', (uid, start_time, end_time, final_avg, count))
    conn.commit()
    conn.close()

async def handle_client(reader, writer):
    global active_clients
    active_clients += 1
    
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr} (Active clients: {active_clients})")
    
    buffer = ""
    uid = None
    start_time = None

    try:
        while True:
            data = await reader.read(1024)
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
                    flights[uid] = {"start_time": start_time, "fuel_sum": 0.0, "count": 0}
                elif msg_type == "data":
                    if uid is None:
                        continue
                    fuel = message.get("fuel")
                    if uid in flights:
                        flights[uid]["fuel_sum"] += fuel
                        flights[uid]["count"] += 1
                elif msg_type == "end":
                    if uid is None:
                        continue
                    end_time = message.get("timestamp")
                    record = flights.pop(uid, None)
                    if record and record["count"] > 0:
                        final_avg = record["fuel_sum"] / record["count"]
                    else:
                        final_avg = 0.0
                    save_flight_record(uid, start_time, end_time, final_avg, record["count"] if record else 0)
    except (ConnectionResetError, asyncio.IncompleteReadError):
        pass
    finally:
        active_clients -= 1
        
        if uid is not None:
            record = flights.pop(uid, None)
            if record and record["count"] > 0:
                final_avg = record["fuel_sum"] / record["count"]
                end_time = time.strftime("%H:%M:%S")
                save_flight_record(uid, record["start_time"], end_time, final_avg, record["count"])
        
        writer.close()
        await writer.wait_closed()
        print(f"Connection from {addr} closed (Active clients: {active_clients})")

# Performance monitoring with psutil - logs to file
async def monitor_performance(interval=1):
    process = psutil.Process(os.getpid())
    
    while True:
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get performance metrics
        cpu = process.cpu_percent()
        mem = process.memory_info().rss / 1024 ** 2  # RAM usage in MB
        num_threads = process.num_threads()
        
        # Log to console (reduced info)
        #print(f"[PERF] CPU: {cpu:.2f}% | RAM: {mem:.2f} MB | Clients: {active_clients}")
        
        # Log to file (full info)
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp},{cpu:.2f},{mem:.2f},{num_threads},{active_clients}\n")
        
        await asyncio.sleep(interval)

async def main():
    init_db()
    init_log_file()
    
    # Start the server
    server = await asyncio.start_server(
        handle_client, SERVER_IP, SERVER_PORT
    )
    
    addr = server.sockets[0].getsockname()
    print(f"Server listening on {addr[0]}:{addr[1]}")
    print(f"Performance logs being written to {LOG_FILE}")
    
    # Start performance monitoring with 1-second interval
    asyncio.create_task(monitor_performance())
    
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("Server shutting down...")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutdown complete.")