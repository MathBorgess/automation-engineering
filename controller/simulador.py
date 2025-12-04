import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import Slider
from matplotlib.animation import FuncAnimation
import numpy as np

class SimuladorExperimento:
    def __init__(self):
        # Configurações do experimento
        self.altura_tubo = 100  # cm
        self.largura_tubo = 20  # cm
        self.raio_bolinha = 3   # cm
        self.altura_grade = 5   # cm (altura da grade acima do fan)
        self.altura_sensor = 2  # cm (altura do sensor no topo)
        
        # Parâmetros físicos
        self.gravidade = 980  # cm/s²
        self.massa_bolinha = 0.5  # gramas (bolinha de isopor é leve)
        self.densidade_ar = 0.001225  # g/cm³ (aproximadamente)
        self.coeficiente_arrasto = 0.47  # Esfera (bolinha)
        self.area_bolinha = np.pi * self.raio_bolinha ** 2  # cm²
        self.forca_fan_maxima = 5000  # dyn (força máxima do fan em dyn)
        self.decay_vento = 0.02  # Fator de decaimento do vento com altura
        
        # Parâmetros de ruído para simulação realista
        self.ruido_sensor_std = 2  # Desvio padrão do ruído do sensor (cm)
        self.turbulencia_vento_std = 0.5  # Desvio padrão da turbulência do vento (fração)
        self.perturbacao_forca_std = 50  # Desvio padrão de perturbações aleatórias na força (dyn)
        self.ruido_vibracao_std = 0.05  # Desvio padrão de vibrações do sistema (cm)
        
        # Estado físico da bolinha
        self.velocidade_fan = 0  # 0-100%
        self.altura_bolinha = self.altura_grade  # cm
        self.velocidade_bolinha = 0  # cm/s
        self.dt = 0.01  # Intervalo de tempo para simulação (s)
        
        # Flag para controlar animação
        self.animacao_ativa = False
        
        # Criar figura e eixos
        self.fig, self.ax = plt.subplots(figsize=(10, 9))
        self.fig.suptitle('Simulador de experimento', 
                         fontsize=14, fontweight='bold')
        
        self.ax.set_xlim(-30, 30)
        self.ax.set_ylim(-5, self.altura_tubo + 10)
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        
        ax_slider = plt.axes([0.2, 0.02, 0.6, 0.03])
        self.slider = Slider(ax_slider, 'Velocidade Fan (%)', 0, 100, 
                            valinit=0, valstep=1)
        self.slider.on_changed(self.atualizar_velocidade_fan)
        
        self.texto_altura = self.ax.text(0, self.altura_tubo + 5, 
                                         'Altura detectada: 0.0 cm\n'
                                         'Velocidade: 0.0 cm/s', 
                                         ha='center', fontsize=11, 
                                         bbox=dict(boxstyle='round', 
                                                 facecolor='yellow', 
                                                 alpha=0.7))
        
        self.desenhar_tubo()
        self.desenhar_grade()
        self.desenhar_sensor()
        self.desenhar_bolinha()
        self.desenhar_fan()
        
        plt.subplots_adjust(bottom=0.1)
        
        self.animacao = FuncAnimation(self.fig, self.atualizar_fisica, 
                                     interval=10, blit=False)
    
    def calcular_forca_vento(self, altura):
        if self.velocidade_fan == 0:
            return 0
        
        v_norm = self.velocidade_fan / 100.0
        
        forca_max = self.forca_fan_maxima * (v_norm ** 2)
        
        altura_relativa = altura - self.altura_grade
        fator_decay = np.exp(-self.decay_vento * altura_relativa)
        
        turbulencia = 1.0 + np.random.normal(0, self.turbulencia_vento_std)
        turbulencia = np.clip(turbulencia, 0.5, 1.5)
        
        return forca_max * fator_decay * turbulencia
    
    def calcular_resistencia_ar(self, velocidade):
        if abs(velocidade) < 0.1:
            return 0
        
        forca_ar = 0.5 * self.densidade_ar * self.coeficiente_arrasto * \
                   self.area_bolinha * (velocidade ** 2)
        
        return -np.sign(velocidade) * forca_ar
    
    def calcular_forcas(self):
        forca_gravidade = -self.massa_bolinha * self.gravidade
        
        forca_vento = self.calcular_forca_vento(self.altura_bolinha)
        
        forca_ar = self.calcular_resistencia_ar(self.velocidade_bolinha)
        
        perturbacao = np.random.normal(0, self.perturbacao_forca_std)
        
        forca_resultante = forca_gravidade + forca_vento + forca_ar + perturbacao
        
        return forca_resultante
    
    def atualizar_fisica(self, frame):
        forca = self.calcular_forcas()
        
        aceleracao = forca / self.massa_bolinha
        
        self.velocidade_bolinha += aceleracao * self.dt
        
        nova_altura = self.altura_bolinha + self.velocidade_bolinha * self.dt
        
        altura_minima = self.altura_grade
        altura_maxima = self.altura_tubo - self.altura_sensor - self.raio_bolinha - 1
        
        if nova_altura < altura_minima:
            nova_altura = altura_minima
            self.velocidade_bolinha *= -0.3
            if abs(self.velocidade_bolinha) < 1:
                self.velocidade_bolinha = 0
        
        if nova_altura > altura_maxima:
            nova_altura = altura_maxima
            self.velocidade_bolinha *= -0.3
            if abs(self.velocidade_bolinha) < 1:
                self.velocidade_bolinha = 0
        
        self.altura_bolinha = nova_altura
        
        self.atualizar_visualizacao()
    
    def atualizar_visualizacao(self):
        vibracao_x = np.random.normal(0, self.ruido_vibracao_std)
        vibracao_y = np.random.normal(0, self.ruido_vibracao_std)
        
        self.bolinha.center = (vibracao_x, self.altura_bolinha + vibracao_y)
        
        distancia_real = (self.altura_tubo + self.altura_sensor) - \
                        (self.altura_bolinha + self.raio_bolinha)
        
        ruido_sensor = np.random.normal(0, self.ruido_sensor_std)
        distancia_sensor_lida = distancia_real + ruido_sensor
        
        distancia_sensor_lida = max(0, distancia_sensor_lida)
        
        altura_detectada = (self.altura_tubo + self.altura_sensor) - distancia_sensor_lida
        self.linha_laser.set_data([0, 0], 
                                  [self.altura_tubo + self.altura_sensor, 
                                   altura_detectada])
        
        self.texto_altura.set_text(
            f'Sensor (com ruído): {distancia_sensor_lida:.1f} cm\n'
            f'Altura real bolinha: {self.altura_bolinha:.1f} cm\n'
            f'Velocidade: {self.velocidade_bolinha:.1f} cm/s\n'
            f'Velocidade fan: {self.velocidade_fan:.0f}%'
        )
        
        self.fig.canvas.draw_idle()
    
    def desenhar_tubo(self):
        tubo = patches.Rectangle((-self.largura_tubo/2, 0), 
                                self.largura_tubo, 
                                self.altura_tubo,
                                linewidth=3, 
                                edgecolor='gray', 
                                facecolor='lightblue',
                                alpha=0.3)
        self.ax.add_patch(tubo)
        
        self.ax.text(0, self.altura_tubo/2, 'TUBO', 
                    ha='center', va='center', 
                    fontsize=10, color='gray', 
                    rotation=90, alpha=0.5)
    
    def desenhar_grade(self):
        for i in range(5):
            y = self.altura_grade + i * 0.5
            linha = patches.Rectangle((-self.largura_tubo/2 + 2, y), 
                                     self.largura_tubo - 4, 
                                     0.2,
                                     linewidth=1, 
                                     edgecolor='darkgray', 
                                     facecolor='darkgray',
                                     alpha=0.6)
            self.ax.add_patch(linha)
        
        self.ax.text(-self.largura_tubo/2 - 5, self.altura_grade + 2.5, 
                    'GRADE', ha='right', va='center', 
                    fontsize=9, color='darkgray')
    
    def desenhar_fan(self):
        base_fan = patches.Circle((0, -2), 8, 
                                 linewidth=2, 
                                 edgecolor='black', 
                                 facecolor='lightgray',
                                 alpha=0.8)
        self.ax.add_patch(base_fan)
        
        for i in range(4):
            angulo = i * 90
            x1 = 0
            y1 = -2
            x2 = 6 * np.cos(np.radians(angulo))
            y2 = -2 + 6 * np.sin(np.radians(angulo))
            self.ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2)
        
        self.ax.text(0, -2, 'FAN', ha='center', va='center', 
                    fontsize=9, fontweight='bold')
    
    def desenhar_sensor(self):
        sensor = patches.Rectangle((-4, self.altura_tubo), 
                                  8, 
                                  self.altura_sensor,
                                  linewidth=2, 
                                  edgecolor='red', 
                                  facecolor='red',
                                  alpha=0.7)
        self.ax.add_patch(sensor)
        
        self.linha_laser, = self.ax.plot([0, 0], 
                                         [self.altura_tubo + self.altura_sensor, 
                                          self.altura_tubo],
                                         'r--', linewidth=1, alpha=0.5)
        
        self.ax.text(0, self.altura_tubo + self.altura_sensor/2, 
                    'SENSOR\nLASER', ha='center', va='center', 
                    fontsize=8, color='white', fontweight='bold')
    
    def desenhar_bolinha(self):
        self.bolinha = patches.Circle((0, self.altura_bolinha), 
                                     self.raio_bolinha,
                                     linewidth=2, 
                                     edgecolor='black', 
                                     facecolor='white',
                                     alpha=0.9)
        self.ax.add_patch(self.bolinha)
        
        sombra = patches.Circle((0.5, self.altura_bolinha - 0.5), 
                               self.raio_bolinha,
                               linewidth=0, 
                               facecolor='gray',
                               alpha=0.3)
        self.ax.add_patch(sombra)
    
    def atualizar_velocidade_fan(self, valor):
        self.velocidade_fan = valor
    
    def mostrar(self):
        plt.show()

if __name__ == '__main__':
    simulador = SimuladorExperimento()
    simulador.mostrar()

