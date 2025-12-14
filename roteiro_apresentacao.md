# Roteiro de apresentação (30 min) — Grupo (5 membros)

> **Regra de tempo**: 30 min total (25 min apresentação + 5 min discussão). **Cobrança rigorosa.**
>
> **Distribuição obrigatória**: 5 membros → **5 minutos por pessoa** (total 25 min).
>
> **Recomendação**: ensaiar com cronômetro e *transições* (troca de pessoa) de **≤ 10 s**.

---

## 1) Visão geral do tempo

- **00:00–05:00 — Membro 1**: Contexto, problema, sistema físico e objetivo.
- **05:00–10:00 — Membro 2**: Modelagem (visão física) e aquisição/pré-processamento de dados.
- **10:00–15:00 — Membro 3**: Identificação (Hammerstein + Evolução Diferencial) e validação.
- **15:00–20:00 — Membro 4**: Controlador Fuzzy (conceitos, implementação e testes).
- **20:00–25:00 — Membro 5**: Demonstração do sistema físico + conclusões e limitações.
- **25:00–30:00 — Discussão**: perguntas da turma/professor(a).

---

## 2) Plano de slides (sugestão: 12–14 slides)

> Observação: manter **~1 minuto por slide** como referência (com margens para demo).

### Slide 1 — Título e autores
- Título do projeto
- Nomes dos integrantes e disciplina

### Slide 2 — Motivação e desafios
- Por que levitação pneumática é um bom caso de estudo
- Desafios: não-linearidade, instabilidade, turbulência, ruído de sensor

### Slide 3 — Sistema físico (hardware)
- Tubo, esfera, fan, sensor, Arduino
- Entrada: PWM; Saída: altura/posição

### Slide 4 — Objetivos e abordagem
- Objetivo: estabilizar a esfera em uma altura de referência
- Pipeline: **modelagem → identificação → controle → validação física**

### Slide 5 — Modelagem (visão física simplificada)
- Ideia: forças atuando na esfera (gravidade × força aerodinâmica/arrasto)
- O que é *modelo físico simplificado* e por que ele ajuda

### Slide 6 — Aquisição de dados (malha aberta)
- Como foi coletado: variação de PWM e leitura do sensor
- Taxa de amostragem / janelas de coleta

### Slide 7 — Pré-processamento
- Limpeza: remoção de spikes/outliers
- Conversão de unidades (cm → m) e impacto na identificação

### Slide 8 — Modelo de Hammerstein (conceito)
- Bloco não-linear estático + bloco linear dinâmico
- Por que faz sentido para fan + dinâmica da esfera

### Slide 9 — Identificação por Evolução Diferencial
- Ideia: otimização metaheurística por população
- Função custo: MSE entre dados reais e saída do modelo

### Slide 10 — Resultados da identificação
- Gráfico comparativo (real × Hammerstein)
- Métrica: MSE e interpretação (o que o modelo captura/erra)

### Slide 11 — Controle Fuzzy (conceito)
- Por que Fuzzy: robustez a incertezas e dificuldade de modelo exato
- Regras linguísticas e funções de pertinência

### Slide 12 — Implementação do controlador e testes
- Como o controlador gera o PWM
- Testes: setpoints, ruído/turbulência (simulação e/ou físico)
- Comparação rápida: **Proporcional (baseline)** vs **Fuzzy (melhorado)**

### Slide 13 — Demonstração do sistema físico (ao vivo)
- Mostrar: referência → esfera estabilizando
- Mostrar: resposta a perturbação leve (se for seguro)
- Mostrar protocolo/telemetria: comandos `FAN:XX` e leituras `DIST:YY.Y`

### Slide 14 — Conclusões e trabalhos futuros
- Lições aprendidas
- Melhorias: mais testes, métricas (IAE/ISE/ITAE), PD-Fuzzy completo, integração fim-a-fim no Arduino

---

## 3) Script por membro (fala + entregáveis)

### Membro 1 (00:00–05:00) — Introdução e sistema
**Objetivo da fala**: convencer que o problema é relevante e delimitar o que foi feito.

Checklist:
- [ ] Apresentar rapidamente o problema: controlar posição com fan.
- [ ] Explicar por que é difícil: não-linearidade, instabilidade, turbulência.
- [ ] Mostrar foto/diagrama do sistema físico e sinal (PWM → altura).

Frases-guia (curtas):
- “A planta é não linear e sensível a turbulência; por isso combinamos identificação e controle inteligente.”
- “A entrada é PWM no ventilador, e a saída é a altura medida pelo sensor.”

### Membro 2 (05:00–10:00) — Modelagem física + dados
**Objetivo da fala**: mostrar que existe embasamento físico e rigor experimental nos dados.

Checklist:
- [ ] Intuição do modelo físico: forças e movimento vertical.
- [ ] Como os dados foram coletados (malha aberta) e por quê.
- [ ] Pré-processamento: por que remover spikes e converter unidades.

Frases-guia:
- “Mesmo com um modelo físico simplificado, o sistema real tem variabilidades; por isso a identificação data-driven é útil.”

### Membro 3 (10:00–15:00) — Identificação (Hammerstein + DE)
**Objetivo da fala**: explicar como o modelo foi obtido e como foi validado.

Checklist:
- [ ] Explicar Hammerstein: NL estática + dinâmica linear.
- [ ] Explicar Evolução Diferencial: busca populacional, robusta em não convexidade.
- [ ] Mostrar gráfico real × modelo e a métrica MSE.

Frases-guia:
- “A DE ajusta os parâmetros minimizando o MSE; isso evita ficar preso em mínimos locais em alguns cenários.”

### Membro 4 (15:00–20:00) — Controle Fuzzy
**Objetivo da fala**: mostrar como o controlador toma decisão e por que funciona bem em prática.

Checklist:
- [ ] Variáveis linguísticas (**distância do sensor** como entrada principal, conforme a implementação atual).
- [ ] Funções de pertinência e regras.
- [ ] Complementos do controlador: correção proporcional, filtro de suavização e velocidade mínima.
- [ ] (Se aplicável) calibração por histórico (`log_experimento.csv`) e uso de lookup distância→velocidade.
- [ ] Mostrar resultado em simulação e/ou testes físicos (se houver).

Frases-guia:
- “O Fuzzy permite incorporar heurística e lidar melhor com incertezas e ruído sem exigir um modelo perfeito.”

### Membro 5 (20:00–25:00) — Demonstração + conclusão
**Objetivo da fala**: provar funcionamento e fechar com mensagem clara.

Checklist:
- [ ] **Demo ao vivo (≈ 3 min)**: estabilizar em um setpoint e mostrar a leitura do sensor.
- [ ] **Fechamento (≈ 2 min)**: conclusões, limitações e próximos passos.

Sugestão de demo (sequência):
1) Mostrar estado inicial (esfera fora do setpoint)
2) Mostrar modo **Manual** (PWM fixo) por alguns segundos
3) Alternar para **Proporcional** (baseline) e observar resposta
4) Alternar para **Fuzzy** (melhorado) e observar estabilidade
5) Pequena perturbação controlada (opcional) e recuperação

Frases-guia:
- “A principal evidência prática é a estabilização com ruído/turbulência presentes.”
- “Próximo passo: ampliar testes (degraus e variações), medir IAE/ISE/ITAE e consolidar o controle no hardware.”

---

## 4) Discussão (25:00–30:00) — perguntas esperadas

Perguntas comuns e respostas curtas:
- **Por que Hammerstein e não um modelo puramente linear?**
  - Porque a atuação do fan e o escoamento impõem não-linearidade; o Hammerstein separa NL estática da dinâmica.
- **Por que Evolução Diferencial?**
  - Por ser metaheurística robusta para otimização não convexa e funcionar bem com função custo baseada em erro.
- **Como vocês validaram o controlador?**
  - Em simulação e/ou físico, observando estabilidade, oscilação e erro em regime; (se tiver) também por métricas de erro.
- **O que mais atrapalha no físico?**
  - Turbulência do fluxo, ruído do sensor e saturação do atuador.

---

## 5) Checklist de ensaio (recomendado)

- [ ] Rodar 2 ensaios completos cronometrados (25 min cravado)
- [ ] Ensaiar demo com plano B (se falhar, mostrar vídeo/gravação/print de resultados)
- [ ] Garantir que cada integrante tenha exatamente ~5 min
- [ ] Preparar transição rápida entre falas (slide “ponte” opcional)
