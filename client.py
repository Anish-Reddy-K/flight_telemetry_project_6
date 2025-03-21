import socket
import time

SERVER_IP = "10.0.0.111" # Replace this with the Mac mini's / servers IP address
SERVER_PORT = 8888

def main():
    plane_id = "Plane_01"
    
    # Minimal simulated flight data
    flight_data = [
        {"time": "10:00", "fuel": 5000, "flag": "in_flight"},
        {"time": "10:05", "fuel": 4950, "flag": "in_flight"},
        {"time": "10:10", "fuel": 4900, "flag": "in_flight"},
        {"time": "10:15", "fuel": 4800, "flag": "end_flight"}
    ]
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Connect to the Mac mini server
        s.connect((SERVER_IP, SERVER_PORT))
        print(f"Connected to {SERVER_IP}:{SERVER_PORT}")
        
        for entry in flight_data:
            # Construct a simple string to send
            msg = f"id={plane_id},time={entry['time']},fuel={entry['fuel']},flag={entry['flag']}"
            s.sendall(msg.encode('utf-8'))
            
            # Optional small delay to mimic real-time sending
            time.sleep(1)
        
        # After sending all data, close the socket (automatically in with-statement)

if __name__ == "__main__":
    main()

# Ask Prof
# UID
# UUID (or) Random number, how important is repeated flight simulation