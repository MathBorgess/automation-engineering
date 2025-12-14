/*
 * Código Arduino para controle do experimento
 * - Recebe velocidade do fan via Serial (0-100%)
 * - Controla fan via PWM na porta 9
 * - Lê sensor ultrassônico nos pinos 5 (trigger) e 7 (echo)
 * - Envia distância medida via Serial
 */

// Pin definitions
const int FAN_PWM_PIN = 9;        // PWM para controlar o fan
const int TRIGGER_PIN = 5;        // Trigger do sensor ultrassônico
const int ECHO_PIN = 7;           // Echo do sensor ultrassônico

// Variáveis
int velocidade_fan = 0;           // Velocidade do fan (0-100%)
unsigned long ultima_leitura = 0; // Controle de timing
const unsigned long INTERVALO_LEITURA = 50; // Leitura a cada 50ms (20Hz)

void setup() {
  // Inicializar Serial
  Serial.begin(9600);
  
  // Configurar pinos
  pinMode(FAN_PWM_PIN, OUTPUT);
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  // Inicializar fan em 0
  analogWrite(FAN_PWM_PIN, 0);
  // Aguardar conexão Serial (opcional, para debug)
  // while (!Serial) {
  //   ; // Aguardar conexão Serial (descomente se usar USB)
  // }
  
  Serial.println("ARDUINO_READY");
}

void loop() {
  // Ler comandos da Serial
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    // Processar comando de velocidade do fan
    // Formato esperado: "FAN:50" ou apenas "50"
    if (comando.startsWith("FAN:")) {
      int valor = comando.substring(4).toInt();
      if (valor >= 0 && valor <= 100) {
        velocidade_fan = valor;
        // Converter 0-100% para 0-255 (PWM)
        int pwm_value = map(velocidade_fan, 0, 100, 0, 255);
        analogWrite(FAN_PWM_PIN, pwm_value);
      }
    } else if (comando.length() > 0 && comando.length() <= 3) {
      // Se for apenas um número, assumir que é a velocidade
      int valor = comando.toInt();
      if (valor >= 0 && valor <= 100)    {
        velocidade_fan = valor;
        int pwm_value = map(velocidade_fan, 0, 100, 0, 255);
        analogWrite(FAN_PWM_PIN, pwm_value);
      }
    }
  }
  
  // Ler sensor ultrassônico periodicamente
  unsigned long tempo_atual = millis();
  if (tempo_atual - ultima_leitura >= INTERVALO_LEITURA) {
    ultima_leitura = tempo_atual;
    
    // Medir distância
    float distancia = ler_sensor_ultrasonico();
    
    // Enviar distância via Serial
    // Formato: "DIST:25.5"
    Serial.print("DIST:");
    Serial.println(distancia, 1);
  }
}

float ler_sensor_ultrasonico() {
  // Limpar trigger
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  
  // Enviar pulso de 10 microsegundos
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
  
  // Ler tempo de eco
  long duracao = pulseIn(ECHO_PIN, HIGH, 30000); // Timeout de 30ms
  
  // Calcular distância em cm
  // Velocidade do som: 343 m/s = 0.0343 cm/μs
  // Distância = (tempo * velocidade) / 2 (ida e volta)
  float distancia = 0;
  if (duracao > 0) {
    distancia = (duracao * 0.0343) / 2.0;
  }
  
  // Filtrar valores inválidos (muito longe ou muito perto)
  if (distancia < 2 || distancia > 400) {
    distancia = 0; // Valor inválido
  }
  
  return distancia;
}

