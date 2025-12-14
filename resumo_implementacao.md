# Resumo da implementação (para apresentação)

Este documento resume **o que foi implementado** no projeto, como os módulos se conectam e como demonstrar o funcionamento (simulação e físico).

---

## 1) Arquitetura do projeto (visão em blocos)

**Fluxo de desenvolvimento e validação**
1. **Aquisição de dados (físico, malha aberta)** → coleta de pares (PWM, distância)
2. **Pré-processamento** → limpeza de ruído/outliers e padronização de unidades
3. **Identificação** → ajuste de um modelo de Hammerstein por Evolução Diferencial (DE)
4. **Controle** → controlador Fuzzy para gerar PWM a partir da medição
5. **Validação** → comparação em gráficos e métricas (MSE) e demonstração do sistema

---

## 2) Coleta de dados no sistema físico (Arduino)

**O que faz**
- Lê um valor de PWM via Serial, aplica no fan (pino PWM) e imprime a distância medida pelo sensor ultrassônico.

**Código**
- Sketch principal: [arduino/read_data_arduino.ino](arduino/read_data_arduino.ino)

**Variante do experimento (protocolo Serial para malha fechada)**
- Sketch: [controller/arduino_experimento.ino](controller/arduino_experimento.ino)
- Recebe comandos `FAN:XX` (0–100%) e envia leituras `DIST:YY.Y` (cm) a cada ~50 ms.

**Como funciona (resumo)**
- Entrada: valor inteiro de PWM (0–255) enviado pela porta serial.
- Saída: linhas no formato “Distância: X cm”, que podem ser logadas no PC.

**Observação prática**
- O script [arduino/read_data.py](arduino/read_data.py) é um exemplo de varredura de PWM e leitura serial (ajustar `PORTA` no macOS).

---

## 3) Pré-processamento do log (limpeza e CSV)

**Por que existe**
- Leituras de distância podem ter *spikes* (picos) e ruído; isso degrada fortemente a identificação.

**O que faz**
- Extrai (PWM, distância) do arquivo bruto.
- Remove saturações (limite de PWM) e remove *spikes* por variação máxima aceitável.
- Converte distância de cm para m (SI) ao salvar o CSV.

**Código**
- Conversão/limpeza: [identifier/conversor_dados.py](identifier/conversor_dados.py)
- Exemplo de dataset processado: [identifier/dados.csv](identifier/dados.csv)

---

## 4) Identificação: Modelo de Hammerstein + Evolução Diferencial

**O modelo implementado**
- Estrutura Hammerstein: 
  - **Bloco NL estático**: polinômio de 2º grau em `u(k)`
  - **Bloco L dinâmico**: filtro discreto IIR aplicado sobre a variável intermediária

**O que é estimado**
- Parâmetros do polinômio (NL) e coeficientes do filtro discreto (L).

**Otimização**
- Evolução Diferencial (`scipy.optimize.differential_evolution`) minimizando o **MSE** entre o sinal real e o sinal estimado.

**Detalhe importante (variável medida)**
- O dataset `dados.csv` contém **distância sensor→bola** em metros; por isso as curvas e o MSE da identificação são calculados nessa variável.

**Validação adicional**
- O script também inclui um **modelo físico simplificado** (equações do movimento + arrasto) para comparação e cálculo de MSE adicional.

**Código**
- Identificação completa: [identifier/identificador.py](identifier/identificador.py)

**Saídas típicas para mostrar em apresentação**
- Curvas: entrada PWM, saída real vs. Hammerstein vs. modelo físico, e erro.
- Métricas: MSE (real×Hammerstein, real×físico, Hammerstein×físico).

---

## 5) Controle: Controlador Fuzzy

**O que foi implementado (estado atual do código)**
- **Controlador Fuzzy melhorado** (biblioteca `scikit-fuzzy`) que mapeia **distância do sensor** (cm) para ação de controle (velocidade do fan em %).
- **Híbrido Fuzzy + correção proporcional**: após a inferência Fuzzy, aplica-se um termo proporcional `ganho_proporcional * erro` para reduzir erro estacionário.
- **Filtro de suavização** (média exponencial) para reduzir oscilações (`alpha_filtro`).
- **Velocidade mínima do fan** (`velocidade_minima`) para evitar “desligar” em regimes onde o fan não sustenta a esfera.
- **Calibração por dados reais**: funções de pertinência e um *lookup* distância→velocidade podem ser ajustados automaticamente a partir do histórico em CSV.

**Código**
- Controlador: [controller/controlador_fuzzy.py](controller/controlador_fuzzy.py)

**Baseline implementado (comparação)**
- Controlador proporcional simples (offset + `kp * erro` + *deadband*): [controller/controlador_proporcional.py](controller/controlador_proporcional.py)

**Interface principal**
- `calcular_velocidade(distancia_sensor_lida)` → retorna `0–100` (%), já com saturação.

---

## 6) Simulador (demonstração rápida sem hardware)

**O que faz**
- Simula a dinâmica da esfera com ruído de sensor, turbulência e perturbações, exibindo animação e sliders.
- Permite ligar/desligar o controle e visualizar convergência para a altura desejada.

**Códigos**
- Simulação base: [controller/simulador.py](controller/simulador.py)
- Variante com controlador acoplado: [controller/Experimento.py](controller/Experimento.py)

**Observação (modo físico via Serial)**
- O simulador também integra comunicação Serial com Arduino (`FAN:`/`DIST:`), permitindo alternar **Manual → Proporcional → Fuzzy** e registrar histórico.
- No macOS, é necessário ajustar a porta em [controller/simulador.py](controller/simulador.py) (ex.: `/dev/cu.usbserial-*`).

**Por que é útil na apresentação**
- Serve como “plano B” se o físico falhar.
- Ajuda a explicar ruído/turbulência e o papel do controlador.

---

## 7) Dependências e execução (para demo)

**Dependências (Python)**
- Lista: [controller/requirements.txt](controller/requirements.txt)

**Executar simulação (sugestão)**
- No diretório do projeto, executar:
  - `python controller/Experimento.py`

**Executar identificação (sugestão)**
- `python identifier/identificador.py`

**Demo físico (sequência recomendada em sala)**
1. Mostrar o setup físico (tubo, fan, sensor, Arduino)
2. Rodar leitura do sensor e confirmar que a distância varia
3. Aplicar PWM baixo → bola cai; PWM maior → bola sobe
4. (Se implementado em malha fechada) ativar controle e mostrar estabilização

---

## 8) Pontos fortes e limitações (para falar em 30–45 s)

**Pontos fortes**
- Pipeline completo: dados → limpeza → identificação → validação → controle.
- Identificação robusta a ruído (pré-processamento + metaheurística).
- Controle interpretável (regras linguísticas) e adequado a incertezas.

**Limitações atuais**
- O controlador implementado está focado em distância/posição e pode ser estendido para a forma PD-Fuzzy completa (erro e variação do erro), se desejado.
- Resultados dependem da qualidade do sensor (spikes) e do regime de operação do fan.
