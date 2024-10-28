import socket
import json
import os
from threading import Thread, threading 
import shlex
import hashlib
import math

stop_event = threading.Event()

#Hàm trả về một chuỗi SHA1
def calculate_piece_hash(piece_data):
    sha1 = hashlib.sha1()
    sha1.update(piece_data)
    return sha1.digest()

#Hàm trả về 1 list các hash của các pieces
def create_pieces_string(pieces):
    hash_pieces = []
    for piece_file_path in pieces:
            with open(piece_file_path, "rb") as piece_file:
                piece_data = piece_file.read()
                piece_hash = calculate_piece_hash(piece_data)
                hash_pieces.append(f"{piece_hash}")
    return hash_pieces

#Hàm cắt file thành list các pieces
def split_file_into_pieces(file_path, piece_length):
    pieces = []
    with open(file_path, "rb") as file:
        counter = 1
        while True:
            piece_data = file.read(piece_length)
            if not piece_data:
                break
            piece_file_path = f"{file_path}_piece{counter}"
            # piece_file_path = os.path.join("", f"{file_path}_piece{counter}")
            with open(piece_file_path, "wb") as piece_file:
                piece_file.write(piece_data)
            pieces.append(piece_file_path)
            counter += 1
    return pieces

def merge_pieces_into_file(pieces, output_file_path):
    with open(output_file_path, "wb") as output_file:
        for piece_file_path in pieces:
            with open(piece_file_path, "rb") as piece_file:
                piece_data = piece_file.read()
                output_file.write(piece_data)
    print("Got all the parts and created the file",output_file_path)

def get_list_local_files(directory='.'):
    try:
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        return True
    except Exception as e:
        return f"Error: Unable to list files - {e}"
    
def check_local_files(file_name):
    if not os.path.exists(file_name):
        return False
    else:
        return True
    
def check_local_piece_files(file_name):
    exist_files = []
    directory = os.getcwd()  # Lấy đường dẫn thư mục hiện tại

    for filename in os.listdir(directory):
        if filename.startswith(file_name) and len(filename)>len(file_name):
            exist_files.append(filename)

    if len(exist_files) > 0:
        return exist_files
    else:
        return False

def handle_request(client_socket):
    while True:
        try:
            # Nhận yêu cầu từ tracker
            data = client_socket.recv(4096).decode().strip()
            if not data:
                break
            
            request = json.loads(data)
            
            if request.get('action') == 'ping':
                # Trả lời ping từ tracker
                response = {'status': 'alive'}
                client_socket.sendall(json.dumps(response).encode() + b'\n')
            else:
                print("Unknown action received:", request.get('action'))
        except Exception as e:
            print("Error in handle_request:", e)
            break

def new_connection(host, port):
    print('Client connecting to Tracker {}:{}'.format(host, port))

    client_socket = socket.socket()
    client_socket.connect((host, port))

    message = "introduce"
    client_socket.send(message.encode())
    data = client_socket.recv(1024).decode()  # receive response
    if data == "connect ok":
        print("Introduce with Tracker OK!")
    else:
        print("Connect Fail:((")

    # Start thread to handle requests from the tracker
    handler_thread = Thread(target=handle_request, args=(client_socket,))
    handler_thread.start()

    while True:
        command = input("Input command: ")
        if command == "get list peer":
            print("OK")
        elif command == "get list file of peeer":
            print("OK")
        elif command == "fetch":
            print("OK")
        elif command == "publish file":
            print("OK")
        elif command == "get peer infor":
            print("OK")
        else: 
            print("Type again!")


def run_peer(host, port):
    new_connection(host, port)


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(
    #     prog='Client',
    #     description='Connect to pre-declared server',
    #     epilog='!!!Ensure the server is running and listening!!!'
    # )
    # parser.add_argument('--server-ip', required=True, help='Server IP address')
    # parser.add_argument('--server-port', type=int, required=True, help='Server port')
    
    # args = parser.parse_args()
    # host = args.server_ip
    # port = args.server_port

    host = "192.168.1.103"
    port = 22236

    run_peer(host, port)