import numpy as np
import csv
from scipy.signal import lfilter
from scipy.optimize import differential_evolution
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt


# LER DADOS DO CSV TRATADO


arquivo_csv = "identifier/dados.csv"

pwms = []
distancias = []

with open(arquivo_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pwm_val = int(row["pwm"])
        dist_val = float(row["distancia"])  # metros
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
    c0, c1, c2 = params[0:3]  # Não-linear
    b1 = params[3]
    a1, a2 = params[4:6]      # Linear IIR

    v = c0*(u_input**2) + c1*u_input + c2
    num = [0, b1]
    den = [1, a1, a2]
    y_est = lfilter(num, den, v)
    return y_est

def funcao_fitness(params):
    if abs(params[4]) > 2 or abs(params[5]) > 1.5:
        return 1e9
    y_est = modelo_hammerstein(params, u_train)
    return np.mean((y_train_noisy - y_est)**2)

bounds = [(-10, 10), (-10, 10), (-5, 5),
          (-5, 5), (-2, 2), (-1, 1)]

print("Rodando Evolução Diferencial (Differential Evolution)...\n")

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
print("Erro Final Hammerstein (MSE):", result.fun)
print("=================================================\n")

y_est_final = modelo_hammerstein(result.x, u_train)

# MODELO FÍSICO

rho = 1.225
g = 9.81
Cd = 0.47
rb = 0.02
m = 0.0027
kv = 5
A = np.pi * rb**2
V_max_fan = 12
ALTURA_MAX = 0.5

def pwm_to_va(D):
    V_fan = V_max_fan * D
    return V_fan * kv

def dynamics(t, x, D_atual):
    z, zdot = x
    va = pwm_to_va(D_atual)
    v_rel = va - zdot
    drag_force = (0.5 * Cd * rho * A * (v_rel**2)) * np.sign(v_rel)
    zddot = (drag_force / m) - g
    return [zdot, zddot]

estado_atual = [0.0, 0.0]
y_fisico = np.zeros(n_steps)

for k in range(n_steps - 1):
    sol = solve_ivp(dynamics, [0, Ts], estado_atual, args=(u_train[k],), method='RK45')
    estado_proximo = sol.y[:, -1]

    if estado_proximo[0] < 0:
        estado_proximo = [0, 0]

    elif estado_proximo[0] > ALTURA_MAX:
        estado_proximo = [ALTURA_MAX, 0]
    elif estado_proximo[0] > 0.9:
        estado_proximo = [0.9, 0]

    estado_atual = estado_proximo
    y_fisico[k+1] = estado_atual[0]


# CÁLCULO DOS ERROS DOS MODELOS

erro_fisico = np.mean((y_train_noisy - y_fisico)**2)
erro_hammerstein_vs_fisico = np.mean((y_est_final - y_fisico)**2)

print("\n================== AVALIAÇÃO ==================")
print(f"MSE Dados Reais vs Hammerstein : {result.fun:.6f}")
print(f"MSE Dados Reais vs Físico     : {erro_fisico:.6f}")
print(f"MSE Hammerstein vs Físico     : {erro_hammerstein_vs_fisico:.6f}")
print("================================================\n")


# PLOTAGEM COMPARATIVA


plt.figure(figsize=(12, 10))

# PWM
plt.subplot(3, 1, 1)
plt.plot(t_vec, u_train, 'g')
plt.ylabel("PWM (norm.)")
plt.title("Entrada PWM Real")
plt.grid(True)

# Comparação geral
plt.subplot(3, 1, 2)
plt.plot(t_vec, y_train_noisy, 'k', label="Dados Reais")
plt.plot(t_vec, y_est_final, 'r--', linewidth=2, label="Hammerstein")
plt.ylabel("Distância (m)")
plt.title("Comparação dos Modelos (Distância)")
plt.legend()
plt.grid(True)

# Diferença dos modelos
plt.subplot(3, 1, 3)
plt.plot(t_vec, y_train_noisy - y_est_final, 'r', label="Real - Hammerstein")
plt.plot(t_vec, y_train_noisy - y_fisico, 'b', label="Real - Físico")
plt.ylabel("Erro (m)")
plt.xlabel("Tempo (s)")
plt.title("Erros Comparativos (Distância)")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
