import numpy as np
import csv
from scipy.signal import lfilter
from scipy.optimize import differential_evolution
import matplotlib.pyplot as plt

# LER DADOS DO CSV TRATADO

arquivo_csv = "identifier/dados.csv"

pwms = []
distancias = []

with open(arquivo_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pwm_val = int(row["pwm"])
        dist_val = float(row["distancia"])  # já em metros 
        pwms.append(pwm_val)
        distancias.append(dist_val)

# Normaliza PWM (0-1)
u_train = np.array(pwms) / 255.0
y_train_noisy = np.array(distancias)

n_steps = len(u_train)
Ts = 0.05
t_vec = np.arange(n_steps) * Ts

print(f"\n➡ Total de amostras carregadas: {n_steps}")
print(f"➡ Exemplo PWM normalizado: {u_train[:5]}")
print(f"➡ Exemplo distâncias (m): {y_train_noisy[:5]}\n")

# MODELO HAMMERSTEIN PARA IDENTIFICAÇÃO

def modelo_hammerstein(params, u_input):
    c0, c1, c2 = params[0:3]  # NL
    b1 = params[3]
    a1, a2 = params[4:6]      # Linear IIR

    # Bloco NL
    v = c0*(u_input**2) + c1*u_input + c2

    # Bloco Linear
    num = [0, b1]
    den = [1, a1, a2]
    y_est = lfilter(num, den, v)
    return y_est

def funcao_fitness(params):
    if abs(params[4]) > 2 or abs(params[5]) > 1.5:
        return 1e9
    y_est = modelo_hammerstein(params, u_train)
    return np.mean((y_train_noisy - y_est)**2)

bounds = [(-10, 10), (-10, 10), (-5, 5), (-5, 5), (-2, 2), (-1, 1)]

print("Rodando Algoritmo Genético\n")

result = differential_evolution(
    funcao_fitness,
    bounds,
    strategy='best1bin',
    maxiter=80,
    popsize=25,
    mutation=(0.5, 1),
    recombination=0.7,
    disp=True
)

print("\n================== RESULTADOS ==================")
print("Melhores parâmetros encontrados:\n", result.x)
print("Erro Final (MSE):", result.fun)
print("=================================================\n")


# 3. VALIDAÇÃO DO MODELO IDENTIFICADO

y_est_final = modelo_hammerstein(result.x, u_train)

plt.figure(figsize=(12, 8))

# PWM
plt.subplot(2, 1, 1)
plt.plot(t_vec, u_train, 'g')
plt.ylabel("PWM (normalizado)")
plt.title("Entrada Real de PWM")
plt.grid(True)

# Dados reais vs modelo
plt.subplot(2, 1, 2)
plt.plot(t_vec, y_train_noisy, 'k', label="Dados Reais")
plt.plot(t_vec, y_est_final, 'r--', linewidth=2, label="Modelo Hammerstein")
plt.ylabel("Altura (m)")
plt.xlabel("Tempo (s)")
plt.title("Identificação Hammerstein com dados reais (CSV tratado)")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
