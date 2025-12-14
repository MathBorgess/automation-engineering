import re
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class ControladorFuzzy:
    """
    Controlador fuzzy para controlar a velocidade do fan baseado apenas
    na leitura do sensor laser.
    
    O controlador recebe a distância detectada pelo sensor e retorna
    a velocidade do fan (0-100%) para manter a bolinha em uma altura desejada.
    """
    
    def __init__(self, altura_tubo=50, altura_sensor=2, altura_desejada=10,
                 offset_velocidade=0.0, ganho_proporcional=0.3, velocidade_minima=41.0):
        """
        Inicializa o controlador fuzzy.
        
        Parâmetros:
        -----------
        altura_tubo : float
            Altura total do tubo em cm
        altura_sensor : float
            Altura do sensor no topo em cm
        altura_desejada : float
            Altura desejada da bolinha em cm (altura alvo)
        offset_velocidade : float
            Offset aplicado na saída da velocidade (%)
        ganho_proporcional : float
            Ganho do termo proporcional para reduzir erro estacionário
        velocidade_minima : float
            Velocidade mínima do fan (%). Abaixo disso, o fan desliga (0%)
        """
        self.altura_tubo = altura_tubo
        self.altura_sensor = altura_sensor
        self.altura_desejada = altura_desejada
        self.offset_velocidade = float(offset_velocidade)
        self.ganho_proporcional = float(ganho_proporcional)
        self.velocidade_minima = float(velocidade_minima)
        
        # Baseado nos dados reais, a relação é: altura_bolinha = 50 - distancia
        # Distância desejada = 50 - altura_desejada
        self.distancia_desejada = 50.0 - altura_desejada
        
        # Mapa de correção altura->velocidade baseado em dados reais
        self.mapa_correcao_altura_vel = None
        self.usar_correcao_lookup = False
        
        # Variável para armazenar a última velocidade (filtro de suavização)
        self.ultima_velocidade = None
        self.alpha_filtro = 0.3  # Fator de suavização (0 = sem filtro, 1 = sem suavização)
        
        # Definir universo de discurso
        # Distância do sensor: 0 a altura máxima do tubo
        distancia_max = altura_tubo + altura_sensor
        self.distancia_sensor = ctrl.Antecedent(
            np.arange(0, distancia_max + 1, 0.5), 
            'distancia_sensor'
        )
        
        # Velocidade do fan: 0 a 100%
        # Nota: O universo inclui 0%, mas as funções de pertinência começam em velocidade_minima
        self.velocidade_fan = ctrl.Consequent(
            np.arange(0, 101, 1), 
            'velocidade_fan'
        )
        
        # Definir funções de pertinência para a distância do sensor
        # A distância é medida do sensor no topo até a bolinha
        # Se a distância é grande, a bolinha está baixa (precisa mais vento)
        # Se a distância é pequena, a bolinha está alta (precisa menos vento)
        self._redefinir_funcoes_distancia()
        
        # Funções de pertinência para velocidade do fan
        # Ajuste das saídas para refletir o perfil que funcionou no proporcional
        # Base próxima de 55-60% quando na região ideal.
        self._redefinir_funcoes_velocidade()
        
        # Definir regras fuzzy
        self._recriar_regras_e_sistema()
    
    def _converter_distancia_cm(self, valores):
        """
        Converte uma lista/array de distâncias para centímetros.
        Se os dados já estiverem em centímetros (ex.: valor máximo > 5),
        nada é alterado; caso contrário, assume-se que estão em metros.
        """
        arr = np.asarray(valores, dtype=float)
        if arr.size == 0:
            raise ValueError("Lista de distâncias vazia para calibração.")
        if np.nanmax(arr) < 5:  # valores provindos do csv estão em metros (~0.4)
            return arr * 100.0
        return arr

    def _redefinir_funcoes_distancia(self, limites=None):
        """
        Atualiza as funções de pertinência da distância.
        Quando limites é None, usa o perfil original; caso contrário,
        utiliza quantis calculados a partir dos dados coletados.
        """
        dist_max = self.altura_tubo + self.altura_sensor
        dist_desej = self.distancia_desejada

        if limites:
            # Garantir monotonicidade e limite superior
            q10 = float(limites.get('muito_baixo_max', dist_desej * 0.3))
            q25 = float(limites.get('baixo_medio', dist_desej * 0.5))
            q50 = float(limites.get('ideal_medio', dist_desej))
            q75 = float(limites.get('ideal_max', dist_desej * 1.2))
            q90 = float(limites.get('alto_max', dist_desej * 1.4))
            dist_max = max(dist_max, float(limites.get('dist_max_dados', dist_max)))

            # Muito baixo / baixo
            self.distancia_sensor['muito_baixo'] = fuzz.trimf(
                self.distancia_sensor.universe,
                [0, 0, min(q10, dist_max)]
            )
            self.distancia_sensor['baixo'] = fuzz.trimf(
                self.distancia_sensor.universe,
                [0, q25, q50]
            )

            # Ideal
            self.distancia_sensor['ideal'] = fuzz.trimf(
                self.distancia_sensor.universe,
                [q25, q50, q75]
            )

            # Alto / muito alto
            alto_medio = float(limites.get('alto_medio', (q75 + q90) / 2))
            self.distancia_sensor['alto'] = fuzz.trimf(
                self.distancia_sensor.universe,
                [q50, alto_medio, q90]
            )

            muito_alto_min = float(limites.get('muito_alto_min', q75))
            self.distancia_sensor['muito_alto'] = fuzz.trimf(
                self.distancia_sensor.universe,
                [muito_alto_min, dist_max, dist_max]
            )
            return

        # Perfil original (sem calibração por dados)
        # Baseado na análise dos dados reais
        dist_desej = self.distancia_desejada
        dist_max = self.altura_tubo + self.altura_sensor

        # Funções de pertinência ajustadas para maior precisão
        # Muito baixo: distância muito pequena (bolinha muito alta)
        # Corresponde a distâncias menores que dist_desej - 5cm
        muito_baixo_max = max(dist_desej - 5, 5)
        self.distancia_sensor['muito_baixo'] = fuzz.trimf(
            self.distancia_sensor.universe,
            [0, 0, muito_baixo_max]
        )

        # Baixo: distância pequena (bolinha alta)
        # Corresponde a distâncias entre dist_desej - 5 e dist_desej - 1
        baixo_min = max(dist_desej - 6, 0)
        baixo_medio = max(dist_desej - 3, 3)
        baixo_max = max(dist_desej - 0.5, 5)
        self.distancia_sensor['baixo'] = fuzz.trimf(
            self.distancia_sensor.universe,
            [baixo_min, baixo_medio, baixo_max]
        )

        # Ideal: distância próxima da desejada (dentro de ±2cm)
        ideal_min = max(dist_desej - 2, 0)
        ideal_medio = dist_desej
        ideal_max = min(dist_desej + 2, dist_max)
        self.distancia_sensor['ideal'] = fuzz.trimf(
            self.distancia_sensor.universe,
            [ideal_min, ideal_medio, ideal_max]
        )

        # Alto: distância grande (bolinha baixa)
        # Corresponde a distâncias entre dist_desej + 1 e dist_desej + 5
        alto_min = max(dist_desej + 0.5, 0)
        alto_medio = min(dist_desej + 3, dist_max - 5)
        alto_max = min(dist_desej + 6, dist_max - 2)
        # Garantir ordenação
        alto_medio = max(alto_min + 0.5, alto_medio)
        alto_max = max(alto_medio + 0.5, alto_max)
        self.distancia_sensor['alto'] = fuzz.trimf(
            self.distancia_sensor.universe,
            [alto_min, alto_medio, alto_max]
        )

        # Muito alto: distância muito grande (bolinha muito baixa)
        # Corresponde a distâncias maiores que dist_desej + 5cm
        muito_alto_min = min(dist_desej + 5, dist_max - 5)
        muito_alto_min = max(muito_alto_min, alto_medio)
        self.distancia_sensor['muito_alto'] = fuzz.trimf(
            self.distancia_sensor.universe,
            [muito_alto_min, dist_max, dist_max]
        )

    def _recriar_regras_e_sistema(self):
        """Cria/recria regras e simulador após ajuste das funções de pertinência."""
        regra1 = ctrl.Rule(
            self.distancia_sensor['muito_baixo'],  # Distância pequena = bolinha alta
            self.velocidade_fan['muito_baixa']      # Diminuir fan
        )
        regra2 = ctrl.Rule(
            self.distancia_sensor['baixo'],  # Distância pequena = bolinha alta
            self.velocidade_fan['baixa']     # Diminuir fan
        )
        regra3 = ctrl.Rule(
            self.distancia_sensor['ideal'],  # Distância ideal
            self.velocidade_fan['media']     # Manter velocidade média
        )
        regra4 = ctrl.Rule(
            self.distancia_sensor['alto'],  # Distância grande = bolinha baixa
            self.velocidade_fan['alta']     # Aumentar fan
        )
        regra5 = ctrl.Rule(
            self.distancia_sensor['muito_alto'],  # Distância muito grande = bolinha muito baixa
            self.velocidade_fan['muito_alta']     # Aumentar muito o fan
        )

        # Criar sistema de controle
        self.sistema_controle = ctrl.ControlSystem([
            regra1, regra2, regra3, regra4, regra5
        ])

        # Criar simulador
        self.simulador = ctrl.ControlSystemSimulation(self.sistema_controle)

    def calcular_velocidade(self, distancia_sensor_lida):
        """
        Calcula a velocidade do fan baseada na leitura do sensor.
        
        Parâmetros:
        -----------
        distancia_sensor_lida : float
            Distância detectada pelo sensor em cm (do sensor até a bolinha)
        
        Retorna:
        --------
        float
            Velocidade do fan em porcentagem (0-100)
        """
        # Garantir que a distância está dentro dos limites
        distancia_max = self.altura_tubo + self.altura_sensor
        distancia_sensor_lida = np.clip(distancia_sensor_lida, 0, distancia_max)
        
        # Se usar correção por lookup, interpolar valores da tabela
        if self.usar_correcao_lookup and self.mapa_correcao_altura_vel:
            velocidade_base = self._interpolar_velocidade_lookup(self.distancia_desejada)
            
            # Calcular erro (distância real - distância desejada)
            erro = distancia_sensor_lida - self.distancia_desejada
            
            # Aplicar ajuste proporcional baseado no erro
            ajuste_proporcional = self.ganho_proporcional * erro
            
            # Velocidade final
            velocidade = np.clip(velocidade_base + ajuste_proporcional + self.offset_velocidade, 0, 100)
            
            # Aplicar filtro de suavização para reduzir oscilações
            if self.ultima_velocidade is not None:
                velocidade = self.alpha_filtro * velocidade + (1 - self.alpha_filtro) * self.ultima_velocidade
            
            self.ultima_velocidade = velocidade
            
            # Garantir que a velocidade nunca seja menor que o mínimo
            # O fan sempre opera em >= velocidade_minima
            velocidade = max(velocidade, self.velocidade_minima)
            
            return float(velocidade)
        
        # Modo fuzzy tradicional
        # Calcular erro (distância real - distância desejada)
        erro = distancia_sensor_lida - self.distancia_desejada
        
        # Definir entrada do sistema fuzzy
        self.simulador.input['distancia_sensor'] = distancia_sensor_lida
        
        # Computar saída
        try:
            self.simulador.compute()
            velocidade = self.simulador.output['velocidade_fan']

            # Adicionar componente proporcional para reduzir erro estacionário
            # Se erro > 0: distância maior que desejada (bolinha muito baixa) -> aumentar velocidade
            # Se erro < 0: distância menor que desejada (bolinha muito alta) -> diminuir velocidade
            ajuste_proporcional = self.ganho_proporcional * erro
            
            # Aplica ajuste proporcional, offset fixo e garante range 0-100
            velocidade = np.clip(velocidade + ajuste_proporcional + self.offset_velocidade, 0, 100)
            
            # Aplicar filtro de suavização para reduzir oscilações
            if self.ultima_velocidade is not None:
                velocidade = self.alpha_filtro * velocidade + (1 - self.alpha_filtro) * self.ultima_velocidade
            
            self.ultima_velocidade = velocidade
            
            # Garantir que a velocidade nunca seja menor que o mínimo
            # O fan sempre opera em >= velocidade_minima
            velocidade = max(velocidade, self.velocidade_minima)
            
            return float(velocidade)
        except Exception as e:
            # Em caso de erro, retornar velocidade média
            print(f"Erro no controlador fuzzy: {e}")
            return 60.0
    
    def _interpolar_velocidade_lookup(self, distancia_desejada):
        """
        Interpola a velocidade baseada na tabela de lookup.
        
        Parâmetros:
        -----------
        distancia_desejada : float
            Distância desejada em cm
            
        Retorna:
        --------
        float
            Velocidade interpolada em %
        """
        if not self.mapa_correcao_altura_vel:
            return 60.0
        
        distancias = np.array(sorted(self.mapa_correcao_altura_vel.keys()))
        velocidades = np.array([self.mapa_correcao_altura_vel[d] for d in distancias])
        
        # Interpolar linearmente
        velocidade = np.interp(distancia_desejada, distancias, velocidades)
        return float(velocidade)
    
    def atualizar_altura_desejada(self, nova_altura_desejada):
        """
        Atualiza a altura desejada da bolinha e recalcula as funções de pertinência.
        
        Parâmetros:
        -----------
        nova_altura_desejada : float
            Nova altura desejada em cm
        """
        self.altura_desejada = nova_altura_desejada
        # Baseado nos dados reais: altura = 50 - distancia
        self.distancia_desejada = 50.0 - nova_altura_desejada
        
        # Recalcular funções de pertinência para distância
        self._redefinir_funcoes_distancia()

        # Recriar as regras e o sistema de controle com as novas funções de pertinência
        self._recriar_regras_e_sistema()
    
    def calibrar_multiplas_alturas(self, caminho_csv, usar_lookup=True):
        """
        Calibra o controlador analisando dados de múltiplas alturas.
        Cria um mapeamento otimizado baseado em todas as alturas testadas.
        
        Parâmetros:
        -----------
        caminho_csv : str
            Caminho para o arquivo CSV com os dados de múltiplas alturas
        usar_lookup : bool
            Se True, usa tabela de lookup para correção baseada em dados reais
        """
        # Ler CSV pulando linhas vazias e inválidas
        # Formato: timestamp_iso,distancia_cm,altura_bolinha_cm,altura_desejada_cm,velocidade_fan_pct,modo
        dados_list = []
        with open(caminho_csv, 'r') as f:
            next(f)  # Pular cabeçalho
            for linha in f:
                linha = linha.strip()
                if not linha or linha.count(',') < 4:
                    continue
                try:
                    partes = linha.split(',')
                    if len(partes) >= 5:
                        # Colunas: 1=distancia, 2=altura_bolinha, 3=altura_desejada, 4=velocidade
                        distancia = float(partes[1])
                        altura_bol = float(partes[2])
                        altura_des = float(partes[3])
                        velocidade = float(partes[4])
                        
                        if altura_des > 0 and distancia > 0:
                            dados_list.append([distancia, altura_bol, altura_des, velocidade])
                except:
                    continue
        
        if not dados_list:
            print("Aviso: Nenhum dado válido encontrado no CSV")
            return
            
        dados = np.array(dados_list)
        
        distancias = dados[:, 0]
        alturas_bolinha = dados[:, 1]
        alturas_desejadas = dados[:, 2]
        velocidades = dados[:, 3]
        
        print("\n" + "="*70)
        print("CALIBRAÇÃO COM MÚLTIPLAS ALTURAS")
        print("="*70)
        
        # Analisar cada altura
        mapa_altura_dist = {}
        mapa_altura_vel = {}
        mapa_dist_vel = {}  # Mapa distância -> velocidade ótima
        
        for altura in np.unique(alturas_desejadas):
            mask = alturas_desejadas == altura
            if np.sum(mask) < 10:  # Ignorar alturas com poucos dados
                continue
                
            dist_altura = distancias[mask]
            vel_altura = velocidades[mask]
            alt_real = alturas_bolinha[mask]
            
            dist_mediana = np.median(dist_altura)
            vel_mediana = np.median(vel_altura)
            alt_real_mediana = np.median(alt_real)
            erro_medio = abs(alt_real_mediana - altura)
            
            # Calcular velocidade ideal que deveria ter sido usada
            # Se altura real > altura desejada: bolinha alta demais, precisa menos velocidade
            # Se altura real < altura desejada: bolinha baixa demais, precisa mais velocidade
            # Usar correção mais agressiva para reduzir erro
            correcao = (altura - alt_real_mediana) * 1.0  # 1.0% por cm de erro
            vel_ideal = np.clip(vel_mediana + correcao, 30, 95)
            
            mapa_altura_dist[altura] = dist_mediana
            mapa_altura_vel[altura] = vel_ideal
            # Distância desejada para essa altura
            dist_desejada = 50.0 - altura
            mapa_dist_vel[dist_desejada] = vel_ideal
            
            print(f"\nAltura {altura:2.0f}cm:")
            print(f"  Distância mediana observada: {dist_mediana:5.1f} cm")
            print(f"  Distância ideal calculada: {dist_desejada:5.1f} cm")
            print(f"  Velocidade mediana: {vel_mediana:5.1f}%")
            print(f"  Velocidade corrigida: {vel_ideal:5.1f}%")
            print(f"  Altura real: {alt_real_mediana:5.1f} cm (erro: {erro_medio:4.1f} cm)")
        
        # Salvar mapa de correção
        if usar_lookup and len(mapa_dist_vel) > 0:
            self.mapa_correcao_altura_vel = mapa_dist_vel
            self.usar_correcao_lookup = True
        
        # Calcular parâmetros globais
        todas_dist = np.array(list(mapa_altura_dist.values()))
        todas_vel = np.array(list(mapa_altura_vel.values()))
        
        # Ajustar ganho proporcional baseado no erro observado
        erros = []
        for altura in mapa_altura_dist.keys():
            mask = alturas_desejadas == altura
            alt_real = np.median(alturas_bolinha[mask])
            erros.append(abs(alt_real - altura))
        
        erro_medio_geral = np.mean(erros)
        # Aumentar ganho proporcional se erro for grande
        # Ajuste mais agressivo para erros maiores
        if erro_medio_geral > 2.0:
            self.ganho_proporcional = min(0.8, 0.4 + (erro_medio_geral - 2.0) * 0.2)
        else:
            self.ganho_proporcional = 0.3
        
        print(f"\n{'='*70}")
        print(f"AJUSTES APLICADOS:")
        print(f"  Ganho proporcional: {self.ganho_proporcional:.3f}")
        print(f"  Erro médio geral: {erro_medio_geral:.2f} cm")
        print(f"  Usar correção por lookup: {self.usar_correcao_lookup}")
        print(f"{'='*70}\n")
        
        # Usar dados globais para definir funções de pertinência
        self.calibrar_com_dados_csv(caminho_csv)

    def calibrar_com_dados_csv(self, caminho_csv, altura_alvo=None):
        """
        Ajusta automaticamente o controlador usando o histórico em CSV.
        - Analisa os dados para cada altura desejada
        - Ajusta as funções de pertinência baseadas em dados reais
        - Calcula ganhos otimizados
        
        Parâmetros:
        -----------
        caminho_csv : str
            Caminho para o arquivo CSV com os dados
        altura_alvo : float, opcional
            Se fornecido, calibra apenas para essa altura específica
        """
        # Ler CSV pulando linhas vazias e inválidas
        dados_list = []
        with open(caminho_csv, 'r') as f:
            next(f)  # Pular cabeçalho
            for linha in f:
                linha = linha.strip()
                if not linha or linha.count(',') < 4:
                    continue
                try:
                    partes = linha.split(',')
                    if len(partes) >= 5:
                        # Colunas: 1=distancia, 2=altura_bolinha, 3=altura_desejada, 4=velocidade
                        distancia = float(partes[1])
                        altura_bol = float(partes[2])
                        altura_des = float(partes[3])
                        velocidade = float(partes[4])
                        
                        if altura_des > 0 and distancia > 0:
                            dados_list.append([distancia, altura_bol, altura_des, velocidade])
                except:
                    continue
        
        if not dados_list:
            print("Aviso: Nenhum dado válido encontrado no CSV")
            return
            
        dados = np.array(dados_list)
        
        # Colunas: distancia_cm, altura_bolinha_cm, altura_desejada_cm, velocidade_fan_pct
        distancias = dados[:, 0]
        alturas_bolinha = dados[:, 1]
        alturas_desejadas = dados[:, 2]
        velocidades = dados[:, 3]
        
        # Se altura_alvo fornecida, filtrar dados
        if altura_alvo is not None:
            mask = alturas_desejadas == altura_alvo
            if np.sum(mask) == 0:
                print(f"Aviso: Nenhum dado encontrado para altura {altura_alvo}cm")
                return
            distancias = distancias[mask]
            velocidades = velocidades[mask]
            
            # Ajustar distância desejada baseada nos dados reais
            self.distancia_desejada = float(np.median(distancias))
            
            # Calcular quantis para as funções de pertinência
            q10, q25, q50, q75, q90 = np.percentile(distancias, [10, 25, 50, 75, 90])
        else:
            # Análise geral de todos os dados
            q10, q25, q50, q75, q90 = np.percentile(distancias, [10, 25, 50, 75, 90])
            self.distancia_desejada = float(q50)
        
        dist_max_dados = float(distancias.max())
        
        # Definir limites mais estreitos baseados nos dados reais
        limites_dist = {
            'muito_baixo_max': float(q10),
            'baixo_medio': float(q25),
            'baixo_max': float(q50 * 0.95),
            'ideal_medio': float(q50),
            'ideal_max': float(q50 * 1.05),
            'alto_min': float(q50 * 1.05),
            'alto_medio': float((q50 + q75) / 2),
            'alto_max': float(q75),
            'muito_alto_min': float(q75),
            'dist_max_dados': dist_max_dados
        }
        
        # Calcular limites de velocidade baseados nos dados
        v10, v25, v50, v75, v90 = np.percentile(velocidades, [10, 25, 50, 75, 90])
        limites_vel = {
            'muito_baixa_max': float(max(v10, 35)),
            'baixa_med': float(v25),
            'media_med': float(v50),
            'alta_med': float(v75),
            'alta_max': float(v90),
        }
        
        self._redefinir_funcoes_distancia(limites=limites_dist)
        self._redefinir_funcoes_velocidade(limites=limites_vel)
        self._recriar_regras_e_sistema()
        
        print(f"Calibração concluída:")
        print(f"  Distância desejada: {self.distancia_desejada:.2f} cm")
        print(f"  Faixa de distâncias: {q10:.1f} - {q90:.1f} cm")
        print(f"  Faixa de velocidades: {v10:.1f}% - {v90:.1f}%")

    def calibrar_com_dados_txt(self, caminho_txt):
        """
        Ajusta o controlador com base no log texto.
        Assumimos:
        - A distância registrada é do topo (sensor) até a bolinha, em cm.
        - PWM informado vai de 0 a 255; convertimos para % (pwm/255 * 100).
        """
        pwm_vals = []
        dist_vals = []
        padrao = re.compile(r"PWM:\s*(\d+).*?Dist[Ôô]ncia:\s*([\d.,]+)")

        with open(caminho_txt, "r", encoding="utf-8") as f:
            for linha in f:
                m = padrao.search(linha)
                if not m:
                    continue
                pwm_raw = float(m.group(1))
                dist_raw = m.group(2).replace(",", ".")
                try:
                    dist_cm = float(dist_raw)
                except ValueError:
                    continue
                pwm_vals.append(pwm_raw)
                dist_vals.append(dist_cm)

        if not pwm_vals or not dist_vals:
            raise ValueError("Não foi possível extrair PWM e distância de dados.txt.")

        pwm_vals = np.asarray(pwm_vals, dtype=float)
        dist_vals = np.asarray(dist_vals, dtype=float)

        pwm_pct = np.clip((pwm_vals / 255.0) * 100.0, 0, 100)

        # Quantis para distância (entrada)
        q10, q25, q50, q75, q90 = np.percentile(dist_vals, [10, 25, 50, 75, 90])
        dist_max_dados = dist_vals.max()
        self.distancia_desejada = float(q50)

        limites_dist = {
            'muito_baixo_max': q10,
            'baixo_medio': q25,
            'baixo_max': q50,
            'ideal_medio': q50,
            'ideal_max': q75,
            'alto_min': q50,
            'alto_medio': (q75 + q90) / 2,
            'alto_max': q90,
            'muito_alto_min': q75,
            'dist_max_dados': dist_max_dados
        }

        # Quantis para PWM em %
        p10, p25, p50, p75, p90 = np.percentile(pwm_pct, [45, 50, 55, 60, 65])
        limites_pwm = {
            'muito_baixa_max': p10,
            'baixa_med': p25,
            'media_med': p50,
            'alta_med': (p75 + p90) / 2,
            'alta_max': p90,
        }

        self._redefinir_funcoes_distancia(limites=limites_dist)
        self._redefinir_funcoes_velocidade(limites=limites_pwm)
        # Recriar as regras e o sistema de controle com as novas funções de pertinência
        self._recriar_regras_e_sistema()

    def _redefinir_funcoes_velocidade(self, limites=None):
        """Ajusta funções de pertinência de saída (PWM%)."""
        if limites:
            p10 = float(limites.get('muito_baixa_max', 15))
            p25 = float(limites.get('baixa_med', 25))
            p50 = float(limites.get('media_med', 55))
            p75 = float(limites.get('alta_med', 75))
            p90 = float(limites.get('alta_max', 90))
            
            # Garantir ordenação mínima e valores válidos
            # IMPORTANTE: Valores nunca podem ser menores que velocidade_minima
            vel_min = self.velocidade_minima
            p10 = np.clip(p10, vel_min, 100)
            p25 = np.clip(max(p25, p10 + 5), vel_min, 100)
            p50 = np.clip(max(p50, p25 + 5), vel_min, 100)
            p75 = np.clip(max(p75, p50 + 5), vel_min, 100)
            p90 = np.clip(max(p90, p75 + 5), vel_min, 100)

            self.velocidade_fan['muito_baixa'] = fuzz.trimf(
                self.velocidade_fan.universe,
                [vel_min, vel_min, p10]
            )
            
            baixa_min = max(p10 * 0.9, vel_min)
            self.velocidade_fan['baixa'] = fuzz.trimf(
                self.velocidade_fan.universe,
                [baixa_min, min(p25, p50 - 1), p50]
            )
            self.velocidade_fan['media'] = fuzz.trimf(
                self.velocidade_fan.universe,
                [max(p25, p50 - 10), p50, min(p75, 100)]
            )
            self.velocidade_fan['alta'] = fuzz.trimf(
                self.velocidade_fan.universe,
                [max(p50, p75 - 10), p75, min(p90, 100)]
            )
            self.velocidade_fan['muito_alta'] = fuzz.trimf(
                self.velocidade_fan.universe,
                [max(p75, p90 - 5), min(p90 + 5, 100), 100]
            )
            return

        # Perfil padrão baseado nos dados reais observados
        # Para alturas baixas (10-15cm): ~55%
        # Para alturas médias (20-25cm): ~60-65%
        # Para alturas altas (30-35cm): ~65-70%
        # IMPORTANTE: Todas as funções começam na velocidade_minima ou acima
        
        vel_min = self.velocidade_minima
        
        # Ajustar os pontos das funções de pertinência para não ficarem abaixo da vel_min
        self.velocidade_fan['muito_baixa'] = fuzz.trimf(
            self.velocidade_fan.universe,
            [vel_min, vel_min, max(vel_min + 5, 50)]
        )
        self.velocidade_fan['baixa'] = fuzz.trimf(
            self.velocidade_fan.universe,
            [vel_min, max(vel_min + 5, 50), max(vel_min + 13, 58)]
        )
        self.velocidade_fan['media'] = fuzz.trimf(
            self.velocidade_fan.universe,
            [max(vel_min + 7, 52), max(vel_min + 15, 60), max(vel_min + 23, 68)]
        )
        self.velocidade_fan['alta'] = fuzz.trimf(
            self.velocidade_fan.universe,
            [max(vel_min + 18, 63), max(vel_min + 27, 72), max(vel_min + 37, 82)]
        )
        self.velocidade_fan['muito_alta'] = fuzz.trimf(
            self.velocidade_fan.universe,
            [max(vel_min + 32, 77), max(vel_min + 45, 90), 100]
        )
    
    def visualizar_funcoes_pertinencia(self):
        """
        Visualiza as funções de pertinência do controlador fuzzy.
        Útil para debug e ajuste dos parâmetros.
        """
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Visualizar funções de pertinência da distância
        self.distancia_sensor.view(ax=ax1)
        ax1.set_title('Funções de Pertinência - Distância do Sensor')
        ax1.set_xlabel('Distância (cm)')
        ax1.set_ylabel('Pertinência')
        ax1.axvline(self.distancia_desejada, color='r', linestyle='--', 
                   label=f'Distância desejada: {self.distancia_desejada:.1f} cm')
        ax1.legend()
        
        # Visualizar funções de pertinência da velocidade
        self.velocidade_fan.view(ax=ax2)
        ax2.set_title('Funções de Pertinência - Velocidade do Fan')
        ax2.set_xlabel('Velocidade (%)')
        ax2.set_ylabel('Pertinência')
        
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    # Exemplo de uso
    print("\n" + "="*70)
    print("TESTE DO CONTROLADOR FUZZY MELHORADO")
    print("="*70)
    
    # Criar controlador com parâmetros otimizados
    controlador = ControladorFuzzy(
        altura_tubo=50,
        altura_sensor=2,
        altura_desejada=10,
        offset_velocidade=0.0,
        ganho_proporcional=0.4
    )
    
    # Tentar calibrar com dados do CSV se disponível
    try:
        print("\nCalibração com dados históricos...")
        controlador.calibrar_multiplas_alturas('log_experimento.csv')
    except FileNotFoundError:
        print("\nArquivo log_experimento.csv não encontrado. Usando valores padrão.")
    
    # Testar com diferentes alturas desejadas
    print("\n" + "="*70)
    print("TESTE DE DIFERENTES ALTURAS")
    print("="*70)
    
    for altura in [10, 15, 20, 25, 30, 35]:
        controlador.atualizar_altura_desejada(altura)
        print(f"\nAltura desejada: {altura} cm (Distância: {controlador.distancia_desejada:.1f} cm)")
        
        # Testar com distâncias próximas à ideal
        distancias_teste = [
            controlador.distancia_desejada - 3,
            controlador.distancia_desejada,
            controlador.distancia_desejada + 3
        ]
        
        for dist in distancias_teste:
            velocidade = controlador.calcular_velocidade(dist)
            altura_estimada = 50 - dist
            print(f"  Dist: {dist:5.1f}cm -> Vel: {velocidade:5.1f}% (altura ~{altura_estimada:5.1f}cm)")
    
    # Visualizar funções de pertinência para uma altura específica
    # controlador.atualizar_altura_desejada(20)
    # controlador.visualizar_funcoes_pertinencia()
