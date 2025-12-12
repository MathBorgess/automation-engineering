# Resumo da implementação (para apresentação)

Este documento resume **o que foi implementado** no projeto de identificação e controle do sistema de levitação pneumática, conectando **código → experimento → resultados**.

---

## 1) Visão geral da arquitetura

**Objetivo:** controlar a altura de uma esfera em um tubo de ar ajustando o PWM do ventilador.

**Componentes principais:**
- **Aquisição (físico):** Arduino + sensor ultrassônico (HC-SR04) + fan (PWM).
- **Dados:** logs com pares *(PWM, distância)*.
- **Pré-processamento:** remoção de saturação e spikes; conversão cm → m.
- **Identificação:** modelo de **Hammerstein** com parâmetros ajustados por **Evolução Diferencial** (DE).
- **Controle:** controlador **Fuzzy** (baseado em regras e funções de pertinência) com saída em % de velocidade/PWM.
- **Simulação:** simulador com ruído/turbulência para testar o controlador antes do físico.

---

## 2) Organização do repositório (o que cada parte faz)

### 2.1 Controle
- `controller/controlador_fuzzy.py`
  - Implementa um controlador Fuzzy (Mamdani via `scikit-fuzzy`).
  - Entrada: `distancia_sensor` (cm)
  - Saída: `velocidade_fan` (0–100%)
  - Possui funções para testar e visualizar funções de pertinência.

- `controller/simulador.py`
  - Simulador 2D do tubo/bola usando `matplotlib`.
  - Modela perturbações realistas (ruído de sensor, turbulência, perturbação de força, vibração).
  - Permite alternar **manual** (slider) e **automático** (Fuzzy ON/OFF).

- `controller/Experimento.py`
  - Especialização do simulador para rodar diretamente “Simulador com Controlador”.

### 2.2 Identificação
- `identifier/identificador.py`
  - Lê dados experimentais de `identifier/dados.csv`.
  - Identifica um modelo **Hammerstein**:
    - Bloco não-linear (polinômio de 2º grau): gera sinal intermediário `v` a partir do PWM normalizado.
    - Bloco linear (IIR discreto via `scipy.signal.lfilter`).
  - Ajusta parâmetros via **Evolução Diferencial** (`scipy.optimize.differential_evolution`) minimizando MSE.
  - Também simula um **modelo físico** simplificado (arrasto ∝ `v_rel^2`) com integração por `solve_ivp`.
  - Gera gráficos comparando: dados reais × Hammerstein × físico.

- `identifier/conversor_dados.py`
  - Converte `identifier/dados.txt` (log bruto) → `identifier/dados.csv` (tratado).
  - Filtra saturação (`pwm <= 240`) e remove spikes (limiar de variação em cm).
  - Converte cm → m ao salvar.

### 2.3 Aquisição no físico (Arduino)
- `arduino/read_data_arduino.ino`
  - Recebe PWM pela serial, aplica `analogWrite` no fan.
  - Mede distância com HC-SR04 e imprime “Distância: X cm”.

- `arduino/read_data.py`
  - Script Python para varrer PWM e registrar leituras via serial.
  - Observação: a porta está como `COM4` (adequado para Windows). No macOS, precisa trocar para `/dev/tty.*`.

---

## 3) Como executar (para preparar a apresentação)

### 3.1 Dependências
As bibliotecas do simulador/identificação incluem:
- `numpy`, `scipy`, `matplotlib`, `scikit-fuzzy`

Arquivo: `controller/requirements.txt`

### 3.2 Simulação com controlador (recomendado para demo “plano B”)
No diretório do projeto:
1. Rodar o simulador com controlador:
   - `python controller/Experimento.py`
2. Mostrar na apresentação:
   - botão **Fuzzy ON/OFF**
   - a esfera convergindo para a altura desejada
   - ruído no sensor e pequenas oscilações (comportamento realista)

Remember: a simulação é a forma mais segura de garantir demo caso o físico falhe.

### 3.3 Identificação (gerar gráficos e MSE)
1. (Opcional) Gerar `dados.csv` a partir do log bruto:
   - `python identifier/conversor_dados.py`
2. Rodar identificação + comparação com modelo físico:
   - `python identifier/identificador.py`
3. Mostrar na apresentação:
   - gráfico de comparação (real × Hammerstein × físico)
   - valores de MSE impressos no terminal

---

## 4) Demonstração no sistema físico (parte recomendada da apresentação)

**Objetivo da demo:** evidenciar que a planta real tem ruído/turbulência e que o controle/identificação são motivados por isso.

Roteiro rápido (3–4 min):
1) Mostrar o sensor lendo distância (bola em repouso/posição inicial).
2) Aplicar um PWM e mostrar a mudança de altura.
3) (Se possível) variar o PWM e mostrar a resposta.

Observações práticas:
- Preparar iluminação/posicionamento do sensor para minimizar leituras inválidas.
- Ensaiar com 2–3 PWMs pré-selecionados para não perder tempo.

---

## 5) O que dizer (frases curtas, “tom de apresentação”)

- “O pipeline fecha o ciclo: **coleta → limpeza → identificação → validação → controle**.”
- “A identificação por Hammerstein separa a não-linearidade do atuador da dinâmica do sistema.”
- “Usamos Evolução Diferencial para ajustar parâmetros minimizando MSE.”
- “O Fuzzy é adequado porque o sistema é não linear e sofre turbulência e ruído.”

---

## 6) Limitações atuais (para transparência acadêmica)

- O texto do artigo descreve um **Fuzzy PD (erro e variação do erro)**, enquanto a implementação atual do controlador usa **distância como entrada única**.
- A integração de malha fechada **100% no Arduino** (leitura → controle → PWM) ainda não está consolidada no código apresentado.

Sugestão para fala:
- “O controlador implementado hoje é uma versão baseada na distância; como evolução, podemos estender para PD‑Fuzzy completo e fechar malha no microcontrolador.”
