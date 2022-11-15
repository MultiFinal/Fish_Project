import serial
import numpy as np
import cv2
import socket
import pybase64
from PIL import Image
from io import BytesIO
import time
import re
import struct

global buf
fish_weight=-1
# ser = serial.Serial('/dev/ttyACM1', 115200) # 아두이노 연결
#fish_weight = int(arduino.readline().decode()[:-2]) # 아두이노에서 받은 데이터
# if ser.readable():
#         ser.close()
#         ser.open()
#         fish_weight=ser.readline()
#         fish_weight=str(fish_weight)
#         fish_weight=re.findall("\d+.\d+",fish_weight)
#         fish_weight=fish_weight[0]
#         fish_weight=int(fish_weight)
buf = b''

# 라즈베리파이 -> 모델, 무게값 전송 함수
def Rpi_client(HOST,PORT) : 
        # 서버의 주소입니다. hostname 또는 ip
        
        #ddress를 사용할 수 있습니다.
        client_HOST = HOST
        # 서버에서 지정해 놓은 포트 번호입니다. 
        client_PORT = PORT       


        # 소켓 객체를 생성합니다. 
        # 주소 체계(address family)로 IPv4, 소켓 타입으로 TCP 사용합니다.  
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


        # 지정한 HOST와 PORT를 사용하여 서버에 접속합니다. 
        client_socket.connect((client_HOST, client_PORT))

        # 메시지를 전송합니다.
        client_socket.sendall(base64_string)
        client_socket.send(fish_weight)

        # 메시지를 수신합니다. 
        # data = client_socket.recv(1024)
        # print('Received', repr(data.decode()))

        # 소켓을 닫습니다.
        client_socket.close()

# 클라이언트 측의 메시지를 받기 위한 함수
def _get_bytes_stream(sock, length):
        global buf
        global data
        data = b''

        # recv함수에 할당된 버퍼 크기보다 클라이언트 측
        # 메시지가 더 큰 경우를 대비
        try:
            step = length
            while True:
                
                # 클라이언트 측의 메시지 수신
                data = sock.recv(step)
                buf += data

                # 빈문자열을 수신한다면 루프 종료
                if data==b'':
                    break
                
                # 메시지가 더 남아있다면 실행됨
                elif len(buf) < length:
                    step = length - len(buf)
        except Exception as e:
            print(e)
        return buf[:length]

# 모델 -> Rpi, 모델 분류 결과를 받기위한 함수
def Rpi_server(HOST,PORT) : 
    server_HOST = HOST
    # 클라이언트 접속을 대기하는 포트 번호입니다. 
    server_PORT = PORT
    
    # 소켓 객체를 생성합니다. 
    # 주소 체계(address family)로 IPv4, 소켓 타입으로 TCP 사용합니다.  
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 포트 사용중이라 연결할 수 없다는 
    # WinError 10048 에러 해결를 위해 필요합니다. 
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind 함수는 소켓을 특정 네트워크 인터페이스와 포트 번호에 연결하는데 사용됩니다.
    # HOST는 hostname, ip address, 빈 문자열 ""이 될 수 있습니다.
    # 빈 문자열이면 모든 네트워크 인터페이스로부터의 접속을 허용합니다. 
    # PORT는 1-65535 사이의 숫자를 사용할 수 있습니다.
    server_socket.bind((server_HOST, server_PORT))

    # 서버가 클라이언트의 접속을 허용하도록 합니다.
    server_socket.listen()

    # accept 함수에서 대기하다가 클라이언트가 접속하면 새로운 소켓을 리턴합니다. 
    client_socket, addr = server_socket.accept()


    _get_bytes_stream(client_socket,10000)

    # 소켓을 닫습니다.
    client_socket.close()
    server_socket.close()

fish_weight = 400
fish_weight = struct.pack(">H",fish_weight)
# 아두이노에서 무게값 전송 받으면 실행
#if(fish_weight) :
cap = cv2.VideoCapture(0) # 노트북 웹캠을 카메라로 사용
cap.set(3,640) # 너비
cap.set(4,480) # 높이

ret, frame = cap.read() # 사진 촬영
frame = cv2.flip(frame, 1) # 좌우 대칭

cv2.imwrite('self camera test.jpg', frame) # 사진 저장
    
cap.release()
cv2.destroyAllWindows()

with open('./self camera test.jpg', 'rb') as img:
    base64_string = pybase64.b64encode(img.read())

# 400에 무게 입력해야 합니다.
#fish_weight = (fish_weight).to_bytes(2,byteorder="little")

# RaspberryPi->PC, 무게값 전송
Rpi_client('192.168.0.108',9999)

# PC->RaspberryPi, 모델링 결과값 받기위한 서버 열기
Rpi_server('',9999)


# 전달받은 모델링 분류값
receive = buf.decode('utf-8')

# 어종
fish_type=receive[:2]

# 성어/치어
fish_check=receive[2:]

time.sleep(1)
fish_type = fish_type.encode('utf-8')   #str -> bytes 타입으로 인코딩
fish_check = fish_check.encode('utf-8')
result = fish_type+fish_check
print(result)
#     ser.write(result)
time.sleep(1)
