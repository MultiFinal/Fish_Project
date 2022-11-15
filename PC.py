#--------------------------------- 라이브러리 ---------------------------------

# 소켓 관련 라이브러리
from PIL import Image, ImageFile
from io import BytesIO
import socket
from PIL import Image
import pybase64



# 모델 관련 라이브러리
from PIL import Image
import tensorflow as tf
from tensorflow.keras.applications import ResNet50 
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
import numpy as np
model = tf.keras.models.load_model('./model/ResNet50_Adadelta_Patience10.h5') 



# DB 관련 라이브러리
# !pip3 install influxdb-client
# pip install tensorflow
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

#--------------------------------- 변수 설정 ---------------------------------

# 소켓 관련 변수
global buf
buf = b''
global data
global result



#모델 관련 변수
fish_weight = 0
fish_img = './fish.jpg'
img_size = 224

fish_id=0 
small_cnt=0 # 치어 포획량



# DB 관련 변수 (커넥션 설정)
bucket="SeaProject"
org = "mint3024@daum.net"
token = "Q7-n7NN5Bf-1tTgpr2eOs6-hi6e7S7g8_z2vYR98KsQXM-1j75-ytnnSOue8dMm_cWSjMMGDzqXMTWTa0xU1NA=="
url = "https://europe-west1-1.gcp.cloud2.influxdata.com"
client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS) # 쓰기 API 구성 : 실시간 동기화

# --------------------------------- 소켓 함수 1 (클라이언트의 데이터 수신) ---------------------------------

# 클라이언트 측의 메시지를 받기 위한 함수
def _get_bytes_stream(sock, length):
    global buf
    global data
    data = b''

    # recv 함수에 할당된 버퍼 크기보다 클라이언트 메시지가 더 큰 경우를 대비
    try:
        step = length
        while True: 

            # 클라이언트 측의 메시지 수신
            data = sock.recv(step)
            buf += data

            # 빈문자열을 수신한다면 루프 종료
            if data==b'':
                break

            # 메시지가 더 남아있다면 실행
            elif len(buf) < length:
                step = length - len(buf)
    except Exception as e:
        print(e)
    return buf[:length]

    #--------------------------------- 소켓 함수 2 ( Model에 서버를 오픈 ) ---------------------------------

def PC_server(HOST,PORT) : 
    server_HOST = HOST # hostname, ip address, 빈 문자열 ""이 될 수 있음
    server_PORT = PORT # 클라이언트 접속을 대기하는 포트 번호. 1-65535 사이의 숫자 사용 가능

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # 소켓 객체 생성. 주소체계: IPv4, 소켓타입: TCP 사용


    # 포트 사용중이라 연결할 수 없다는 WinError 10048 에러 해결을 위해 필요 
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 소켓을 특정 네트워크 인터페이스와 포트 번호에 연결하는데 사용
    # 빈 문자열이면 모든 네트워크 인터페이스로부터의 접속을 허용
    server_socket.bind((server_HOST, server_PORT))

    # 서버가 클라이언트의 접속 허용 
    server_socket.listen()

    # accept 함수에서 대기하다가 클라이언트가 접속하면 새로운 소켓을 리턴
    client_socket, addr = server_socket.accept()

    # 접속한 클라이언트의 주소
    print('Connected by', addr)

    _get_bytes_stream(client_socket,10000)

    client_socket.close()
    server_socket.close() 

    # -------------------------------- 소켓 함수 3 ( RaspberryPi => Model 데이터값 전송 ) ---------------------------------

def receive_data(data):
    global fish_img
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        fish_weight=int.from_bytes(data[-2:],"little") # 생선 무게 받기
        buf_new = data + bytes('=','utf-8') * (4-len(data) % 4) # 전송 받은 데이터에 문제 발생 방지를 위한 코드
        img = Image.open(BytesIO(pybase64.b64decode(buf_new)))
        img = img.convert('RGB')
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = False

    img.save('fish.jpg',"JPEG") # 이미지 저장
    fish_img = image.load_img(fish_img, target_size=(img_size,img_size)) #이미지로드

    # -------------------------------- 소켓 함수 4  ( Model => RaspberryPi 데이터값 전송 ) ---------------------------------

def PC_client(HOST, PORT):
    global result
    client_HOST = HOST
    client_PORT = PORT 

    fish_type = bytes(result[0],'utf-8')
    fish_check = bytes(result[1],'utf-8')

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_socket.connect((client_HOST, client_PORT))

    client_socket.send(fish_type)
    client_socket.send(fish_check)

    client_socket.close()

    #--------------------------------- Model 함수 ( Input : 이미지, 무게 => Output: 어종, 치어여부 ) ---------------------------------

def AI_check(fish_img, fish_weight): 
    global result
    #샘플이미지 전처리
    model_fish_img = image.img_to_array(fish_img) 
    model_fish_img = np.expand_dims(fish_img, axis=0)
    model_fish_img = preprocess_input(model_fish_img)

    # Model 가동
    result_img = model.predict(model_fish_img)


    # 어종판별, 기준무게 설정
    if np.argmax(result_img) == 0: # 감성돔
        fish_type='BP'
        standard_weight= 392 
    elif np.argmax(result_img) == 1: # 돌돔
        fish_type= 'RB'
        standard_weight= 331
    elif np.argmax(result_img) == 2: # 참돔
        fish_type='RS'
        standard_weight= 210

    # 치어판별, 치어갯수 추가
    if fish_weight < standard_weight:
        fish_check = 'small'
    else: 
        fish_check = 'adult'
    
    # 라즈베리파이로 전송되는 결과
    result = [fish_type, fish_check] # 어종 / 치어여부 
    return result
   
   #--------------------------------- DB 전송을 위한 데이터 가공 함수 ( Input : 어종, 치어여부 => Output: ID, 치어비율, 어종, 치어여부 ) ---------------------------------

def DB_preprocess(fish_type, fish_check):
    global fish_id 
    global small_rate
    global small_cnt

        
    # 어종 한글 변환
    if fish_type =='BP': 
        fish_type ='감성돔'

    elif fish_type =='RB': 
        fish_type = '돌돔'

    elif fish_type =='RS': 
        fish_type ='참돔'

    # 치어여부 한글 변환 
    if fish_check =='adult': 
        fish_check ='성어'

    elif fish_check =='small': 
        fish_check = '치어'
        small_cnt+=1 # 치어 마리수 계산
    
    fish_id += 1  # 물고기 마리수 계산 
    small_rate= (small_cnt/ fish_id)*100 # 물고기 비율 계산

    result = [fish_id, small_rate, fish_type, fish_check] # 아이디, 치어 비율, 어종, 치어 여부 
    return result

    #--------------------------------- DB 전송 함수 ---------------------------------

def send_to_DB(id, small_rate, fish_type, fish_check):
    points = (
        Point("어종4") # Point1: ID, 어종
        .tag(key="id", value=id)
        .field(fish_type, value=int(1)), 
        Point("치어여부4")  # Point2: ID, 치어여부
        .tag(key="id", value=id)
        .field(fish_check, value=int(1)), 
        Point("치어비율4" ) #  Point3: 치어비율
        .field("치어_비율", value=small_rate)
    )
    write_api = client.write_api(write_options=SYNCHRONOUS) # 쓰기 API 구성 : 실시간 동기화
    return points

def final ():
    global buf
    global fish_img
    global fish_weight
    PC_server('',9999) # Model 서버 Open
    while True:
        if not buf=='': # buf에 데이터값이 들어왔다면
            receive_data(buf) # RaspberryPi에서 데이터값 수신

            AI_result = AI_check(fish_img, fish_weight) # Model 가동 

            PC_client('192.168.1.44', 9999) # RaspberryPi에 Model 결과값 전송 
            DB_result= DB_preprocess(AI_result[0], AI_result[1]) # DB에 보낼 데이터값 가공

            points = send_to_DB(DB_result[0], DB_result[1], DB_result[2], DB_result[3])
            write_api.write(bucket=bucket, org=org, record=points) # DB에 데이터값 전송 
            buf='' # buf에 데이터값 삭제
            break
            # final() # 무한반복

# 이러면 특정 measurement
# client = InfluxDBClient(url=url, token=token, org=org)
# delete_api = client.delete_api()
# delete_api.delete('1970-01-01T00:00:00Z', '2022-11-11T00:00:00Z', '_measurement="여기다가 measurement 이름을 넣으세요"',bucket=bucket )

final()