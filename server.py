import socket

HOST = ''          # Listen on all interfaces
PORT = 8888        # Arbitrary choice, just ensure it's not blocked

def main():
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on port {PORT}...")
        
        while True:
            client_socket, client_addr = s.accept()
            print(f"New connection from {client_addr}")
            
            with client_socket:
                # Keep receiving data until client disconnects
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        # No more data -> client closed connection
                        break
                    # Just print the incoming data
                    print(f"Received: {data.decode('utf-8')}", end="\n\n")

if __name__ == "__main__":
    main()