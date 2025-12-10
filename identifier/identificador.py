import numpy as np
import csv
import os
from scipy.signal import lfilter
from scipy.optimize import differential_evolution
import matplotlib.pyplot as plt

# ==========================================
# 1. CARREGAMENTO E TRATAMENTO DE DADOS
# ==========================================
arquivo_csv = "identifier/dados.csv"

# Verifica se o arquivo existe antes de tentar abrir
if not os.path.exists(arquivo_csv):
    print(f"[ERRO] O arquivo '{arquivo_csv}' não foi encontrado.")
    print("Execute o 'conversor_dados.py' primeiro.")
    exit()

pwms = []
distancias = []

# Leitura do CSV
with open(arquivo_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            pwm_val = int(row["pwm"])
            dist_val = float(row["distancia"]) # Já deve estar em Metros pelo conversor
            pwms.append(pwm_val)
            distancias.append(dist_val)
        except ValueError:
            continue

# Conversão para Numpy e Normalização
# Normalizamos o PWM (0-255) para (0.0 - 1.0) para facilitar a convergência do polinômio
u_train = np.array(pwms) / 255.0
y_real = np.array(distancias)

# Definição do tempo (assumindo 50ms de amostragem do Arduino)
Ts = 0.05 
n_steps = len(u_train)
t_vec = np.arange(n_steps) * Ts

print(f"\n[INFO] Dados carregados: {n_steps} amostras.")
print(f"[INFO] Faixa de Altura: {min(y_real):.2f}m a {max(y_real):.2f}m")

# ==========================================
# 2. DEFINIÇÃO DO MODELO HAMMERSTEIN
# ==========================================

def modelo_hammerstein(params, u_input):
    """
    Estrutura do Modelo:
    1. Não-Linearidade (Polinômio 2º grau): v = c0*u^2 + c1*u + c2
    2. Dinâmica (Filtro IIR 2ª ordem): G(z) = (b1*z^-1 + b2*z^-2) / (1 + a1*z^-1 + a2*z^-2)
    
    Vetor de Parâmetros (7 genes):
    [c0, c1, c2, b1, b2, a1, a2]
    """
    # Desempacota os genes
    c0, c1, c2 = params[0:3] # Coeficientes NL
    b1, b2 = params[3:5]     # Numerador
    a1, a2 = params[5:7]     # Denominador

    # Bloco 1: Não-Linearidade Estática (Curva do Ventilador)
    v_intermed = c0 * (u_input**2) + c1 * u_input + c2
    
    # Bloco 2: Dinâmica Linear (Física da Bola)
    # Numerador: [0, b1, b2] -> O '0' inicial representa o atraso natural de 1 amostra (z^-1)
    num = [0, b1, b2]
    den = [1, a1, a2]
    
    # Aplica o filtro linear sobre o sinal intermediário
    y_estimado = lfilter(num, den, v_intermed)
    
    return y_estimado

def funcao_fitness(params):
    """
    Calcula o erro entre o modelo proposto e os dados reais.
    """
    # 1. Penalidade de Instabilidade
    # Se os coeficientes do denominador forem muito altos, o sistema é instável.
    # O AG deve evitar essas regiões.
    a1, a2 = params[5], params[6]
    if abs(a1) > 2.5 or abs(a2) > 1.5:
        return 1e6 # Retorna um erro gigante para descartar esse gene
        
    # 2. Gera a saída do modelo atual
    y_est = modelo_hammerstein(params, u_train)
    
    # 3. Calcula o Erro Quadrático Médio (MSE)
    # Ignora os primeiros 10 passos para evitar erro de condição inicial
    erro = np.mean((y_real[10:] - y_est[10:])**2)
    
    if np.isnan(erro):
        return 1e6
        
    return erro

# ==========================================
# 3. OTIMIZAÇÃO (ALGORITMO EVOLUTIVO)
# ==========================================

# Limites de busca para cada parâmetro [min, max]
# c0,c1,c2 (NL) | b1,b2 (Num) | a1,a2 (Den)
bounds = [
    (-20, 20), (-20, 20), (-10, 10), # Polinômio pode ter ganhos altos
    (-5, 5), (-5, 5),                # Numerador
    (-2, 2), (-1, 1)                 # Denominador (limitado para estabilidade)
]

print("\n[INFO] Iniciando Algoritmo de Evolução Diferencial...")
print("       Isso pode levar de 30s a 2min dependendo do PC.\n")

result = differential_evolution(
    funcao_fitness,
    bounds,
    strategy='best1bin', # Estratégia padrão robusta
    maxiter=100,         # Número de gerações
    popsize=20,          # Tamanho da população (20 * 7 parâmetros = 140 indivíduos)
    mutation=(0.5, 1),   # Taxa de mutação
    recombination=0.7,   # Taxa de cruzamento
    disp=True,           # Mostra o progresso no terminal
    workers=-1           # Usa todos os núcleos da CPU
)

# ==========================================
# 4. RESULTADOS E VALIDAÇÃO
# ==========================================

melhores_params = result.x
erro_final = result.fun

print("\n" + "="*40)
print("       IDENTIFICAÇÃO CONCLUÍDA")
print("="*40)
print(f"Erro Final (MSE): {erro_final:.6f}")
print("-" * 40)
print("Vetor de Parâmetros Identificado:")
print(f"c0 (u^2): {melhores_params[0]:.4f}")
print(f"c1 (u)  : {melhores_params[1]:.4f}")
print(f"c2 (bias): {melhores_params[2]:.4f}")
print(f"b1      : {melhores_params[3]:.4f}")
print(f"b2      : {melhores_params[4]:.4f}")
print(f"a1      : {melhores_params[5]:.4f}")
print(f"a2      : {melhores_params[6]:.4f}")
print("-" * 40)
print(f"Copie esta lista para o seu controlador:\n{list(melhores_params)}")
print("="*40)

# Gerar gráfico de validação
y_validacao = modelo_hammerstein(melhores_params, u_train)

plt.figure(figsize=(12, 8))

# Subplot 1: Entrada (PWM)
plt.subplot(2, 1, 1)
plt.plot(t_vec, u_train, 'g', label='Sinal de Excitação (PWM)')
plt.title(f"Dados de Entrada (Normalizados)")
plt.ylabel("Duty Cycle (0-1)")
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()

# Subplot 2: Saída (Real vs Modelo)
plt.subplot(2, 1, 2)
plt.plot(t_vec, y_real, 'k', alpha=0.7, linewidth=1.5, label='Dados Reais (Sensor)')
plt.plot(t_vec, y_validacao, 'r--', linewidth=2, label='Modelo Identificado (Hammerstein)')
plt.title(f"Validação do Modelo (MSE: {erro_final:.5f})")
plt.xlabel("Tempo (s)")
plt.ylabel("Altura da Bola (m)")
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)

plt.tight_layout()
plt.show()