import numpy as np


class ControladorProporcional:
    """Controlador proporcional simples para o fan."""

    def __init__(
        self,
        altura_tubo=50,
        altura_sensor=2,
        altura_desejada=20,
        kp=2,
        offset_base=57,
        deadband_cm=1.0,
    ):
        self.altura_tubo = altura_tubo
        self.altura_sensor = altura_sensor
        self.altura_desejada = altura_desejada
        self.kp = kp
        self.offset_base = offset_base
        self.deadband_cm = deadband_cm
        self.raio_bolinha = 2
        self._atualizar_distancia_desejada()

    def _atualizar_distancia_desejada(self):
        self.distancia_desejada = (self.altura_tubo + self.altura_sensor) - (
            self.altura_desejada + self.raio_bolinha
        )

    def calcular_velocidade(self, distancia_sensor_lida):
        distancia_max = self.altura_tubo + self.altura_sensor
        distancia_sensor_lida = np.clip(distancia_sensor_lida, 0, distancia_max)

        erro = distancia_sensor_lida - self.distancia_desejada
        # Em erro muito pequeno, mantenha offset base (evita queda abrupta)
        if abs(erro) <= self.deadband_cm:
            return float(np.clip(self.offset_base, 0, 100))

        velocidade = self.offset_base + self.kp * erro
        velocidade = np.clip(velocidade, 0, 100)
        return float(velocidade)

    def atualizar_altura_desejada(self, nova_altura_desejada):
        self.altura_desejada = nova_altura_desejada
        self._atualizar_distancia_desejada()

