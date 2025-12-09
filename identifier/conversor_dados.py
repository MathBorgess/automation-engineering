import chardet
import csv
import os
import re
import numpy as np

def extrair_pwm_distancia(linha):
    """
    Extrai PWM e distância da linha:
    Exemplo:
    PWM: 100, Medida 101: Distância: 42.65 cm
    """
    # Ignora linhas de PWM ajustado
    if "PWM ajustado" in linha:
        return None

    # pegar PWM
    m_pwm = re.search(r"PWM:\s*(\d+)", linha)
    if not m_pwm:
        return None
    pwm = int(m_pwm.group(1))

    # pegar distância
    m_dist = re.search(r"Dist.*?([\d\.]+)\s*cm", linha, re.IGNORECASE)
    if not m_dist:
        return None
    distancia = float(m_dist.group(1))
    distancia = np.round(distancia/100, 2)

    return pwm, distancia


def detectar_encoding(caminho_arquivo):
    """Detecta encoding usando chardet."""
    with open(caminho_arquivo, "rb") as f:
        raw = f.read()
        resultado = chardet.detect(raw)
        return resultado["encoding"]

def ler_arquivo(caminho_arquivo):
    """Lê o arquivo com encoding detectado e retorna lista de tuplas (pwm, distancia)"""
    encoding = detectar_encoding(caminho_arquivo)
    print(f"[INFO] Encoding detectado: {encoding}")

    dados = []

    with open(caminho_arquivo, "r", encoding=encoding, errors="ignore") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue

            # remove caracteres estranhos
            linha = linha.encode("utf-8", "ignore").decode("utf-8")

            resultado = extrair_pwm_distancia(linha)
            if resultado:
                dados.append(resultado)
    # Dados apresentam erros de medição, pela proximidade com o sensor
    dados = filtrar_pwm(dados)
    print(f"[INFO] {len(dados)} registros após remover PWM > 240.")
    dados = remover_spikes(dados)

    return dados

def filtrar_pwm(dados, limite=240):
    """
    Recebe lista de tuplas (pwm, distancia) e remove registros com pwm > limite
    """
    return [ (pwm, dist) for pwm, dist in dados if pwm <= limite ]

def remover_spikes(dados, delta_max=5.0):
    """
    Remove valores 'muito fora da curva' baseando-se na diferença com o valor anterior.
    - dados: lista de tuplas (pwm, distancia)
    - delta_max: diferença máxima aceitável entre distâncias consecutivas
    """
    if not dados:
        return []

    dados_filtrados = [dados[0]]  # mantém o primeiro valor
    for i in range(1, len(dados)):
        _, dist_atual = dados[i]
        _, dist_anterior = dados_filtrados[-1]

        if abs(dist_atual - dist_anterior) <= delta_max:
            dados_filtrados.append(dados[i])
        else:
            print(f"[INFO] Spike removido: {dist_atual} (Δ={dist_atual - dist_anterior:.2f})")

    return dados_filtrados


def salvar_csv(caminho_saida, dados):
    """Salva dados (lista de tuplas) em CSV com colunas pwm, distancia"""
    with open(caminho_saida, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["pwm", "distancia"])  # cabeçalho
        for pwm, distancia in dados:
            writer.writerow([pwm, distancia])

    print(f"[INFO] CSV salvo em: {caminho_saida}")


def converter_para_csv(arquivo_origem):
    """Pipeline completo"""
    saida = os.path.splitext(arquivo_origem)[0] + ".csv"

    print("[INFO] Lendo e tratando arquivo...")
    linhas = ler_arquivo(arquivo_origem)

    print("[INFO] Convertendo para CSV...")
    salvar_csv(saida, linhas)

    print("[OK] Conversão finalizada!")

if __name__ == "__main__":
    converter_para_csv("identifier/dados.txt")
