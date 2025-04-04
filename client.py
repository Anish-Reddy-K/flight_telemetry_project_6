import socket
import time
import uuid
import json
import random
import os

# Configuration
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000
DATA_FILES_DIR = "Data Files"

def get_telemetry_files():
    """Return list of telemetry file paths from the designated directory."""
    files = []
    if os.path.exists(DATA_FILES_DIR):
        for file in os.listdir(DATA_FILES_DIR):
            if file.endswith('.txt'):
                files.append(os.path.join(DATA_FILES_DIR, file))
    return files

def simulate_flight():
    # Generate a global unique flight ID
    uid = str(uuid.uuid4())

    # Create a socket connection to the server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, SERVER_PORT))
    
    # Initial Handshake: send "start" message
    start_time = time.strftime("%H:%M:%S")
    start_message = {"type": "start", "uid": uid, "timestamp": start_time}
    s.sendall((json.dumps(start_message) + "\n").encode())
    print(f"Sent start message: {start_message}")
    
    # Select a random telemetry file from the data directory
    telemetry_files = get_telemetry_files()
    if not telemetry_files:
        print("No telemetry files found in 'Data Files' directory!")
        s.close()
        return
    telemetry_file = random.choice(telemetry_files)
    print(f"Using telemetry file: {telemetry_file}")

    # Process telemetry file line-by-line
    with open(telemetry_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Assume each line is "timestamp fuel" (space separated)
            parts = line.split()
            if len(parts) < 2:
                continue
            telemetry_timestamp, fuel_str = parts[0], parts[1]
            try:
                fuel_value = float(fuel_str)
            except ValueError:
                continue
            
            # Send telemetry "data" message
            data_message = {
                "type": "data",
                "uid": uid,
                "timestamp": telemetry_timestamp,
                "fuel": fuel_value
            }
            s.sendall((json.dumps(data_message) + "\n").encode())
            print(f"Sent data message: {data_message}")
            time.sleep(1)  # Simulate 1-second intervals

    # Final Handshake: send "end" message
    end_time = time.strftime("%H:%M:%S")
    end_message = {"type": "end", "uid": uid, "timestamp": end_time}
    s.sendall((json.dumps(end_message) + "\n").encode())
    print(f"Sent end message: {end_message}")
    
    s.close()

if __name__ == '__main__':
    simulate_flight()