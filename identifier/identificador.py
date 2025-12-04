import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
from scipy.signal import lfilter
import matplotlib.pyplot as plt

# ==========================================
# 1. PARÂMETROS E MODELO FÍSICO (A VERDADE)
# ==========================================

# Parâmetros físicos
rho = 1.225       # densidade do ar (kg/m³)
g = 9.81          # gravidade (m/s²)
Cd = 0.47         # coeficiente arrasto típico de esfera
rb = 0.02         # raio da bolinha (m)
m = 0.0027        # massa (kg)
kv = 5            # Ganho do ventilador (m/s por Volt)
A = np.pi * rb**2 # área da bolinha
V_max_fan = 12    # Tensão máxima do cooler (12V é padrão, ajustei de 5 para 12)

def pwm_to_va(D):
    # D : Duty cycle (0 a 1)
    V_fan = V_max_fan * D 
    return V_fan * kv # velocidade ventilador (m/s)

def dynamics(t, x, D_atual):
    z, zdot = x
    va = pwm_to_va(D_atual)
    
    # Velocidade relativa (Ar - Bola)
    v_rel = va - zdot
    
    # Força de Arrasto (sempre se opõe ao movimento relativo, mas aqui simplificado para fluxo ascendente)
    # Adicionado np.sign para garantir física correta se a bola cair mais rápido que o ar
    drag_force = (0.5 * Cd * rho * A * (v_rel**2)) * np.sign(v_rel)
    
    zddot = (drag_force / m) - g
    return [zdot, zddot]

# ==========================================
# 2. GERAÇÃO DE DADOS DE TREINO (EXCITAÇÃO)
# ==========================================
print("Gerando dados de simulação...")

# Configurações de Amostragem
Ts = 0.05  # Tempo de amostragem (50ms) - Importante para o identificador discreto
T_total = 20 # Segundos de experimento
n_steps = int(T_total / Ts)

# Criar sinal de Excitação (PWM variando para "agitar" o sistema)
# PRBS (Pseudo-Random Binary Sequence) simples para identificação
u_train = np.zeros(n_steps)
nivel = 0.4 # Começa em 40%
for k in range(n_steps):
    if k % 40 == 0: # Muda de nível a cada 2 segundos (40 amostras)
        nivel = np.random.uniform(0.35, 0.75) # PWM entre 35% e 75%
    u_train[k] = nivel

# Loop de Simulação Discreta (Passo a Passo)
y_train = np.zeros(n_steps)
estado_atual = [0.0, 0.0] # [z, z_dot]

for k in range(n_steps - 1):
    # Simula a física por um intervalo Ts com o PWM constante u_train[k]
    sol = solve_ivp(dynamics, [0, Ts], estado_atual, args=(u_train[k],), method='RK45')
    
    # Atualiza o estado para o próximo passo
    estado_proximo = sol.y[:, -1]
    
    # Restrições físicas (chão e teto do tubo)
    if estado_proximo[0] < 0: 
        estado_proximo = [0, 0] # Bateu no chão
    elif estado_proximo[0] > 0.9: # Tubo de 90cm
        estado_proximo = [0.9, 0] # Bateu no teto
        
    estado_atual = estado_proximo
    y_train[k+1] = estado_atual[0]

# Adicionar um pouco de ruído de medição (realismo)
y_train_noisy = y_train + np.random.normal(0, 0.002, n_steps) 

# ==========================================
# 3. IDENTIFICADOR HAMMERSTEIN (GENÉTICO)
# ==========================================

def modelo_hammerstein(params, u_input):
    """
    Estrutura Hammerstein:
    1. Não-Linearidade Estática (Polinômio): v(k) = c0*u² + c1*u + c2
    2. Dinâmica Linear (Função de Transferência): G(z)
    """
    # Desempacota o cromossomo (genes)
    c0, c1, c2 = params[0:3]      # Coeficientes do Polinômio
    b1 = params[3]                # Numerador (ganho dinâmico)
    a1, a2 = params[4:6]          # Denominador (polos)

    # 1. Bloco Não-Linear
    v_intermed = c0 * (u_input**2) + c1 * u_input + c2
    
    # 2. Bloco Linear (Filtro IIR de 2ª ordem)
    # Função de Transferência estimada: G(z) = (b1*z^-1) / (1 + a1*z^-1 + a2*z^-2)
    # num = [0, b1], den = [1, a1, a2]
    num = [0, b1]
    den = [1, a1, a2]
    
    # Simula o filtro linear
    y_estimado = lfilter(num, den, v_intermed)
    return y_estimado

def funcao_fitness(params):
    # Penalidade para instabilidade (se polos > 1)
    if np.abs(params[4]) > 2 or np.abs(params[5]) > 1.5:
        return 1e9
        
    y_est = modelo_hammerstein(params, u_train)
    
    # Erro Quadrático Médio (MSE)
    erro = np.mean((y_train_noisy - y_est)**2)
    return erro

# Limites de busca para o Algoritmo Genético
# [c0, c1, c2, b1, a1, a2]
bounds = [(-10, 10), (-10, 10), (-5, 5), (-5, 5), (-2, 2), (-1, 1)]

print("Rodando Algoritmo Genético (Isso pode levar alguns segundos)...")
# Usa Differential Evolution (robusto para identificação)
result = differential_evolution(
    funcao_fitness, 
    bounds, 
    strategy='best1bin', 
    maxiter=50, 
    popsize=20,
    mutation=(0.5, 1), 
    recombination=0.7,
    disp=True
)

print(f"\nMelhor gene encontrado: {result.x}")
print(f"Erro Final (MSE): {result.fun}")

# ==========================================
# 4. VALIDAÇÃO DOS RESULTADOS
# ==========================================
y_validacao = modelo_hammerstein(result.x, u_train)
t_vec = np.linspace(0, T_total, n_steps)

plt.figure(figsize=(10, 8))

# Plot 1: Entrada PWM
plt.subplot(2, 1, 1)
plt.plot(t_vec, u_train, 'g', label='PWM (Entrada)')
plt.ylabel('Duty Cycle (0-1)')
plt.title('Sinal de Excitação')
plt.grid(True)

# Plot 2: Saída Real vs Identificada
plt.subplot(2, 1, 2)
plt.plot(t_vec, y_train_noisy, 'k', alpha=0.6, label='Dados Simulados (Física + Ruído)')
plt.plot(t_vec, y_validacao, 'r--', linewidth=2, label='Modelo Identificado (Hammerstein)')
plt.ylabel('Altura (m)')
plt.xlabel('Tempo (s)')
plt.title('Comparação: Modelo Físico vs Modelo Matemático Identificado')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()