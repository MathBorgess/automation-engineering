import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class ControladorFuzzy:
    
    def __init__(self, altura_tubo=100, altura_sensor=2, altura_desejada=50):
        self.altura_tubo = altura_tubo
        self.altura_sensor = altura_sensor
        self.altura_desejada = altura_desejada
        
        self.raio_bolinha = 3
        self.distancia_desejada = (altura_tubo + altura_sensor) - \
                                  (altura_desejada + self.raio_bolinha)
        
        distancia_max = altura_tubo + altura_sensor
        self.distancia_sensor = ctrl.Antecedent(
            np.arange(0, distancia_max + 1, 0.5), 
            'distancia_sensor'
        )
        
        self.velocidade_fan = ctrl.Consequent(
            np.arange(0, 101, 1), 
            'velocidade_fan'
        )
        
        dist_desej = self.distancia_desejada
        dist_max = distancia_max
        
        self.distancia_sensor['muito_baixo'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [0, 0, max(dist_desej * 0.3, 5)]
        )
        
        self.distancia_sensor['baixo'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [0, dist_desej * 0.5, dist_desej * 0.9]
        )
        
        self.distancia_sensor['ideal'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [dist_desej * 0.7, dist_desej, dist_desej * 1.3]
        )
        
        self.distancia_sensor['alto'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [dist_desej * 1.1, dist_desej * 1.5, min(dist_desej * 2, dist_max * 0.8)]
        )
        
        self.distancia_sensor['muito_alto'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [max(dist_desej * 1.5, dist_max * 0.6), dist_max, dist_max]
        )
        
        self.velocidade_fan['muito_baixa'] = fuzz.trimf(
            self.velocidade_fan.universe, 
            [0, 0, 20]
        )
        self.velocidade_fan['baixa'] = fuzz.trimf(
            self.velocidade_fan.universe, 
            [0, 20, 40]
        )
        self.velocidade_fan['media'] = fuzz.trimf(
            self.velocidade_fan.universe, 
            [30, 50, 70]
        )
        self.velocidade_fan['alta'] = fuzz.trimf(
            self.velocidade_fan.universe, 
            [60, 80, 100]
        )
        self.velocidade_fan['muito_alta'] = fuzz.trimf(
            self.velocidade_fan.universe, 
            [80, 100, 100]
        )
        
        regra1 = ctrl.Rule(
            self.distancia_sensor['muito_baixo'],
            self.velocidade_fan['muito_baixa']
        )
        regra2 = ctrl.Rule(
            self.distancia_sensor['baixo'],
            self.velocidade_fan['baixa']
        )
        regra3 = ctrl.Rule(
            self.distancia_sensor['ideal'],
            self.velocidade_fan['media']
        )
        regra4 = ctrl.Rule(
            self.distancia_sensor['alto'],
            self.velocidade_fan['alta']
        )
        regra5 = ctrl.Rule(
            self.distancia_sensor['muito_alto'],
            self.velocidade_fan['muito_alta']
        )
        
        self.sistema_controle = ctrl.ControlSystem([
            regra1, regra2, regra3, regra4, regra5
        ])
        
        self.simulador = ctrl.ControlSystemSimulation(self.sistema_controle)
    
    def calcular_velocidade(self, distancia_sensor_lida):
        distancia_max = self.altura_tubo + self.altura_sensor
        distancia_sensor_lida = np.clip(distancia_sensor_lida, 0, distancia_max)
        
        self.simulador.input['distancia_sensor'] = distancia_sensor_lida
        
        try:
            self.simulador.compute()
            velocidade = self.simulador.output['velocidade_fan']
            
            velocidade = np.clip(velocidade, 0, 100)
            
            return float(velocidade)
        except Exception as e:
            print(f"Erro no controlador fuzzy: {e}")
            return 50.0
    
    def atualizar_altura_desejada(self, nova_altura_desejada):
        self.altura_desejada = nova_altura_desejada
        self.distancia_desejada = (self.altura_tubo + self.altura_sensor) - \
                                  (nova_altura_desejada + self.raio_bolinha)
        
        distancia_max = self.altura_tubo + self.altura_sensor
        dist_desej = self.distancia_desejada
        dist_max = distancia_max
        
        self.distancia_sensor['muito_baixo'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [0, 0, max(dist_desej * 0.3, 5)]
        )
        
        self.distancia_sensor['baixo'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [0, dist_desej * 0.5, dist_desej * 0.9]
        )
        
        self.distancia_sensor['ideal'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [dist_desej * 0.7, dist_desej, dist_desej * 1.3]
        )
        
        self.distancia_sensor['alto'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [dist_desej * 1.1, dist_desej * 1.5, min(dist_desej * 2, dist_max * 0.8)]
        )
        
        self.distancia_sensor['muito_alto'] = fuzz.trimf(
            self.distancia_sensor.universe, 
            [max(dist_desej * 1.5, dist_max * 0.6), dist_max, dist_max]
        )
    
    def visualizar_funcoes_pertinencia(self):
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        self.distancia_sensor.view(ax=ax1)
        ax1.set_title('Funções de Pertinência - Distância do Sensor')
        ax1.set_xlabel('Distância (cm)')
        ax1.set_ylabel('Pertinência')
        ax1.axvline(self.distancia_desejada, color='r', linestyle='--', 
                   label=f'Distância desejada: {self.distancia_desejada:.1f} cm')
        ax1.legend()
        
        self.velocidade_fan.view(ax=ax2)
        ax2.set_title('Funções de Pertinência - Velocidade do Fan')
        ax2.set_xlabel('Velocidade (%)')
        ax2.set_ylabel('Pertinência')
        
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    controlador = ControladorFuzzy(
        altura_tubo=100,
        altura_sensor=2,
        altura_desejada=50
    )
    
    print("Testando controlador fuzzy:")
    print(f"Distância desejada: {controlador.distancia_desejada:.1f} cm\n")
    
    distancias_teste = [20, 40, 50, 60, 80, 100]
    for dist in distancias_teste:
        velocidade = controlador.calcular_velocidade(dist)
        print(f"Distância sensor: {dist:.1f} cm -> Velocidade fan: {velocidade:.1f}%")
