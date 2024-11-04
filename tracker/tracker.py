import socket 
from threading import Thread 
import logging
import json
import sys
import psycopg2
import os
import bencodepy
import hashlib
from collections import Counter

# list_peer_active = []
# list_file_tracker_have = []
# Establish a connection to the PostgreSQL database
def connect_db():
    return psycopg2.connect(dbname="postgres", user="postgres", password="1903", host="localhost", port="5432")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
def log_event(message):
    logging.info(message)

def update_client_info(peer_ID, peer_ip,peer_port,file_name,file_size,piece_hash,piece_size,num_order_in_file):
    # Update the client's file list in the database
    conn = connect_db()
    cursor = conn.cursor()
    for i in range(len(num_order_in_file)):
        # Kiểm tra trước khi chèn
        cursor.execute('SELECT 1 FROM "piece" WHERE hash = %s', (piece_hash[i],))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO "piece" (peer_port, hash, file_name, file_size, piece_size, num_order_in_file) VALUES (%s, %s, %s, %s, %s, %s)',
                (peer_port, piece_hash[i], file_name, file_size, piece_size, num_order_in_file[i])
            )
            conn.commit()
        # list_file_tracker_have.append({'peer_ID': peer_ID, 'peer_ip': peer_ip,
        #                                         'peer_port': peer_port, 'file_name': file_name, 'file_size': file_size,
        #                                          'piece_hash': piece_hash[i], 'piece_size': piece_size, 'num_order_in_file': num_order_in_file[i]})
    cursor.close()
    conn.close()
    


# Đăng ký người dùng mới
def signup(sock, username, hash_password, id_x, ip, port):
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO "user" (id, username, password) VALUES (%s, %s, %s)',
            (id_x, username, hash_password)
        )
        conn.commit()
        sock.sendall("success".encode())
        cursor.execute(
            'INSERT INTO "address" (port, ip, id_peer, active) VALUES (%s, %s, %s, %s)',
            (port, ip, id_x, False)
        )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        sock.sendall("fail".encode())
    finally:
        cursor.close()
        conn.close()

# Đăng nhập người dùng
def login(sock, username, hash_password, ip, port):
    conn = connect_db()
    cursor = conn.cursor()

    # Kiểm tra thông tin đăng nhập
    cursor.execute(
        'SELECT * FROM "user" WHERE username = %s AND password = %s',
        (username, hash_password)
    )
    user = cursor.fetchone()

    if user:
        # Lấy giá trị của id với username được người dùng nhập vào
        cursor.execute('SELECT id FROM "user" WHERE username = %s', (username,))
        id_peer = cursor.fetchone()

        # Kiểm tra nếu id_peer có tồn tại
        if id_peer:
            id_peer = id_peer[0]  # Lấy giá trị id từ tuple

            # Cập nhật lại giá trị ip và port khi người dùng đăng nhập
            cursor.execute(
                'UPDATE address SET ip = %s, port = %s, active = %s WHERE id_peer = %s',
                (ip, port, True, id_peer)
            )
            conn.commit()  # Lưu thay đổi vào database

            sock.sendall(json.dumps({'success': id_peer}).encode())

        else:
            sock.sendall("fail".encode())
    else:
        sock.sendall("fail".encode())

    cursor.close()
    conn.close()

#Cần viết hàm exit for peer
def exit_peer(id_peer):
    conn = connect_db()
    cursor = conn.cursor()
    # Cập nhật lại giá trị active khi user logout
    cursor.execute(
        'UPDATE address SET active = %s WHERE id_peer = %s',
        (False, id_peer)
    )
    conn.commit()  # Lưu thay đổi vào database
    cursor.close()
    conn.close()


#Cần viết hàm đầu vào là file_name, danh sách hash_piece cần để tải xuống đầu ra là danh sách thông tin về hash_pieces đó sao cho peer đó active
def get_infor_pices(file_name, hash_pieces, boolea):

    conn = connect_db()
    cursor = conn.cursor()
    # Cập nhật lại giá trị active khi user logout
    # Câu truy vấn SQL
    query = """
            SELECT 
                address.id_peer, address.port, address.ip, 
                piece.file_name, piece.file_size, 
                piece.hash, piece.piece_size, 
                piece.num_order_in_file
            FROM 
                address
            JOIN 
                piece ON address.port = piece.peer_port
            WHERE 
                piece.file_name = %s
                AND address.active = %s
                AND piece.hash = ANY(%s);
            """
    # Thực thi câu truy vấn
    cursor.execute(query, (file_name, boolea, hash_pieces))
    result = cursor.fetchall()

    # Đưa các kết quả vào danh sách
    # args=(sock, peer_info['peer_ip'],
    #                             peer_info['peer_port'],
    #                             peer_info['file_name'],
    #                             peer_info['piece_hash'],
    #                             peer_info['num_order_in_file'],
    #                             peer_info['file_size'],
    #                             peer_info['piece_size']))
    address_list = []
    for address in result:
        address_list.append({
            'peer_ID': address[0],
            'peer_port': address[1],
            'peer_ip': address[2],
            'file_name': address[3],
            'file_size': address[4],
            'piece_hash': address[5],
            'piece_size': address[6],
            'num_order_in_file': address[7]
        })

    cursor.close()
    conn.close()

    return address_list 




#code nay chi de test
def client_call(conn, addr):
    #list_peer_active.append(addr)
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                continue 

            command = json.loads(data)
            #print("Test X: ", command, "\n")

            peer_ip = addr[0]
            peer_port = addr[1]
            peer_ID = command['peer_ID'] if 'peer_ID' in command else ""
            user_name = command['user_name'] if 'user_name' in command else ""
            hash_password = command['hash_password'] if 'hash_password' in command else ""
            file_name = command['file_name'] if 'file_name' in command else ""
            file_size = command['file_size'] if 'file_size' in command else ""
            piece_hash = command['piece_hash'] if 'piece_hash' in command else ""
            piece_size = command['piece_size'] if 'piece_size' in command else ""
            num_order_in_file = command['num_order_in_file'] if 'num_order_in_file' in command else ""
            infor_hash = command['infor_hash'] if 'infor_hash' in command else ""
            
            if command.get('action') == 'login':
                login(conn, user_name, hash_password, peer_ip, peer_port)
            elif command.get('action') == 'signup':
                signup(conn, user_name, hash_password, peer_ID, peer_ip, peer_port)
            # elif command.get('action') == 'introduce':
            #     #get all file list of peer
            #     list_peer_active.append({'peer_ID': peer_ID, 'peer_ip': peer_ip, 'peer_port': peer_port})
                #cur.execute("INSERT INTO ")
            elif command.get('action') == 'publish':
                #get add meta file to tracker
                update_client_info(peer_ID, peer_ip,peer_port,file_name,file_size,piece_hash,piece_size,num_order_in_file)
                conn.sendall("File list updated!".encode())
            elif command.get('action') == 'fetch':
                # command = {
                #     "action": "fetch",
                #     "peer_port": peer_port,
                #     "peers_ID": id_peer_main,
                #     "file_name":file_name,
                #     "piece_hash":piece_hash_need,
                #     "num_order_in_file":num_order_in_file,
                #     "file_size": file_size
                # } 
                #get file from client
                peer_infor = get_infor_pices(file_name, piece_hash, True)
                
                # peer_infor = []
                for item in peer_infor:
                    if item['file_size'] == 0:
                        item['file_size'] = file_size

                # Đếm số lượng mỗi chuỗi hash xuất hiện trong list
                hash_count = Counter(i["piece_hash"] for i in peer_infor)

                # Sắp xếp list theo số lượng xuất hiện của hash (từ nhỏ đến lớn), sau đó theo hash
                sorted_peer_infor = sorted(peer_infor, key=lambda x: (hash_count[x["piece_hash"]], x["piece_hash"]))
                
                if peer_infor:
                    print(conn)                      
                    conn.sendall(json.dumps({'peers_info': sorted_peer_infor}).encode())
                    print("Sent all")
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
            elif command.get('action') == 'peer_exit':
                print("Exit peer", peer_ID)
                exit_peer(peer_ID)
            else:
                print("Not yet....")
    except Exception as e:
        logging.exception(f"An error occurred while handling client {addr}: {e}")

    finally:

        conn.close()
        log_event(f"Connection with {addr} has been closed.")

# #Hàm này để ping đến một địa chỉ IP + Port
def ping_IP(ip, port, timeout=1):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((ip, port))
            return True
        except (socket.timeout, socket.error):
            return False

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
    conn = connect_db()
    cursor = conn.cursor()
    # Truy vấn để lấy thông tin các địa chỉ có active = true
    cursor.execute('SELECT id_peer, ip, port, active FROM "address" WHERE active = true')

    # Lấy tất cả các hàng kết quả
    addresses = cursor.fetchall()

    # Đưa các kết quả vào danh sách
    address_list = []
    for address in addresses:
        address_list.append({
            'ID_peer': address[0],
            'IP': address[1],
            'PORT': address[2],
            'Active': address[3]
        })
    cursor.close()
    conn.close()

    return address_list

#In ra danh sach file ma tracker nam giu
def get_peer_file():
    # print("This is the file list \n")
    # for file in list_file_tracker_have:
    #     print(file, "\n")

    conn = connect_db()
    cursor = conn.cursor()
    # Truy vấn để lấy thông tin các địa chỉ có active = true
    cursor.execute('SELECT id_peer, ip, port, active FROM "address" WHERE active = true')

    # Lấy tất cả các hàng kết quả
    addresses = cursor.fetchall()

    # Đưa các kết quả vào danh sách
    address_list = []
    for address in addresses:
        address_list.append({
            'ID_peer': address[0],
            'IP': address[1],
            'PORT': address[2],
            'Active': address[3]
        })
    cursor.close()
    conn.close()

    return address_list



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

#Hàm lấy danh sách các pieces hash từ magnet link
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
    

#Hàm Rarest pieces first
# def rarest_first(hash_lst):





#------------------------------------------------------------------
#Code duoi day WARNING
#------------------------------------------------------------------

#command for server - tracker
def command_server():
    while True:
        try: 
            cmd = input("Admin: ")
            cmd = cmd.split()
            print(cmd)
            if cmd:
                action = cmd[0]
                if action.lower() == "peer":
                    temp = get_peer_active()
                    for i in temp:
                        print(i, "\n")
                elif action.lower() == "file":
                    #get_peer_file() #get list file that peer have with cmd[1] = peer_ID
                    print(get_peer_file())
                elif action.lower() == "meta":
                    local_torrent = check_local_torrent()
                    print(local_torrent)
                elif action.lower() == "exit":
                    break

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
    port = 22222
    #run_server(hostip, port)

    # Start server in a separate thread
    server_thread = Thread(target=run_server, args=(hostip, port))
    server_thread.start()

    #Start the server command shell in the main thread
    command_server()

    print("End game.")
    sys.exit(0)