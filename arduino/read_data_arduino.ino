#include <Arduino.h>

// ---------------- Ventoinha -----------------
const int pwmPin = 9;

// ---------------- HC-SR04 -------------------
const int trigPin = 5;
const int echoPin = 7;

int pwmValueInt = 0; // PWM convertido para analogWrite
unsigned long lastMeasurement = 0;
const unsigned long interval = 200; // tempo entre leituras em ms

void setup() {
    Serial.begin(115200);

    pinMode(pwmPin, OUTPUT);
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);

    analogWrite(pwmPin, 150); // valor inicial
    delay(1000);

    Serial.println("Digite o valor de PWM (0-255) no Serial Monitor.");
}

void loop() {
    // ----------- Ler PWM do Serial Monitor -----------
    if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n'); // lê até ENTER
        input.trim(); // remove espaços

        int valor = input.toInt(); // converte para int
        if (valor < 0) valor = 0;
        if (valor > 255) valor = 255;

        pwmValueInt = valor;
        analogWrite(pwmPin, pwmValueInt);

        Serial.print("PWM ajustado para: ");
        Serial.println(pwmValueInt);
    }

    // ----------- Ler distância HC-SR04 -----------

        digitalWrite(trigPin, LOW);
        delayMicroseconds(2);
        digitalWrite(trigPin, HIGH);
        delayMicroseconds(10);
        digitalWrite(trigPin, LOW);

        // Mede tempo do ECHO
        long duration = pulseIn(echoPin, HIGH);

        // Converte para distância em cm
        float distance = duration * 0.0343 / 2;

        Serial.print("Distância: ");
        Serial.print(distance);
        Serial.println(" cm");

        delay(200);
    
}
