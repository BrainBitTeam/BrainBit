#!/usr/bin/env python3
"""
PC Side - TCP Client
Listens for messages from ZCU102 and lets the user send replies anytime.
"""

import socket
import threading

ZCU_IP = "192.168.1.11"   # IP address of your ZCU102
PORT = 5000

def receive_messages(sock):
    """Thread that constantly listens for incoming messages."""
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("Disconnected from ZCU102.")
                break
            message = data.decode('utf-8')
            print(f"\n[ZCU102]: {message}")
            print("You: ", end="", flush=True)
        except ConnectionError:
            print("Connection closed.")
            break

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Connecting to ZCU102 at {ZCU_IP}:{PORT}...")
        s.connect((ZCU_IP, PORT))
        print("Connected! Type a message and press Enter to send.")

        threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

        while True:
            user_text = input("You: ")
            if user_text.strip().lower() == "exit":
                print("Closing connection.")
                break
            s.sendall(user_text.encode('utf-8'))

if __name__ == "__main__":
    main()