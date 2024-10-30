import socket
import json
import os
import threading
import shlex
import hashlib
import math
import argparse
import bencodepy
from urllib.parse import urlparse, parse_qs

stop_event = threading.Event()

# # Function to parse a magnet URI
def parse_magnet_uri(magnet_link):
    # Parse the magnet link
    parsed = urlparse(magnet_link)
    params = parse_qs(parsed.query)
    
    # Extract info hash
    info_hash = params.get('xt')[0].split(":")[-1]
    
    # Extract display name (optional)
    display_name = params.get('dn', ['Unknown'])[0]
    
    # Extract tracker URL (optional)
    tracker_url = params.get('tr', [''])[0]
    
    return info_hash, display_name, tracker_url

# # Function to create a .torrent file (Metainfo)
def create_torrent_file(tracker, filename, size, chunk_hash, chunk_size, output_file):
    # Sample torrent metadata (in Bencode format)
    hash_string = ""
    for i in chunk_hash:
        hash_string += i 
    torrent_data = {
        "announce": tracker.encode(),  # Tracker URL
        "info": {
            "piece length": chunk_size,  # Example piece length (512KB)
            "length": size,  # Example file size (1MB)
            "hash_string": hash_string,  # Placeholder piece hashes (20-byte SHA-1 hashes)
            "name": filename.encode(),  # File name
        }
    }
    
    # Bencode the data
    encoded_data = bencodepy.encode(torrent_data)
    
    # Write the encoded data to a .torrent file
    with open(output_file, "wb") as f:
        f.write(encoded_data)
    
    print(f"Torrent file '{output_file}' created successfully!")


#Cắt chuỗi dài thành các đoạn có độ dài là 40
def split_string(input_string, chunk_size=40):
    return [input_string[i:i + chunk_size] for i in range(0, len(input_string), chunk_size)]

#Read Torrent file
def torrent_to_pieces_need(torrent_path):
    with open(torrent_path, 'rb') as file:
        torrent_data = bencodepy.decode(file.read())

    announce_url = torrent_data.get(b'announce', b'').decode('utf-8') if b'announce' in torrent_data else None
    # Lấy thông tin từ khóa 'info' trong file .torrent
    info = torrent_data.get(b'info', {})
    file_name = info.get(b'name', b'').decode('utf-8') if b'name' in info else None
    file_size = info.get(b'length', None)  # Kích thước file
    piece_length = info.get(b'piece length', None)  # Độ dài mỗi phần
    pieces = info.get(b'hash_string', b'').decode('utf-8') if b'hash_string' in info else None  # Danh sách các hash của từng phần
    pieces_lst = split_string(pieces)

    print("Test 1: ", pieces, "\n")
    print("Test 2: ", pieces_lst, "\n")

    return (file_name, pieces_lst)
    #trong đó lưu ý pieces chính là 1 list 
    


def calculate_piece_hash(piece_data):
    sha1 = hashlib.sha1()
    sha1.update(piece_data)
    return sha1.hexdigest()

def create_pieces_string(pieces):
    hash_pieces = []
    for piece_file_path in pieces:
            with open(piece_file_path, "rb") as piece_file:
                piece_data = piece_file.read()
                piece_hash = calculate_piece_hash(piece_data)
                hash_pieces.append(f"{piece_hash}")
    return hash_pieces

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
        if filename.startswith(file_name) and len(filename)>len(file_name) and not filename.endswith('.torrent'):
            exist_files.append(filename)

    if len(exist_files) > 0:
        return exist_files
    else:
        return False

def handle_publish_piece(sock, peers_port, pieces, file_name,file_size,piece_size):
    pieces_hash = create_pieces_string(pieces)
    user_input_num_piece = input( f"File {file_name} have {pieces}\n piece: {pieces_hash}. \nPlease select num piece in file to publish:" )
    num_order_in_file = shlex.split(user_input_num_piece) 
    piece_hash=[]
    print("You was selected: " )
    for i in num_order_in_file:
        index = pieces.index(f"{file_name}_piece{i}")
        piece_hash.append(pieces_hash[index])
        print (f"Number {i} : {pieces_hash[index]}")
    publish_piece_file(sock,peers_port,file_name,file_size, piece_hash,piece_size,num_order_in_file)

def publish_piece_file(sock,peers_port,file_name,file_size, piece_hash,piece_size,num_order_in_file):
    #peers_hostname = socket.gethostname()
    command = {
        "action": "publish",
        "peers_port": peers_port,
        "peer_ID": 19,
        "file_name":file_name,
        "file_size":file_size,
        "piece_hash":piece_hash,
        "piece_size":piece_size,
        "num_order_in_file":num_order_in_file,
    }
    # shared_piece_files_dir.append(command)
    sock.sendall(json.dumps(command).encode() + b'\n')
    response = sock.recv(4096).decode()
    print(response)

def request_file_from_peer(peers_ip, peer_port, file_name, piece_hash, num_order_in_file):
    peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        peer_sock.connect((peers_ip, int(peer_port)))
        peer_sock.sendall(json.dumps({'action': 'send_file', 'file_name': file_name, 'piece_hash':piece_hash, 'num_order_in_file':num_order_in_file}).encode() + b'\n')

        # Peer will send the file in chunks of 4096 bytes
        with open(f"{file_name}_piece{num_order_in_file}", 'wb') as f:
            while True:
                data = peer_sock.recv(4096)
                if not data:
                    break
                f.write(data)

        peer_sock.close()
        print(f"Piece of file: {file_name}_piece{num_order_in_file} has been fetched from peer.")
    except Exception as e:
        print(f"An error occurred while connecting to peer at {peers_ip}:{peer_port} - {e}")
    finally:
        peer_sock.close()

def fetch_file(sock,peer_port,file_name, piece_hash_need, num_order_in_file):
    #peers_hostname = socket.gethostname()
    command = {
        "action": "fetch",
        "peer_port": peer_port,
        "peers_ID": 19,
        "file_name":file_name,
        "piece_hash":piece_hash_need,
        "num_order_in_file":num_order_in_file,
    } 
    # command = {"action": "fetch", "fname": fname}
    sock.sendall(json.dumps(command).encode() + b'\n')
    response = json.loads(sock.recv(4096).decode())

    if 'peers_info' in response:

        peers_info = response['peers_info']
        print(response) #response chính là một list các dictionary thông tin peer nào có hash nào


        # In thông tin về các máy ngang hàng có chứa tệp
        host_info_str = "\n".join([
            f"Piece {peer_info['num_order_in_file']}: "
            f"Peer ID {peer_info['peer_ID']} at {peer_info['peer_ip']}:{peer_info['peer_port']} - "
            f"Piece Hash: {peer_info['piece_hash']} | File Size: {peer_info['file_size']} | "
            f"Piece Size: {peer_info['piece_size']}"
            for peer_info in peers_info
        ])
        print(f"Hosts with the file {file_name}:\n{host_info_str}")

        threads = []

        # Kiểm tra nếu có ít nhất một host
        if peers_info:
            for peer_info in peers_info:
                thread = threading.Thread(target=request_file_from_peer, 
                                          args=(peer_info['peer_ip'],
                                                peer_info['peer_port'],
                                                peer_info['file_name'],
                                                peer_info['piece_hash'],
                                                peer_info['num_order_in_file']))
            threads.append(thread)
            thread.start()

            # Chờ tất cả các luồng hoàn thành
            for thread in threads:
                thread.join()

            #chosen_info = input("Enter the piece numbers of the hosts to download from (e.g., '1 2'): ")
            #chosen_pieces = shlex.split(chosen_info) 

            # Lấy các phần mà người dùng yêu cầu
            # for piece_number in chosen_pieces:
            #     # Tìm peer chứa phần tương ứng
            #     peer_index = next((index for index, peer_info in enumerate(peers_info)
            #                        if peer_info['num_order_in_file'] == piece_number), None)
                
            #     if peer_index is not None:
            #         peer_info = peers_info[peer_index]
            #         request_file_from_peer(
            #             peer_info['peer_ip'],
            #             peer_info['peer_port'],
            #             peer_info['file_name'],
            #             peer_info['piece_hash'],
            #             peer_info['num_order_in_file']
            #         )
            #     else:
            #         print(f"Invalid piece number entered: {piece_number}")
            
            # Kiểm tra xem tất cả các phần của tệp đã được tải xuống chưa
            all_pieces = check_local_piece_files(file_name)
            if all_pieces and len(all_pieces) == math.ceil(int(peers_info[0]['file_size']) / int(peers_info[0]['piece_size'])):
                merge_pieces_into_file(all_pieces, file_name)
            else:
                print("Not all pieces downloaded yet.")
        else:
            print("No hosts have the file.")
    else:
        print("No peers have the file or the response format is incorrect.")

def send_piece_to_client(conn, piece):
    with open(piece, 'rb') as f:
        while True:
            bytes_read = f.read(4096)
            if not bytes_read:
                break
            conn.sendall(bytes_read)

def handle_file_request(conn, shared_files_dir):
    try:
        data = conn.recv(4096).decode()
        command = json.loads(data)
        if command['action'] == 'send_file':
            file_name = command['file_name']
            num_order_in_file = command['num_order_in_file']
            file_path = os.path.join(shared_files_dir, f"{file_name}_piece{num_order_in_file}")
            send_piece_to_client(conn, file_path)
    finally:
        conn.close()

def start_host_service(port, shared_files_dir):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('0.0.0.0', port))
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.listen()

    while not stop_event.is_set():
        try:
            server_sock.settimeout(1) 
            conn, addr = server_sock.accept()
            thread = threading.Thread(target=handle_file_request, args=(conn, shared_files_dir))
            thread.start()
        except socket.timeout:
            continue
        except Exception as e:
            break

    server_sock.close()

def connect_to_server(server_host, server_port, peers_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((server_host, peers_port))
    sock.connect((server_host, server_port))

    sock.sendall(json.dumps({'action': 'introduce', 'peer_ID': '19', 'peers_port':peers_port }).encode() + b'\n')
    return sock

def main(server_host, server_port, peers_port):
    host_service_thread = threading.Thread(target=start_host_service, args=(peers_port, './'))
    host_service_thread.start()

    # Connect to the server
    sock = connect_to_server(server_host, server_port,peers_port)

    try:
        while True:
            user_input = input("Enter command (publish file_name --- fetch torrent_path/magnet_link --- exit): ")
            command_parts = shlex.split(user_input)
            if len(command_parts) == 2 and command_parts[0].lower() == 'publish':
                _,file_name = command_parts
                if check_local_files(file_name):
                    piece_size = 524288  # 524288 byte = 512KB
                    file_size = os.path.getsize(file_name)
                    pieces = split_file_into_pieces(file_name,piece_size)
                    handle_publish_piece(sock, peers_port, pieces, file_name,file_size,piece_size)
                elif (pieces := check_local_piece_files(file_name)):
                    handle_publish_piece(sock, peers_port, pieces, file_name,file_size,piece_size)
                else:
                    print(f"Local file {file_name}/piece does not exist.")
            elif len(command_parts) == 2 and command_parts[0].lower() == 'fetch' and 'torrent' in command_parts[1]:
                #fetch file with torrent file
                file_name, pieces_hash_need = torrent_to_pieces_need(command_parts[1])

                print("Test: ", file_name, " ", pieces_hash_need, "\n")

                pieces = check_local_piece_files(file_name)
                pieces_hash_had = [] if not pieces else create_pieces_string(pieces)
                num_order_in_file= [] if not pieces else [item.split("_")[-1][5:] for item in pieces]

                for i in pieces_hash_had:
                    if i in pieces_hash_need:
                        pieces_hash_need.remove(i)

                fetch_file(sock,peers_port,file_name, pieces_hash_need, num_order_in_file)
            elif len(command_parts) == 2 and command_parts[0].lower() == 'fetch' and 'magnet' in command_parts[1]:
                print("Hmmm")
            elif len(command_parts) == 2 and command_parts[0].lower() == 'make':
                _, file_name = command_parts
                split_file_into_pieces(file_name, 524288)
                hmm = create_pieces_string(check_local_piece_files(file_name))
                file_size = os.path.getsize(file_name)
                out_file = file_name + '.torrent'

                print("Test 3: ", hmm, "\n")
                
                create_torrent_file(server_host, file_name, file_size, hmm, 524288, out_file)

            elif user_input.lower() == 'exit':
                stop_event.set()  # Stop the host service thread
                sock.close()    
                break
            else:
                print("Invalid command.")

    finally:
            sock.close()
            host_service_thread.join()


if __name__ == "__main__":
    # Replace with your server's IP address and port number
    SERVER_HOST = '192.168.1.103'
    SERVER_PORT = 22236
    #CLIENT_PORT = 65434

    parser = argparse.ArgumentParser(
        prog='Client',
        description='Connect to pre-declared server',
        epilog='!!!Ensure the server is running and listening!!!'
    )
    #parser.add_argument('--server-ip', required=True, help='Server IP address')
    parser.add_argument('--client-port', type=int, required=True, help='Server port')
    
    args = parser.parse_args()
    # host = args.server_ip
    port = args.client_port

    main(SERVER_HOST, SERVER_PORT, port)
    