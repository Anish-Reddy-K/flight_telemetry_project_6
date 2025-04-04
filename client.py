import socket
import time
import uuid
import json
import random
import os

# config
SERVER_IP = 'X'  # change this to server computer's IP
SERVER_PORT = 8000
DATA_FILES_DIR = "Data Files"

def get_telemetry_files():
    files = []
    if os.path.exists(DATA_FILES_DIR):
        for file in os.listdir(DATA_FILES_DIR):
            if file.endswith('.txt'):
                files.append(os.path.join(DATA_FILES_DIR, file))
    return files

def parse_line(line):
    # remove extra whitespace and trailing commas
    line = line.strip().rstrip(',')
    if not line:
        return None, None

    # split by comma
    fields = line.split(',')
    # for header line, expected format:
    # "FUEL TOTAL QUANTITY,3_3_2023 14:53:21,4564.466309"
    if fields[0].upper() == "FUEL TOTAL QUANTITY":
        if len(fields) < 3:
            return None, None
        timestamp = fields[1].strip()
        fuel_str = fields[2].strip()
    else:
        # for regular data lines, expected format:
        # "3_3_2023 14:53:22,4564.405273"
        if len(fields) < 2:
            return None, None
        timestamp = fields[0].strip()
        fuel_str = fields[1].strip()

    try:
        fuel_value = float(fuel_str)
    except ValueError:
        return None, None

    return timestamp, fuel_value

def simulate_flight():
    # generate a global unique flight ID using uuid4
    uid = str(uuid.uuid4())

    # create a TCP socket connection to the server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, SERVER_PORT))
    
    # initial handshake: send "start" message with uid and timestamp
    start_time = time.strftime("%H:%M:%S")
    start_message = {"type": "start", "uid": uid, "timestamp": start_time}
    s.sendall((json.dumps(start_message) + "\n").encode())
    print(f"Sent start message: {start_message}")
    
    # wait one second before sending the first telemetry data
    time.sleep(1)
    
    # select a random telemetry file from the data directory
    telemetry_files = get_telemetry_files()
    if not telemetry_files:
        print("No telemetry files found in 'Data Files' directory!")
        # send an end message if no file is available
        end_time = time.strftime("%H:%M:%S")
        end_message = {"type": "end", "uid": uid, "timestamp": end_time}
        s.sendall((json.dumps(end_message) + "\n").encode())
        s.close()
        return

    telemetry_file = random.choice(telemetry_files)
    print(f"Using telemetry file: {telemetry_file}")

    # read all lines from the telemetry file
    with open(telemetry_file, "r") as f:
        lines = f.readlines()
        if not lines:
            print("Telemetry file is empty!")
    
    # process each line, sending one per second
    for line in lines:
        print(f"Read line: '{line.strip()}'")
        timestamp, fuel_value = parse_line(line)
        if timestamp is None or fuel_value is None:
            print("Skipping line due to parse error.")
            continue

        # build and send telemetry "data" message / packet
        data_message = {
            "type": "data",
            "uid": uid,
            "timestamp": timestamp,
            "fuel": fuel_value
        }
        s.sendall((json.dumps(data_message) + "\n").encode())
        print(f"Sent data message: {data_message}")
        time.sleep(1)  # wait 1 second before sending next line

    # final handshake: send "end" message with uid and timestamp
    end_time = time.strftime("%H:%M:%S")
    end_message = {"type": "end", "uid": uid, "timestamp": end_time}
    s.sendall((json.dumps(end_message) + "\n").encode())
    print(f"Sent end message: {end_message}")
    
    s.close()

if __name__ == '__main__':
    simulate_flight()