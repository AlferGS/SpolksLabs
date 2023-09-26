#var 7

import socket
import os
import os.path
import sys
import time
import re
from termcolor import colored
from commands import client_commands

PORT = 1357

BUFFER_SIZE = 1024
OOB_RATE = 100
TIMEOUT = 20
OK_STATUS = 200


def WaitingOK():
    while (client.recv(2).decode('utf-8') != "OK"):
        print("waiting for OK")

def SendingOK():
    client.send("OK".encode('utf-8'))

def GetData():
    return client.recv(BUFFER_SIZE).decode('utf-8')

def SendingData(data):
    client.send(str(data).encode('utf-8'))

def HandleClientRequest(request):
    command = request.split()
    name_command = command[0]
    body = ""

    if (len(command) == 2):
        body = command[1]

    if (client_commands.get(name_command) == "echo"):
        if len(body) == 0:
            print("Body of echo command is NULL")
            return
        SendingData(request)
        if (WaitingForAck(name_command) == False):
            return
        Echo()

    if (client_commands.get(name_command) == "time"):
        SendingData(request)
        if (WaitingForAck(name_command) == False):
            return
        GetTime()

    if (client_commands.get(name_command) == "download"):
        if len(body) == 0:
            print("Body of get command is NULL. Example 'get #file_name'")
            return
        SendingData(request)
        if (WaitingForAck(name_command) == False):
            return
        Download(body, request)

    if (client_commands.get(name_command) == "upload"):
        if len(body) == 0:
            print("Body of post command is NULL. Example 'post #file_name'")
            return
        if (IsFileExist(body)):
            SendingData(request)
            if (WaitingForAck(name_command) == False):
                return
            Upload(body, request)
        else:
            ShowErrorMessage("No such file exists")

    if (client_commands.get(name_command) == "help"):
        ShowServerMenu()

    if (client_commands.get(name_command) == "exit"):
        SendingData(request)
        if (WaitingForAck(name_command) == False):
            return
        client.close()
        os._exit(1)

    if client_commands.get(name_command) == None:
        print(f"Command '{request}' does not exist")

def WaitingForAck(command_to_compare):
    while True:
        response = client.recv(BUFFER_SIZE).decode('utf-8').split(" ", 2)

        if not response:
            return False

        sent_request = response[0]
        status = response[1]

        if (len(response) > 2):
            message = response[2]
        else:
            message = None

        if (command_to_compare == sent_request and int(status) == OK_STATUS):
            return True
        elif (message):
            print(message)
            return False
        else:
            return False

def IsServerAvailable(request, command):
    global client
    client.close()
    i = TIMEOUT
    while(i > 0):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((HOST, PORT))
            client.send(request.encode('utf-8'))
            WaitingForAck(command)
            return True
        except socket.error as er:
            sys.stdout.write("Waiting for a server: %d seconds \r" %i)
            sys.stdout.flush()
        i -= 1
        time.sleep(1)

    sys.stdout.flush()
    print("\nServer was disconnected")
    sys.stdout.flush()
    return False


def IsFileExist(file_name):
    return os.path.exists(file_name)

def Echo():
    print(GetData())

def GetTime():
    print(GetData())

def Download(file_name, request):
    file_size = int(GetData())
    SendingOK()
    SendingData(0)
    data_size_recv = int(GetData())
    SendingOK()
    if (data_size_recv == 0):
        file = open(file_name, "wb")
    else:
        file = open(file_name, "rb+")

    time_start = time.time()
    progress_bar = 10
    while (data_size_recv < file_size):
        try:
            data = client.recv(BUFFER_SIZE)
            file.seek(data_size_recv, 0)
            file.write(data)
            data_size_recv += BUFFER_SIZE
            progress = (data_size_recv / file_size) * 100

            if (progress >= progress_bar):
                print("Download progress: %d%% " % progress)
                progress_bar += 10

        except socket.error as e:
            if(IsServerAvailable(request, "download")):
                size = int(GetData())
                SendingOK()
                SendingData(data_size_recv)
                data_size_recv = int(GetData())
                SendingOK()
                print("\n")
            else:
                file.close()
                client.close()
                os._exit(1)

        except KeyboardInterrupt:
            print("KeyboardInterrupt was handled")
            file.close()
            client.close()
            os._exit(1)

    file.close()
    print("\n"+"DOWNLOADING COMPLETE (" + file_name + ")")
    time_end = time.time()
    delta_time = (time_end - time_start)
    print("Total time: %f ms" %delta_time)
    speed = (file_size/1024**2)/delta_time*1000
    print("Average speed: %f M/s" % speed)

def Upload(file_name, request):

    f = open (file_name, "rb+")
    size = int(os.path.getsize(file_name))
    SendingData(size)
    WaitingOK()
    SendingData(0)
    data_size_recv = int(GetData())
    WaitingOK()
    f.seek(data_size_recv, 0)
    time_start = time.time()
    progress_bar = 10
    while (data_size_recv < size):
        try:
            data_file = f.read(BUFFER_SIZE)
            client.send(data_file)
            progress = (data_size_recv / size) * 100

            if (progress >= progress_bar):
                print("Download progress: %d%% " % progress)
                progress_bar += 10

            data_size_recv += BUFFER_SIZE
            f.seek(data_size_recv, 0)

        except socket.error as e:
            if(IsServerAvailable(request, "upload")):
                SendingData(size)
                WaitingOK()
                SendingData(data_size_recv)
                data_size_recv = int(GetData())
                WaitingOK()
                print("\n")
            else:
                f.close()
                client.close()
                os._exit(1)

        except KeyboardInterrupt:
            print("KeyboardInterrupt was handled")
            f.close()
            client.close()
            os._exit(1)

    f.close()
    print("\n"+"UPLOADING COMPLETE (" + file_name + ")")
    time_end = time.time()
    delta_time = (time_end - time_start)
    print("Total time: %f ms" %delta_time)
    speed = (size/1024**2)/delta_time
    print("Average speed: %f m/s" % speed)

def CheckValidRequest(request):
    command = request.split()
    if (len(command) == 0):
        return False
    else: return True

def ShowErrorMessage(error):
    print(error)

def ShowStartMessage():
    print("\nWelcome to client cli!")
    ShowServerMenu()

def ShowServerMenu():
    for x in client_commands:
        print(colored(x,"yellow"), colored(": ","yellow"), colored(client_commands[x],"yellow"))

is_valid_address = False

REGULAR_IP = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'
regex = re.compile(REGULAR_IP)


while (is_valid_address == False):
    addr = input("\nInput host address: ")
    if (regex.match(addr)):
        is_valid_address = True
        HOST = addr
    else:
        try:
            HOST = socket.gethostbyname(addr)
            is_valid_address = True
        except socket.error:
            print("Please, input valid address")
            is_valid_address = False


ShowStartMessage()
server_address = (HOST, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(server_address)


while True:

    try:
        request = input()
        if (CheckValidRequest(request)):
            HandleClientRequest(request)
    except KeyboardInterrupt:
        print("KeyboardInterrupt was handled")
        continue
        # client.close()
        # os._exit(1)
