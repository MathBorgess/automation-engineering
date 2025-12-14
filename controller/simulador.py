import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation
import numpy as np
from controlador_fuzzy import ControladorFuzzy
from controlador_proporcional import ControladorProporcional
import serial
import serial.tools.list_ports
import threading
import time

class SimuladorExperimento:
    def __init__(self):
        # Configurações do experimento
        self.altura_tubo = 50  # cm
        self.largura_tubo = 6  # cm
        self.raio_bolinha = 2   # cm
        self.altura_grade = 0   # cm (altura da grade acima do fan)
        self.altura_sensor = 2  # cm (altura do sensor no topo)
        
        # Estado da bolinha (apenas para visualização)
        self.velocidade_fan = 0  # 0-100%
        self.altura_bolinha = self.altura_grade  # cm
        
        # Flag para evitar callback do slider quando atualizado programaticamente
        self.atualizando_slider_programaticamente = False
        
        # Controle de modos
        self.altura_desejada = 25  # Altura desejada: 25 cm
        self.modos_disponiveis = ["manual", "proporcional", "fuzzy"]
        self._indice_modo = 2  # iniciar em fuzzy
        self.modo_controle = self.modos_disponiveis[self._indice_modo]
        self.controlador_fuzzy = None
        self.controlador_proporcional = None
        self.distancia_sensor_lida = 0
        # Guardar última leitura válida para evitar zerar o controle por ruído
        self.ultima_distancia_valida = 0
        self.tempo_ultima_distancia = 0
        
        # Configuração de log
        self.caminho_log = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "log_experimento.csv"
        )
        self.ultimo_log = 0
        self.intervalo_log_seg = 0.2  # frequência de log (5 Hz)
        self._preparar_arquivo_log()
        
        # Comunicação Serial com Arduino
        self.arduino = None
        self.porta_serial = None
        self.distancia_arduino = 0
        self.thread_serial = None
        self.serial_ativo = False
        
        # Criar figura e eixos
        self.fig, self.ax = plt.subplots(figsize=(10, 9))
        self.fig.suptitle('Experimento com Controlador Fuzzy - Dados Reais', 
                         fontsize=14, fontweight='bold')
        
        # Configurar eixos
        self.ax.set_xlim(-30, 30)
        self.ax.set_ylim(-5, self.altura_tubo + 10)
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        
        # Criar slider para altura desejada
        ax_slider_altura = plt.axes([0.2, 0.06, 0.6, 0.03])
        self.slider_altura_desejada = Slider(ax_slider_altura, 'Altura Desejada (cm)', 5, 45, 
                                            valinit=self.altura_desejada, valstep=0.5)
        self.slider_altura_desejada.on_changed(self.atualizar_altura_desejada)
        
        # Criar slider para velocidade do fan (apenas para modo manual)
        ax_slider = plt.axes([0.2, 0.02, 0.6, 0.03])
        self.slider = Slider(ax_slider, 'Potência Fan (%)', 0, 100, 
                            valinit=0, valstep=1)
        self.slider.on_changed(self.atualizar_velocidade_fan)
        
        # Criar botão para alternar modo de controle
        ax_botao_fuzzy = plt.axes([0.85, 0.06, 0.12, 0.03])
        self.botao_controlador = Button(ax_botao_fuzzy, 'Modo: Fuzzy')
        self.botao_controlador.color = 'lightgreen'
        self.botao_controlador.on_clicked(self.ciclar_modo_controle)
        
        # Área para mostrar informações
        self.texto_altura = self.ax.text(0, self.altura_tubo + 5, 
                                         'Altura detectada: 0.0 cm\n'
                                         'Velocidade: 0.0 cm/s', 
                                         ha='center', fontsize=11, 
                                         bbox=dict(boxstyle='round', 
                                                 facecolor='yellow', 
                                                 alpha=0.7))
        
        # Desenhar componentes
        self.desenhar_tubo()
        self.desenhar_grade()
        self.desenhar_sensor()
        self.desenhar_bolinha()
        self.desenhar_fan()
        
        plt.subplots_adjust(bottom=0.18)  # Mais espaço para os dois sliders
        
        # Criar controladores
        self.controlador_fuzzy = ControladorFuzzy(
            altura_tubo=self.altura_tubo,
            altura_sensor=self.altura_sensor,
            altura_desejada=self.altura_desejada
        )
        self.controlador_proporcional = ControladorProporcional(
            altura_tubo=self.altura_tubo,
            altura_sensor=self.altura_sensor,
            altura_desejada=self.altura_desejada
        )
        self.definir_modo_controle(self.modo_controle)
        
        # Conectar ao Arduino automaticamente
        if self.conectar_arduino():
            print("Conectado ao Arduino. Iniciando leitura de dados reais...")
        else:
            print("ERRO: Não foi possível conectar ao Arduino!")
            print("Certifique-se de que o Arduino está conectado e o código está carregado.")
        
        # Iniciar animação para atualizar visualização
        self.animacao = FuncAnimation(self.fig, self.atualizar_visualizacao, 
                                     interval=50, blit=False)  # Atualizar a cada 50ms
    
    def conectar_arduino(self):
        """Conecta ao Arduino na porta específica identificada"""
        # Porta obtida da sua imagem
        porta_alvo = "/dev/cu.usbserial-1140"
        baud_rate = 9600  # Certifique-se que seu código .ino usa Serial.begin(9600)

        print(f"Tentando conectar em {porta_alvo}...")

        try:
            # Tenta conectar diretamente na porta conhecida
            # write_timeout garante que o write não trave indefinidamente
            self.arduino = serial.Serial(
                porta_alvo, 
                baud_rate, 
                timeout=1,
                write_timeout=1
            )
            
            # Limpar buffer de entrada antes de começar
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            # O Arduino Uno reinicia ao abrir a serial via USB, precisamos esperar
            time.sleep(2) 
            
            self.porta_serial = porta_alvo
            self.serial_ativo = True
            
            # Iniciar thread para ler dados do Arduino
            if self.thread_serial is None or not self.thread_serial.is_alive():
                self.thread_serial = threading.Thread(target=self.ler_serial, daemon=True)
                self.thread_serial.start()
            
            print(f"Conectado com sucesso ao Arduino na porta {porta_alvo}")
            return True

        except serial.SerialException as e:
            print(f"Não foi possível abrir a porta {porta_alvo}.")
            print(f"Verifique se o cabo está conectado e se o Arduino IDE não está com o Monitor Serial aberto.")
            return False
        except Exception as e:
            print(f"Erro genérico ao conectar: {e}")
            return False
    
    def desconectar_arduino(self):
        """Desconecta do Arduino"""
        self.serial_ativo = False
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
        self.arduino = None
        self.porta_serial = None
        print("Desconectado do Arduino")
    
    def ler_serial(self):
        """Thread para ler dados do Arduino continuamente"""
        while self.serial_ativo and self.arduino and self.arduino.is_open:
            try:
                if self.arduino.in_waiting > 0:
                    linha = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not linha:  # Ignorar linhas vazias
                        continue
                    
                    # Processar mensagem de distância
                    if linha.startswith("DIST:"):
                        try:
                            distancia_str = linha[5:].strip()
                            distancia = float(distancia_str)
                            # Aceitar a leitura do sensor dentro do range típico do ultrassônico
                            # Se filtrarmos demais (teto muito baixo), o controlador nunca recebe a medição
                            # e não ajusta a velocidade do fan. Mantemos apenas um limite alto de segurança.
                            if 0 < distancia <= 400:
                                self.distancia_arduino = distancia
                                self.ultima_distancia_valida = distancia
                                self.tempo_ultima_distancia = time.time()
                                # Não imprimir toda leitura para não poluir o console
                                # print(f"Distância sensor: {distancia:.1f} cm")
                            else:
                                # Distância fora do range esperado, ignorar
                                pass
                        except (ValueError, IndexError) as e:
                            # Ignorar erros de conversão
                            pass
                    elif linha == "ARDUINO_READY":
                        print("Arduino pronto!")
                    elif linha.startswith("RECEBIDO:"):
                        # Debug: comando recebido pelo Arduino (apenas em modo debug)
                        pass  # Comentado para reduzir ruído no console
                    elif linha.startswith("FAN aplicado:"):
                        # Confirmação de que o fan foi ajustado
                        print(f"[Arduino] {linha}")
                    elif linha.startswith("ERRO:") or linha.startswith("Comando não reconhecido:"):
                        # Erros do Arduino
                        print(f"[Arduino ERRO] {linha}")
            except UnicodeDecodeError:
                # Ignorar erros de decodificação ocasionais
                pass
            except Exception as e:
                if self.serial_ativo:
                    print(f"Erro ao ler Serial: {e}")
                break
            time.sleep(0.01)
    
    def enviar_velocidade_fan(self, velocidade):
        """Envia velocidade do fan para o Arduino"""
        if self.arduino and self.arduino.is_open:
            try:
                # Garantir que a velocidade está no range válido
                velocidade_int = int(np.clip(velocidade, 0, 100))
                comando = f"FAN:{velocidade_int}\n"
                self.arduino.write(comando.encode('utf-8'))
                self.arduino.flush()  # Garantir que o comando seja enviado imediatamente
                print(f"[Enviado] FAN:{velocidade_int}%")
            except Exception as e:
                print(f"Erro ao enviar comando para Arduino: {e}")
        else:
            print(f"[AVISO] Arduino não conectado. Não foi possível enviar FAN:{int(velocidade)}%")
    
    def ciclar_modo_controle(self, event):
        """Alterna entre Manual -> Proporcional -> Fuzzy."""
        self._indice_modo = (self._indice_modo + 1) % len(self.modos_disponiveis)
        novo_modo = self.modos_disponiveis[self._indice_modo]
        self.definir_modo_controle(novo_modo)

    def definir_modo_controle(self, modo):
        """Configura rótulo e cor do botão conforme o modo."""
        self.modo_controle = modo
        if modo == "fuzzy":
            self.botao_controlador.label.set_text("Modo: Fuzzy")
            self.botao_controlador.color = "lightgreen"
            print("Controlador Fuzzy ATIVADO")
        elif modo == "proporcional":
            self.botao_controlador.label.set_text("Modo: Proporcional")
            self.botao_controlador.color = "lightskyblue"
            print("Controlador Proporcional ATIVADO")
        else:
            self.botao_controlador.label.set_text("Modo: Manual")
            self.botao_controlador.color = "lightgray"
            print("Modo Manual (sem controlador)")

        self.fig.canvas.draw_idle()
    
    def atualizar_altura_desejada(self, valor):
        """Atualiza a altura desejada e recalcula o controlador fuzzy"""
        self.altura_desejada = valor
        
        # Atualizar controladores
        if self.controlador_fuzzy is not None:
            self.controlador_fuzzy.atualizar_altura_desejada(valor)
        if self.controlador_proporcional is not None:
            self.controlador_proporcional.atualizar_altura_desejada(valor)
        print(f"Altura desejada atualizada para: {valor:.1f} cm")
        
        # Atualizar visualização
        self.fig.canvas.draw_idle()
    
    def atualizar_visualizacao(self, frame=None):
        """Atualiza a visualização da bolinha e informações usando dados reais do Arduino"""
        # Usar dados do Arduino
        distancia_sensor_lida = self.distancia_arduino
        
        # Calcular altura da bolinha a partir da distância do sensor
        # Distância = (altura_tubo + altura_sensor) - (altura_bolinha + raio)
        # altura_bolinha = (altura_tubo + altura_sensor) - distancia - raio
        if distancia_sensor_lida > 0:
            altura_calculada = (self.altura_tubo + self.altura_sensor) - \
                              distancia_sensor_lida - self.raio_bolinha
            altura_calculada = max(self.altura_grade, 
                                 min(altura_calculada, 
                                     self.altura_tubo - self.altura_sensor - self.raio_bolinha))
            self.altura_bolinha = altura_calculada
        
        # Sempre atualizar distancia_sensor_lida com o valor do Arduino
        self.distancia_sensor_lida = distancia_sensor_lida
        
        # Usar controlador conforme o modo
        if distancia_sensor_lida <= 0:
            # Tentar usar última distância válida recente (para não travar por uma leitura 0)
            limite_stale = 0.8  # segundos
            if self.ultima_distancia_valida > 0 and (time.time() - self.tempo_ultima_distancia) < limite_stale:
                distancia_sensor_lida = self.ultima_distancia_valida
                print(f"[DEBUG] Usando distância válida recente: {distancia_sensor_lida:.2f} cm")
            else:
                print(f"[DEBUG] Distância lida inválida para controle: {distancia_sensor_lida:.2f} cm")
        
        if distancia_sensor_lida > 0:
            velocidade_controlador = None
            if self.modo_controle == "fuzzy" and self.controlador_fuzzy is not None:
                velocidade_controlador = self.controlador_fuzzy.calcular_velocidade(
                    distancia_sensor_lida
                )
                prefixo = "[Fuzzy]"
            elif self.modo_controle == "proporcional" and self.controlador_proporcional is not None:
                velocidade_controlador = self.controlador_proporcional.calcular_velocidade(
                    distancia_sensor_lida
                )
                prefixo = "[P]"

            if velocidade_controlador is not None:
                delta = abs(velocidade_controlador - self.velocidade_fan)
                # Log para depuração: saber se o controlador está sendo chamado
                print(f"{prefixo} Distância: {distancia_sensor_lida:.1f} cm -> Vcalc: {velocidade_controlador:.1f}%, atual: {self.velocidade_fan:.1f}% (Δ={delta:.2f})")
                if delta > 0.1:
                    self.velocidade_fan = velocidade_controlador
                    self.enviar_velocidade_fan(velocidade_controlador)
                    self.atualizando_slider_programaticamente = True
                    self.slider.set_val(velocidade_controlador)
                    self.atualizando_slider_programaticamente = False
        else:
            # Depurar por que o controlador não roda (ex.: sensor lendo 0)
            pass
        
        # Atualizar linha do laser usando o valor do Arduino
        altura_detectada = (self.altura_tubo + self.altura_sensor) - distancia_sensor_lida
        self.linha_laser.set_data([0, 0], 
                                  [self.altura_tubo + self.altura_sensor, 
                                   altura_detectada])
        
        # Atualizar posição visual da bolinha
        self.bolinha.center = (0, self.altura_bolinha)
        
        # Atualizar texto com informações
        if self.modo_controle == "fuzzy":
            modo_controle = "AUTOMÁTICO (Fuzzy)"
        elif self.modo_controle == "proporcional":
            modo_controle = "AUTOMÁTICO (Proporcional)"
        else:
            modo_controle = "MANUAL"
        
        self.texto_altura.set_text(
            f'Modo: {modo_controle} | DADOS REAIS\n'
            f'Distância sensor: {distancia_sensor_lida:.1f} cm\n'
            f'Altura bolinha: {self.altura_bolinha:.1f} cm\n'
            f'Altura desejada: {self.altura_desejada:.1f} cm\n'
            f'Potência fan: {self.velocidade_fan:.0f}%'
        )
        
        # Registrar log periódico
        self._registrar_log(distancia_sensor_lida)
        
        # Redesenhar
        self.fig.canvas.draw_idle()
    
    def desenhar_tubo(self):
        """Desenha o tubo transparente"""
        # Tubo (retângulo com borda)
        tubo = patches.Rectangle((-self.largura_tubo/2, 0), 
                                self.largura_tubo, 
                                self.altura_tubo,
                                linewidth=3, 
                                edgecolor='gray', 
                                facecolor='lightblue',
                                alpha=0.3)
        self.ax.add_patch(tubo)
        
        # Adicionar label
        self.ax.text(0, self.altura_tubo/2, 'TUBO', 
                    ha='center', va='center', 
                    fontsize=10, color='gray', 
                    rotation=90, alpha=0.5)
    
    def desenhar_grade(self):
        """Desenha a grade acima do fan"""
        # Grade (linhas horizontais)
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
        
        # Label da grade
        self.ax.text(-self.largura_tubo/2 - 5, self.altura_grade + 2.5, 
                    'GRADE', ha='right', va='center', 
                    fontsize=9, color='darkgray')
    
    def desenhar_fan(self):
        """Desenha o fan na parte inferior"""
        # Base do fan
        base_fan = patches.Circle((0, -2), 8, 
                                 linewidth=2, 
                                 edgecolor='black', 
                                 facecolor='lightgray',
                                 alpha=0.8)
        self.ax.add_patch(base_fan)
        
        # Pás do fan (simplificado)
        for i in range(4):
            angulo = i * 90
            x1 = 0
            y1 = -2
            x2 = 6 * np.cos(np.radians(angulo))
            y2 = -2 + 6 * np.sin(np.radians(angulo))
            self.ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2)
        
        # Label do fan
        self.ax.text(0, -2, 'FAN', ha='center', va='center', 
                    fontsize=9, fontweight='bold')
    
    def desenhar_sensor(self):
        """Desenha o sensor de distância a laser no topo"""
        # Sensor (retângulo pequeno)
        sensor = patches.Rectangle((-4, self.altura_tubo), 
                                  8, 
                                  self.altura_sensor,
                                  linewidth=2, 
                                  edgecolor='red', 
                                  facecolor='red',
                                  alpha=0.7)
        self.ax.add_patch(sensor)
        
        # Linha do laser (linha pontilhada)
        self.linha_laser, = self.ax.plot([0, 0], 
                                         [self.altura_tubo + self.altura_sensor, 
                                          self.altura_tubo],
                                         'r--', linewidth=1, alpha=0.5)
        
        # Label do sensor
        self.ax.text(0, self.altura_tubo + self.altura_sensor/2, 
                    'SENSOR\nLASER', ha='center', va='center', 
                    fontsize=8, color='white', fontweight='bold')
    
    def desenhar_bolinha(self):
        """Desenha a bolinha de isopor"""
        self.bolinha = patches.Circle((0, self.altura_bolinha), 
                                     self.raio_bolinha,
                                     linewidth=2, 
                                     edgecolor='black', 
                                     facecolor='white',
                                     alpha=0.9)
        self.ax.add_patch(self.bolinha)
        
        # Adicionar sombra para efeito 3D
        sombra = patches.Circle((0.5, self.altura_bolinha - 0.5), 
                               self.raio_bolinha,
                               linewidth=0, 
                               facecolor='gray',
                               alpha=0.3)
        self.ax.add_patch(sombra)
    
    def atualizar_velocidade_fan(self, valor):
        """Atualiza a velocidade do fan manualmente (apenas quando fuzzy está desativado)"""
        # Ignorar se estiver atualizando programaticamente (pelo fuzzy)
        if self.atualizando_slider_programaticamente:
            return
        
        # Se um controlador automático estiver ativo, ignorar mudanças manuais
        if self.modo_controle != "manual":
            self.slider.set_val(self.velocidade_fan)
            return
        
        # Modo manual - atualizar velocidade
        self.velocidade_fan = valor
        
        # Enviar comando para Arduino
        self.enviar_velocidade_fan(valor)
    
    def mostrar(self):
        """Mostra o simulador"""
        plt.show()
    
    def _preparar_arquivo_log(self):
        """Cria arquivo de log com cabeçalho, se não existir."""
        if not os.path.exists(self.caminho_log):
            with open(self.caminho_log, "w", encoding="utf-8") as f:
                f.write("timestamp_iso,distancia_cm,altura_bolinha_cm,altura_desejada_cm,velocidade_fan_pct,modo\n")
            print(f"[LOG] Criado: {self.caminho_log}")
        else:
            print(f"[LOG] Gravando em: {self.caminho_log}")
    
    def _registrar_log(self, distancia_sensor_lida):
        """Registra log periódico da execução."""
        agora = time.time()
        if (agora - self.ultimo_log) < self.intervalo_log_seg:
            return
        self.ultimo_log = agora
        
        try:
            linha = (
                f"{datetime.now().isoformat(timespec='milliseconds')},"
                f"{distancia_sensor_lida:.3f},"
                f"{self.altura_bolinha:.3f},"
                f"{self.altura_desejada:.3f},"
                f"{self.velocidade_fan:.3f},"
                f"{self.modo_controle}\n"
            )
            with open(self.caminho_log, "a", encoding="utf-8") as f:
                f.write(linha)
        except Exception as e:
            print(f"[LOG ERRO] Falha ao gravar log: {e}")
    
    def __del__(self):
        """Destrutor - desconectar Arduino ao fechar"""
        self.desconectar_arduino()

if __name__ == '__main__':
    simulador = SimuladorExperimento()
    simulador.mostrar()

