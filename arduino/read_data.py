import serial
import time

# ---------------- CONFIGURAÇÃO ----------------
PORTA = "COM4"
BAUDRATE = 115200
TIMEOUT = 1

arduino = serial.Serial(PORTA, BAUDRATE, timeout=TIMEOUT)
time.sleep(2)  # espera Arduino inicializar

# ---------------- LOOP DE TESTE ----------------
try:
    for pwm in range(100, 256):  # de 0 a 255
        for i in range(10):  # repetir 10 vezes
            # envia PWM
            arduino.write(f"{pwm}\n".encode())
            
            # lê a distância do Arduino
            linha = arduino.readline().decode().strip()
            if linha:
                print(f"PWM: {pwm}, Medida {pwm+1}: {linha}")
            time.sleep(0.1)

        time.sleep(0.1)  # espera 100ms entre leituras

except KeyboardInterrupt:
    print("Teste interrompido pelo usuário.")

finally:
    arduino.close()
