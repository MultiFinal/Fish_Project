/* 라이브러리 불러오기 */
#include <Servo.h>              // 서보모터   라이브러리
#include <Wire.h>               // I2C 통신  라이브러리
#include <HX711.h>              // 무게 센서  라이브러리
#include <SoftwareSerial.h>     // 블루투스   라이브러리
#include <LiquidCrystal_I2C.h>  // LCD 모니터 라이브러리

/* 무게센서 교정계수 설정*/
unsigned int calibration_factor=610;

/* 상수 선언 : 핀 번호, 속도제어, 서보모터의 각도*/
#define PIN_DC_DIRECTION 13  // DC모터(레일) 방향을 정하는 핀(Motor B)
#define PIN_DC_SPEED 11     

#define PIN_SERVO 9          // 서보모터 연결 핀
#define PIN_LSERVO A3        // 무게센서 서보모터 연결 핀

#define BLUETOOTH_TX 7       //블루투스 연결 핀
#define BLUETOOTH_RX 6       

#define PIN_IR A0            // 적외선 IR센서 연결 핀

#define DOUT A2              // 무게센서 연결 핀
#define CLK A1               

#define POS_Small 70                   // 치어 분류를 위한 서보모터의 각도

int POS_Lservo=10;

/*변수 선언*/
int fish_weight;                          // 물고기의 무게
String fish_data = "";                      // NodMCU에서 받은 치어 여부
String fish_type = "";
String fish_check = "";
String fish_name = "";
Servo servo;                             //분류 서보모터
Servo Lservo;                            //무게센서 서보모터

SoftwareSerial bluetooth(BLUETOOTH_RX, BLUETOOTH_TX);

int railSpeed = 100;                      // 레일 기본 속도, 초기값은 160
bool isRailMoving = false;                // 레일 상태값
bool isWorking=false;                     // 블루투스로 프로그램 온오프 조절

HX711 scale;                   //setup에서 begin
//HX711 scale(DOUT,CLK);       라이브러리 버전에 따라서 다를 수 있음


LiquidCrystal_I2C lcd(0x27,16,2);

void setup(){
  Serial.begin(115200);
  scale.begin(DOUT, CLK);
  /* 모터 설정 */
  pinMode(PIN_DC_DIRECTION, OUTPUT);     // dc모터의 방향을 제어하는 핀을 output으로 설정
  digitalWrite(PIN_DC_DIRECTION, HIGH);   // 방향은 전진. 의도한 방향과 반대일 경우 HIGH -> LOW로 변경

  /*서보모터 초기화*/
  servo.attach(PIN_SERVO);               // 서보모터를 아두이노와 연결
  servo.write(0);                        // 각도 초기화
  delay(500);                            // 서보모터가 완전히 동작을 끝낸 후 detach를 위해 delay를 부여
  servo.detach();                        // 서보모터와 아두이노 분리
  
  /*무게센서 서보모터 초기화*/
  pinMode(PIN_LSERVO,OUTPUT);            // 무게센서 서보모터 핀을 디지털핀 OUTPUT으로 설정
  Lservo.attach(PIN_LSERVO);             
  Lservo.write(0);                        
  delay(500);                            
  Lservo.detach();   
        
  /* 적외선 센서 설정 */
  pinMode(PIN_IR, INPUT);                // 적외선 센서 핀을 디지털핀 INPUT으로 설정

  /* 무게 센서 조정 */
  scale.set_scale(calibration_factor);   // 교정계수
  scale.tare();                          // 영점잡기. 현재 측정값을 0으로 둔다.

  lcd.init();                           // 최신 버전 begin 구버전 init
  lcd.backlight();
  
  /* 블루투스 설정 */
  bluetooth.begin(9600);                 // 9600baud rate로 블루투스 통신 시작
  bluetooth.write('n');
}

void loop() {
  if(bluetooth.available()) btHandler(); // 블루투스 통신으로부터 전달 된 값이 있다면 btHandler()함수에서 처리
 
  if(!isWorking) return;

  /*무게 센서의 물고기를 컨베이어 벨트로 옮김*/
  if(scale.get_units(4)>3){           //무게가 감지되면 시작            
    fish_weight=scale.get_units(10)*20;  //1초 후에 무게 저장
    delay(1000);    
    Lservo.attach(PIN_LSERVO);
    for(POS_Lservo=10;POS_Lservo<=95;POS_Lservo++)
    {
      Lservo.write(POS_Lservo);
      delay(5);
    }
    delay(500);
    POS_Lservo=10;
    Lservo.write(POS_Lservo);
    delay(500);
    Lservo.detach();
  }
  else{
     delay(1000);
     return;                              //무게 센서에 신호가 없으면 loop문 처음으로 돌아간다.
  }  

  analogWrite(PIN_DC_SPEED,railSpeed);    //컨베이어 벨트 작동 시작
  isRailMoving = true;
  delay(1000);
    
  /* 적외선 센서에서 감지하면 카메라에서 레일 정지 */
  while(isRailMoving==true){        
     if(digitalRead(PIN_IR)==LOW){        // 적외선 센서는 물건 감지 시 LOW값을 전달. HIGH라는 것은 감지되지 않았음
        Serial.println(fish_weight);      // 라즈베리 파이에 무게 정보 전달
        analogWrite(PIN_DC_SPEED, 0);     // 적외선 센서에서 제품을 감지하여 일시 정지
        toneDetected();                   // 감지되었을 때 나오는 소리를 부저에 출력
        isRailMoving = false;
     }
  }

  while(true)
  {
  if(Serial.available())
  {
    fish_data=Serial.readString(); // 입력값 저장
    fish_data.trim();
    fish_type = fish_data.substring(0,2); // 앞의 두글자는 어종
    fish_check = fish_data.substring(2);  // 뒤의 두글자는 치어 여부

    if(fish_type=="KR") fish_name="Korean Rockfish";   //풀네임 변경
    else if(fish_type=="RS") fish_name="Red Seabream";
    else if(fish_type=="RB") fish_name="Rock Bream";

    lcd_write();

    if(fish_check=="adult")
    {
      bluetooth.write('a');
      delay(2000);
    }
    else if(fish_check=="small")
    {
      servo.attach(PIN_SERVO);             
      servo.write(POS_Small);
      analogWrite(PIN_DC_SPEED,railSpeed);
      isRailMoving=true;
      delay(2000);
      servo.write(0);
      delay(500);
      servo.detach();
  
      bluetooth.write('s');
    }
    delay(1000);

   if(scale.get_units(4)>3){    //저울에 다음 표본이 대기 중일 경우 멈추지 않고 진행
     return;
   }

    analogWrite(PIN_DC_SPEED,0);
    isRailMoving=false;
    break;

   }//if(Serial.available())
  }//while(true)
}//loop
/* 블루투스 동작 함수*/
void btHandler() {
  char b = bluetooth.read();               // 블루투스로부터 읽어온 값을 변수에 저장
  bluetooth.flush();                       // 나머지 의미없는 통신 값을 정리

  if(b == 'c'){                            // 'c': 시스템의 현재 상태를 요구
    if(isWorking) bluetooth.write('y');// "Yes"의 'y'를 스마트폰에 전달
    else bluetooth.write('n');            // "NO"의 'n'을 스마트폰에 전달
     
  }else if(b == '0'){                      // '0' : 작동중인 스마트 팩토리를 정지
    isWorking = false;                 // 레일의 움직임 상태를 나타내는 isRailMoving 변수의 값을 false로 바꿈
    analogWrite(PIN_DC_SPEED, 0);         // 레일 정지
    bluetooth.write('n');                 // "NO"의 'n'을 스마트폰에 전달
  }else if(b == '1'){                      // '1' : 정지중인 스마트 팩토리를 가동
    isWorking = true;                  // 레일의 움직임 상태를 나타내는 isRailMoving 변수의 값을 true로 바꿈
    bluetooth.write('y');                 // "Yes"의 'y'를 스마트폰에 전달
  }
}

void lcd_write(){
    lcd.setCursor(0,0);
    lcd.print(fish_name);
  
    lcd.setCursor(0,1);
    lcd.print('(');
    lcd.setCursor(1,1);
    lcd.print(fish_weight);
    lcd.setCursor(4,1);
    lcd.print('g');
    lcd.setCursor(5,1);
    lcd.print(')');
    
    lcd.setCursor(9,1);
    lcd.print(fish_check);
    analogWrite(PIN_DC_SPEED,railSpeed);
    isRailMoving=true;
    Serial.println(fish_check);
}

/* 적외선 센서, 색상감지 센서에서 물체를 감지했을 때 나오는 소리를 출력 */
void toneDetected() {                                                                                                                                             
  tone(4, 523, 50);                        // '도'에 해당. 0.05초간 출력
  delay(100);                              // 0.1초간 대기(출력시간 0.05초 + 대기시간 0.05초 = 0.1초)
  tone(4, 784, 50);                        // '미'에 해당. 0.05초간 출력
  delay(100);                              // 0.1초간 대기(출력시간 0.05초 + 대기시간 0.05초 = 0.1초)
}
