"""
Memory-optimized version of server.py using asyncio with performance logging
and connection monitoring for abrupt client disconnections.
Run with: python server_optimized_with_connection_monitoring.py
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
LOG_FILE = 'server_performance_optimized_crash_2.csv'

# Timeout configuration for inactive connections (seconds)
INACTIVITY_TIMEOUT = 3

# Dictionary to hold live flight data: {uid: {...}}
flights = {}

# Track active client connections with last activity timestamp
# {writer_obj: {'uid': uid, 'last_active': timestamp}}
active_clients = {}

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

def close_inactive_connection(writer, uid=None, connection_info=None):
    """Clean up resources for an inactive connection"""
    if not connection_info and writer in active_clients:
        connection_info = active_clients[writer]
        
    if connection_info:
        uid = connection_info.get('uid')
        
    if uid is not None and uid in flights:
        # Save flight data before cleaning up
        record = flights.pop(uid)
        if record and record["count"] > 0:
            final_avg = record["fuel_sum"] / record["count"]
            end_time = time.strftime("%H:%M:%S")
            save_flight_record(uid, record["start_time"], end_time, final_avg, record["count"])
    
    # Remove from active clients tracking
    if writer in active_clients:
        del active_clients[writer]
    
    # Close connection if not already closed
    if not writer.is_closing():
        writer.close()

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    active_clients[writer] = {'uid': None, 'last_active': time.time()}
    print(f"New connection from {addr} (Active clients: {len(active_clients)})")
    
    buffer = ""
    uid = None
    start_time = None

    try:
        while True:
            try:
                # Set a timeout for reading from the client
                data = await asyncio.wait_for(reader.read(1024), timeout=INACTIVITY_TIMEOUT)
                if not data:
                    # If no data is received, it means the connection is closed
                    break
                
                # Update last active timestamp when data is received
                active_clients[writer]['last_active'] = time.time()
                
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
                        active_clients[writer]['uid'] = uid
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
            except asyncio.TimeoutError:
                # No data received within timeout period, but continue the loop
                continue
            except (ConnectionResetError, asyncio.IncompleteReadError):
                # Connection was reset or broken
                break
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        # Clean up the connection and save any pending flight data
        close_inactive_connection(writer, uid)
        await writer.wait_closed()
        print(f"Connection from {addr} closed (Active clients: {len(active_clients)})")

# Connection monitoring task - checks for inactive connections
async def monitor_connections(check_interval=3):
    while True:
        current_time = time.time()
        
        # Make a copy of the keys to safely iterate while potentially modifying
        for writer in list(active_clients.keys()):
            client_info = active_clients[writer]
            inactive_time = current_time - client_info['last_active']
            
            # If the client hasn't sent any data for longer than the inactivity timeout
            if inactive_time > INACTIVITY_TIMEOUT:
                addr = writer.get_extra_info('peername', 'Unknown')
                uid = client_info.get('uid')
                print(f"Detected inactive client {addr} (UID: {uid}). Inactive for {inactive_time:.1f}s. Closing.")
                
                # Close the connection and clean up
                close_inactive_connection(writer, connection_info=client_info)
                
                # Wait for the connection to close
                if not writer.is_closing():
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except:
                        pass
        
        await asyncio.sleep(check_interval)

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
        client_count = len(active_clients)
        
        # Log to console (reduced info)
        print(f"[PERF] CPU: {cpu:.2f}% | RAM: {mem:.2f} MB | Clients: {client_count}")
        
        # Log to file (full info)
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp},{cpu:.2f},{mem:.2f},{num_threads},{client_count}\n")
        
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
    print(f"Monitoring for inactive connections (timeout: {INACTIVITY_TIMEOUT}s)")
    
    # Start performance monitoring
    asyncio.create_task(monitor_performance())
    
    # Start connection monitoring
    asyncio.create_task(monitor_connections())
    
    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("Server shutting down...")
            
            # Clean up all active connections when shutting down
            for writer in list(active_clients.keys()):
                try:
                    close_inactive_connection(writer)
                except:
                    pass

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutdown complete.")