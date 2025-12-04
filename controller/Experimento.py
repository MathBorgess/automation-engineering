import numpy as np
from simulador import SimuladorExperimento
from controlador_fuzzy import ControladorFuzzy

class SimuladorComControlador(SimuladorExperimento):
    
    def __init__(self, altura_desejada=50, usar_controlador=True):
        super().__init__()
        
        self.usar_controlador = usar_controlador
        self.altura_desejada = altura_desejada
        
        if usar_controlador:
            self.controlador = ControladorFuzzy(
                altura_tubo=self.altura_tubo,
                altura_sensor=self.altura_sensor,
                altura_desejada=altura_desejada
            )
            
            self.distancia_sensor_lida = 0
            
            self.fig.suptitle(
                f'Simulador com Controlador Fuzzy (Altura desejada: {altura_desejada} cm)', 
                fontsize=14, fontweight='bold'
            )
    
    def atualizar_visualizacao(self):
        vibracao_x = np.random.normal(0, self.ruido_vibracao_std)
        vibracao_y = np.random.normal(0, self.ruido_vibracao_std)
        
        self.bolinha.center = (vibracao_x, self.altura_bolinha + vibracao_y)
        
        distancia_real = (self.altura_tubo + self.altura_sensor) - \
                        (self.altura_bolinha + self.raio_bolinha)
        
        ruido_sensor = np.random.normal(0, self.ruido_sensor_std)
        distancia_sensor_lida = distancia_real + ruido_sensor
        
        distancia_sensor_lida = max(0, distancia_sensor_lida)
        
        self.distancia_sensor_lida = distancia_sensor_lida
        
        if self.usar_controlador:
            velocidade_controlador = self.controlador.calcular_velocidade(
                distancia_sensor_lida
            )
            self.velocidade_fan = velocidade_controlador
            self.slider.set_val(velocidade_controlador)
        
        altura_detectada = (self.altura_tubo + self.altura_sensor) - distancia_sensor_lida
        self.linha_laser.set_data([0, 0], 
                                  [self.altura_tubo + self.altura_sensor, 
                                   altura_detectada])
        
        modo = "AUTOMÁTICO (Fuzzy)" if self.usar_controlador else "MANUAL"
        self.texto_altura.set_text(
            f'Modo: {modo}\n'
            f'Sensor (com ruído): {distancia_sensor_lida:.1f} cm\n'
            f'Altura real bolinha: {self.altura_bolinha:.1f} cm\n'
            f'Altura desejada: {self.altura_desejada:.1f} cm\n'
            f'Velocidade: {self.velocidade_bolinha:.1f} cm/s\n'
            f'Velocidade fan: {self.velocidade_fan:.1f}%'
        )
        
        self.fig.canvas.draw_idle()


if __name__ == '__main__':
    print("Iniciando simulador com controlador fuzzy...")
    print("O controlador tentará manter a bolinha a 50 cm de altura.")
    print("\nPara usar controle manual, modifique o código para usar_controlador=False\n")
    
    simulador = SimuladorComControlador(
        altura_desejada=50,
        usar_controlador=True
    )
    
    simulador.mostrar()
