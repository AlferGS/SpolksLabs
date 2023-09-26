# var 7

import socket
import select
import threading
import sys
import os
import os.path
import time
from datetime import datetime
from commands import server_commands, help_commands

IP = '192.168.0.107'
PORT = 1357
SERVER_ADDRESS = (IP, PORT)
BUFFER_SIZE = 1024
OK_STATUS = 200
SERVER_ERROR = 500
TIMEOUT = 20


def isFileExist(file_name):
    return os.path.exists(file_name)

def SendStatus(client, request, status):
    message = str("" + request + " " + str(status))
    client.send(message.encode('utf-8'))

def SendStatusAndMessage(client, request, status, message):
    message = str("" + request + " " + str(status) + " " + message)
    client.send(message.encode('utf-8'))

def HandleClient(client): # Если клиент не закрыт и от него пришел не пустой запрос
    if(client["is_closed"] == False):
        request = client['socket'].recv(BUFFER_SIZE).decode('utf-8')
        request = request.strip()
        if request != '':
            print("Received a command: %s" %request)
            HandleClientRequest(client,request)

def Echo(client, body):
    time.sleep(0.001)
    SendData(client, body)

def SendTime(client):
    server_time = "Server time: " + str(datetime.now())[:19]
    SendData(client, server_time)

def ExitClient(client):
    global inputs

    inputs.remove(client['socket'])
    clients_pool.remove(client)
    client['is_closed'] = True
    client['socket'].close()
    print("CLIENT IS EXIT")

def HandleClientRequest(client, request):
    command = request.split()
    name_command = command[0]

    if(len(command) == 2):
        body = command[1]

    if(name_command == "get"):
        if(isFileExist(body)):
            print("1.1")
            SendStatus(client['socket'], name_command, OK_STATUS)
            print("1.2")
            Download(client, body)
            print("1.3")
        else:
            print("File: " + body + " is not exist.")
            SendStatusAndMessage(client['socket'], name_command, SERVER_ERROR, "No such file!")

    elif(name_command == "post"):
        SendStatus(client['socket'], name_command, OK_STATUS)
        Upload(client, body)

    elif(name_command == "echo"):
        SendStatus(client['socket'], name_command, OK_STATUS)
        Echo(client, body)

    elif(name_command == "time"):
        SendStatus(client['socket'], name_command, OK_STATUS)
        SendTime(client)

    elif(name_command == "exit"):
        SendStatus(client['socket'], name_command, OK_STATUS)
        ExitClient(client)

def SearchByIP(list, ip):
    found_client = [element for element in list if element['ip'] == ip]
    return found_client[0] if len(found_client) > 0 else False

def SearchBySocket(list, socket):
    found_client = [element for element in list if element['socket'] == socket]
    return found_client[0] if len(found_client) > 0 else False

def SaveToWaitingClients(ip, command, file_name, progress):
    waiting_clients.append(
        {
            'ip': ip,
            'command': command,
            'file_name': file_name,
            'progress': progress,
        })

def HandleDisconnect(client, command, file_name, progress):
    SaveToWaitingClients(client['ip'], command, file_name, progress)
    clients_pool.remove(client)
    inputs.remove(client['socket'])
    client['socket'].close()

    sys.stdout.flush()
    print("\nClient was disconnected")
    sys.stdout.flush()

def WaitOK(client):
    while client['socket'].recv(2).decode('utf-8') != "OK":
        print("wait for OK")

def SendOK(client):
    client['socket'].send("OK".encode('utf-8'))

def GetData(client):
    return client['socket'].recv(BUFFER_SIZE).decode('utf-8')

def SendData(client, data):
    client['socket'].send(str(data).encode('utf-8'))

def Download(client, file_name):
    file = open(file_name, "rb+") # Открываем файл в режиме (чтения/записи бинарного)
    print("1.2.1")
    file_size = int(os.path.getsize(file_name))
    print("1.2.2")
    SendData(client, file_size)
    print("1.2.3")
    WaitOK(client)
    print("1.2.4")

    waiting_client = SearchByIP(waiting_clients, client['ip'])
    print("1.2.5")
    if (len(waiting_clients) > 0 and waiting_client != False):
        waiting_clients.remove(waiting_client)
    print("1.2.6")

    data_size_recv = int(GetData(client))
    print("1.2.7")

    if (waiting_client):
        if (waiting_client['file_name'] == file_name and waiting_client['command'] == 'download'):
            data_size_recv = int(waiting_client['progress'])
            SendData(client, data_size_recv)
    else:
        SendData(client, data_size_recv)

    print("1.2.8")
    WaitOK(client)
    print("1.2.9")

    file.seek(data_size_recv, 0)
    print("1.2.10")

    print("Start downloading")
    while (data_size_recv < file_size):
        try:
            data_file = file.read(BUFFER_SIZE)
            client['socket'].sendall(data_file)
            data_size_recv += BUFFER_SIZE
            file.seek(data_size_recv)

        except socket.error as e:
            file.close()
            HandleDisconnect(client, "download", file_name, data_size_recv)
            client['is_closed'] = True
            return

        except KeyboardInterrupt:
            server_socket.close()
            client.socket.close()
            os._exit(1)

    file.close()

def Upload(client, file_name):
    file_size = int(GetData(client))
    SendOK(client)

    data_size_recv = GetData(client)
    if (data_size_recv):
        data_size_recv = int(data_size_recv)

    waiting_client = SearchByIP(waiting_clients, client['ip'])
    if (len(waiting_clients) > 0 and waiting_client != False):
        waiting_clients.remove(waiting_client)

    if (waiting_client):
        if (waiting_client['file_name'] == file_name and waiting_client['command'] == 'upload'):
            data_size_recv = int(waiting_client['progress'])
            SendData(client, data_size_recv)
    else:
        SendData(client, data_size_recv)

    SendOK(client)

    if (data_size_recv == 0):
        file = open(file_name, "wb")
    else:
        file = open(file_name, "rb+")

    file.seek(data_size_recv, 0)

    print("Start uploading")
    while (data_size_recv < file_size):
        try:
            data = client['socket'].recv(BUFFER_SIZE)
            file.write(data)
            data_size_recv += len(data)
            file.seek(data_size_recv, 0)

        except socket.error as e:
            file.close()
            HandleDisconnect(client, "upload", file_name, data_size_recv)
            client['is_closed'] = True
            return

    print("Upload finished")
    file.close()

def ServerCLI():
    while True:
        command = input()
        parsed_data = ParseServerCommand(command)
        if(parsed_data == False):
            pass
        elif(len(parsed_data) == 2):
            command, body = parsed_data
            HandleServerCommand(command, body)

def ParseServerCommand(command):
    command = command.split()
    if(len(command) == 0):    #if parsed string is NULL
        return False
    name_command = command[0]
    if(len(command) == 2):
        body = command[1]     #[0]-Command, [1]-Other(Body)
    else:
        body = ""             #command without body
    return [name_command, body]

def ShowClients():
    clients_pool_len = len(clients_pool)
    if(clients_pool_len == 0):
        print("\nNo clients available")

    for i in range (0, clients_pool_len):
        print("\nClient" + str(i+1) + " info: ")
        print("\nIP:" + clients_pool[i]['ip'])
        print("\nPORT:" + clients_pool[i]['port'])
        print("\nCLOSED:" + clients_pool[i]['is_closed'])

    waiting_clients_len = len(waiting_clients)
    for i in range(0, waiting_clients_len):
        print(waiting_clients)

def HandleServerCommand(command, body):
    if (server_commands.get(command) == "help"):
        ShowServerMenu()
    if (server_commands.get(command) == "echo"):
        print(body)
    if (server_commands.get(command) == "show_clients"):
        ShowClients()
    if (server_commands.get(command) == "time"):
        print("Server time: " + str(datetime.now())[:19])
    if (server_commands.get(command) == "exit"):
        server_socket.close()
        os._exit(1)

def ShowServerMenu():
    for x in help_commands:
        print(x, ":", help_commands[x])

def ShowStartMessage():
    print("Server is start. Listen on %s:%d" %(IP, PORT))
    ShowServerMenu()



#---------------------------------------------------------
# Создание и бинд сокета сервера
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Stream = TCP
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(SERVER_ADDRESS)
server_socket.listen(1)

ShowStartMessage()

# Запуск потока для CLI сервера
server_cli = threading.Thread(target = ServerCLI)
server_cli.start()

# Создаем список подключенных и ожидающих клиентов
clients_pool = []
waiting_clients = []

# ???
inputs = [server_socket]
# ???
client_ID = 0


while True:

    inputready,outputready,exceptready = select.select(inputs,[], inputs)

    for ready_socket in inputready:
        if ready_socket == server_socket:
            client, client_info = server_socket.accept()

            client_ip = client_info[0]
            client_port = client_info[1]

            print("Accepted connection from: %s:%d" % (client_ip, client_port))

            client_obj = {
                            "id": client_ID,
                            "socket": client,
                            "ip": client_ip,
                            "is_closed": False,
                            "port": client_port
                        }

            clients_pool.append(client_obj)
            inputs.append(client)

            client_ID += 1

        else:
            request = ready_socket.recv(BUFFER_SIZE).decode('utf-8')
            found_client = SearchBySocket(clients_pool, ready_socket)
            if request:
                request = request.strip()
                if request != '':
                    print("Received a command: %s" %request)
                    HandleClientRequest(found_client, request)
            else:
                ExitClient(found_client)
