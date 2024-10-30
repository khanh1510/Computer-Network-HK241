import socket 
from threading import Thread 
import logging
import json
import sys
import psycopg2
import os
import bencodepy
import hashlib

list_peer_active = []
list_file_tracker_have = []
# Establish a connection to the PostgreSQL database
# conn = psycopg2.connect(dbname="", user="postgres", password="1903", host="", port="5432")
# cur = conn.cursor()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
def log_event(message):
    logging.info(message)

def update_client_info(peer_ID, peer_ip,peer_port,file_name,file_size,piece_hash,piece_size,num_order_in_file):
    # Update the client's file list in the database
    for i in range(len(num_order_in_file)):
        list_file_tracker_have.append({'peer_ID': peer_ID, 'peer_ip': peer_ip,
                                                'peer_port': peer_port, 'file_name': file_name, 'file_size': file_size,
                                                 'piece_hash': piece_hash[i], 'piece_size': piece_size, 'num_order_in_file': num_order_in_file[i]})


#code nay chi de test
def client_call(conn, addr):
    #list_peer_active.append(addr)
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                continue 

            command = json.loads(data)
            print("Test X: ", command, "\n")

            peer_ip = addr[0]
            peer_port = addr[1]
            peer_ID = command['peer_ID'] if 'peer_ID' in command else ""
            file_name = command['file_name'] if 'file_name' in command else ""
            file_size = command['file_size'] if 'file_size' in command else ""
            piece_hash = command['piece_hash'] if 'piece_hash' in command else ""
            piece_size = command['piece_size'] if 'piece_size' in command else ""
            num_order_in_file = command['num_order_in_file'] if 'num_order_in_file' in command else ""
            infor_hash = command['infor_hash'] if 'infor_hash' in command else ""

            if command.get('action') == 'introduce':
                #get all file list of peer
                list_peer_active.append({'peer_ID': peer_ID, 'peer_ip': peer_ip, 'peer_port': peer_port})
            elif command.get('action') == 'publish':
                #get add meta file to tracker
                update_client_info(peer_ID, peer_ip,peer_port,file_name,file_size,piece_hash,piece_size,num_order_in_file)
                conn.sendall("File list updated!".encode())
            elif command.get('action') == 'fetch':
                #get file from client
                peer_infor = []
                for item in list_file_tracker_have:
                    if item['file_name'] == file_name and item['piece_hash'] in piece_hash:
                        if item['file_size'] == 0:
                            item['file_size'] = file_size
                        peer_infor.append(item)
                if peer_infor:
                    print(conn)                      
                    conn.sendall(json.dumps({'peers_info': peer_infor}).encode())
                    print("send all")
                else:
                    conn.sendall(json.dumps({'error': 'File not available'}).encode())
            elif command.get('action') == 'magnet':
                #Đầu tiên lấy thông tin infor_hash của command đem so sanh với tất 
                #cả infor_hash của torren_tracker_local cái nào đúng thì lấy hash_string
                #của torrent đó gửi về lại peer
                if check(infor_hash):
                    pieces_lst, file_name = check(infor_hash)
                    conn.sendall(json.dumps({'file_name': file_name, 'hash_pice_lst': pieces_lst}).encode())
                else:
                    conn.sendall(json.dumps({'Error': 'No file in the server'}).encode())


            else:
                print("Not yet....")
    except Exception as e:
        logging.exception(f"An error occurred while handling client {addr}: {e}")

    finally:

        conn.close()
        log_event(f"Connection with {addr} has been closed.")

# #Hàm này để ping đến một địa chỉ IP + Port
# def ping_IP(ip, port, conn):
#     if ip:
#         # peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         # peer_sock.connect((ip, port))
#         request = {'action': 'ping'}
#         conn.sendall(json.dumps(request).encode() + b'\n')
#         response = conn.recv(4096).decode()
#         return response
#     else:
#         print("Invalid peer to ping!!!")

# #Tra ve kq cua peer nao dang active
# def get_peer_active(peers, conn):
#     print("Peers are connecting: \n")
#     for i in range(len(peers)): 
#         #print(peers[i][0], peers[i][1])
#         active = ping_IP(peers[i][0], peers[i][1], conn)
#         if active:
#             print(i, peers[i], "\n")

#In ra danh sach list peer dang hoat dong
def get_peer_active():
    print("This is the peer list \n")
    for peer in list_peer_active:
        print(peer, "\n")

#In ra danh sach file ma tracker nam giu
def get_peer_file():
    print("This is the file list \n")
    for file in list_file_tracker_have:
        print(file, "\n")

def request_file_list_from_client(ip, port):
    try: 
        if ip:
            peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_sock.connect((ip, port))
            request = {'action': 'request_file_list'}
            peer_sock.sendall(json.dumps(request).encode() + b'\n')
            response = json.loads(peer_sock.recv(4096).decode())
            peer_sock.close()
            if 'files' in response:
                return response['files']
            else:
                return "Error: No file list in response"
    except:
        print("Peer cann't connected :(")

def discover_files(ip, port):
    # Connect to the client and request the file list
    files = request_file_list_from_client(ip, port)
    print(f"Files on {ip} {port}: {files}")

def check_local_torrent():
    print("Check local pieces\n")
    exist_files = []
    directory = os.getcwd()  # Lấy đường dẫn thư mục hiện tại

    for filename in os.listdir(directory):
        if filename.endswith('.torrent'):
            exist_files.append(filename)

    if len(exist_files) > 0:
        return exist_files
    else:
        return False
    
#Cắt chuỗi dài thành các đoạn có độ dài là 40
def split_string(input_string, chunk_size=40):
    return [input_string[i:i + chunk_size] for i in range(0, len(input_string), chunk_size)]

def check(infor_hash):
    lst = check_local_torrent()
    for i in lst:
        with open(i, 'rb') as file:
            torrent_data = bencodepy.decode(file.read())
            info = torrent_data.get(b'info', {})
            if hashlib.sha1(bencodepy.encode(info)).hexdigest() == infor_hash:
                pieces = info.get(b'hash_string', b'').decode('utf-8') if b'hash_string' in info else None  # Danh sách các hash của từng phần
                pieces_lst = split_string(pieces)
                file_name = info.get(b'name', b'').decode('utf-8') if b'name' in info else None
                return pieces_lst, file_name
    return False
    






#------------------------------------------------------------------
#Code duoi day WARNING
#------------------------------------------------------------------

#command for server - tracker
def command_server():
    while True:
        try: 
            cmd = input("Admin: ")
            cmd = cmd.split()
            if cmd:
                action = cmd[0]
                if action.lower() == "peer":
                    get_peer_active()
                elif action.lower() == "file":
                    get_peer_file() #get list file that peer have with cmd[1] = peer_ID
                elif action.lower() == "meta":
                    local_torrent = check_local_torrent()
                    print(local_torrent)

            else:
                print("Request wrong, please type again!")
        except:
            print("Try again!")

#Code của thầy để lấy địa chỉ IP của máy :)))
def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


#Hàm chính để chạy server
def run_server(host, port):
    server_socket = socket.socket()
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"Server listening on {host}:{port}")
    
    try:
        while True:
            conn, address = server_socket.accept()  # accept new connection
            print(f"Connection from {address}")
            
            # Start a new thread for each client connection
            client_thread = Thread(target=client_call, args=(conn, address))
            client_thread.start()
    except KeyboardInterrupt:
        log_event("Server shutdown requested.")
    finally:
        server_socket.close()
        # cur.close()
        conn.close()

if __name__ == "__main__":
    hostip = get_host_default_interface_ip()
    port = 22236
    #run_server(hostip, port)

    # Start server in a separate thread
    server_thread = Thread(target=run_server, args=(hostip, port))
    server_thread.start()

    #Start the server command shell in the main thread
    command_server()

    print("End game.")
    sys.exit(0)