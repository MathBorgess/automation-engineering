import chardet
import csv
import os
import re
import numpy as np

def extrair_pwm_distancia(linha):
    """
    Extrai PWM e distância da linha.
    Retorna a distância em CENTÍMETROS (cm) para facilitar a filtragem.
    """
    # Ignora linhas de PWM ajustado ou logs de debug
    if "PWM ajustado" in linha:
        return None

    # Pegar PWM (Ex: "PWM: 100")
    m_pwm = re.search(r"PWM:\s*(\d+)", linha)
    if not m_pwm:
        return None
    pwm = int(m_pwm.group(1))

    # Pegar distância (Ex: "Distância: 42.65 cm")
    m_dist = re.search(r"Dist.*?([\d\.]+)\s*cm", linha, re.IGNORECASE)
    if not m_dist:
        return None
    
    distancia_cm = float(m_dist.group(1))
    # MANTEMOS EM CM AQUI para o filtro funcionar corretamente
    
    return pwm, distancia_cm


def detectar_encoding(caminho_arquivo):
    """Detecta encoding usando chardet."""
    with open(caminho_arquivo, "rb") as f:
        raw = f.read()
        resultado = chardet.detect(raw)
        return resultado["encoding"]

def filtrar_pwm(dados, limite=240):
    """
    Remove registros onde o PWM é maior que o limite (saturação ou erro).
    """
    return [ (pwm, dist) for pwm, dist in dados if pwm <= limite ]

def remover_spikes(dados, delta_max=10.0):
    """
    Remove valores 'muito fora da curva' (outliers).
    - dados: lista de tuplas (pwm, distancia_cm)
    - delta_max: diferença máxima aceitável em CM (padrão 10cm)
    """
    if not dados:
        return []

    dados_filtrados = [dados[0]]  # Mantém o primeiro valor
    spikes_removidos = 0

    for i in range(1, len(dados)):
        _, dist_atual = dados[i]
        _, dist_anterior = dados_filtrados[-1]

        # Se a variação for menor que o limite, aceita o dado
        if abs(dist_atual - dist_anterior) <= delta_max:
            dados_filtrados.append(dados[i])
        else:
            spikes_removidos += 1
            # Opcional: printar apenas os primeiros para não poluir o terminal
            if spikes_removidos <= 5:
                print(f"[INFO] Spike removido: {dist_atual:.1f}cm (Δ={dist_atual - dist_anterior:.1f}cm)")

    if spikes_removidos > 0:
        print(f"[INFO] Total de spikes removidos: {spikes_removidos}")
    
    return dados_filtrados

def ler_arquivo(caminho_arquivo):
    """Lê, filtra e trata os dados brutos."""
    if not os.path.exists(caminho_arquivo):
        print(f"[ERRO] Arquivo não encontrado: {caminho_arquivo}")
        return []

    encoding = detectar_encoding(caminho_arquivo)
    print(f"[INFO] Lendo {caminho_arquivo} com encoding: {encoding}")

    dados = []

    with open(caminho_arquivo, "r", encoding=encoding, errors="ignore") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            
            # Limpeza básica de caracteres
            linha = linha.encode("utf-8", "ignore").decode("utf-8")

            resultado = extrair_pwm_distancia(linha)
            if resultado:
                dados.append(resultado)
    
    print(f"[INFO] {len(dados)} linhas brutas lidas.")

    # 1. Filtra PWM inválido
    dados = filtrar_pwm(dados)
    
    # 2. Remove ruídos bruscos (spikes) usando lógica em CM
    dados = remover_spikes(dados, delta_max=10.0) 

    return dados

def salvar_csv(caminho_saida, dados):
    """
    Salva os dados processados em CSV.
    CONVERTE DE CM PARA METROS NESTA ETAPA.
    """
    if not dados:
        print("[AVISO] Nenhum dado para salvar.")
        return

    with open(caminho_saida, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["pwm", "distancia"])  # Cabeçalho
        
        for pwm, distancia_cm in dados:
            # CONVERSÃO FINAL: cm -> metros (SI)
            distancia_m = np.round(distancia_cm / 100.0, 3)
            writer.writerow([pwm, distancia_m])

    print(f"[SUCESSO] CSV salvo em: {caminho_saida}")
    print(f"          Total de registros válidos: {len(dados)}")


def converter_para_csv(arquivo_origem):
    """Pipeline completo de conversão"""
    # Define o nome de saída (mesmo nome, extensão .csv)
    saida = os.path.splitext(arquivo_origem)[0] + ".csv"

    print("--- INICIANDO CONVERSÃO ---")
    linhas = ler_arquivo(arquivo_origem)
    salvar_csv(saida, linhas)
    print("---------------------------")

if __name__ == "__main__":
    # Ajuste o caminho se necessário
    arquivo_input = "identifier/dados.txt"
    converter_para_csv(arquivo_input)