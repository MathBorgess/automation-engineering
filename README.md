1. Introdução 
Este documento tem como objetivo justificar a escolha das técnicas inteligentes para o projeto de identificação e controle do sistema de levitação de uma esfera em um tubo de ar. Devido aos desafios impostos pelo sistema, como não-linearidades e instabilidades aerodinâmicas, nossa equipe selecionou Algoritmos Genéticos (AG) para a etapa de identificação dos parâmetros do sistema e Lógica Fuzzy para a etapa de controle.
2. Justificativa para Identificação com Algoritmos Genéticos
Para a identificação da planta, escolhemos os Algoritmos Genéticos devido à sua robustez em processos de busca e otimização. Conforme analisado no artigo Comparison between evolutionary algorithms in height adjustment in a pneumatic levitator, métodos baseados na teoria da evolução, como o AG, são ferramentas eficazes para encontrar soluções ótimas em espaços de busca complexos, simulando processos de seleção natural.
O artigo de revisão sobre otimização de controladores destaca que os Algoritmos Genéticos são excelentes heurísticas de busca global, capazes de evitar que a solução fique presa em "mínimos locais", o que é comum em métodos clássicos de otimização. Utilizaremos essa capacidade para encontrar os parâmetros matemáticos que melhor descrevem o comportamento físico do nosso levitador a partir dos dados coletados.
3. Justificativa para Controle com Lógica Fuzzy
Para o controle da posição da esfera, optamos pela Lógica Fuzzy. O artigo Fuzzy Control Strategies Applied to an Air Levitation System ressalta que sistemas de levitação a ar são inerentemente não-lineares e sofrem com perturbações causadas pela turbulência do fluxo de ar, o que torna o controle clássico desafiador.
A grande vantagem da Lógica Fuzzy, segundo os estudos lidos, é que ela não exige um modelo matemático exato da planta para funcionar bem. O controlador pode ser projetado com base no "conhecimento de especialista" e regras linguísticas (exemplo: se a bola está muito baixa, aumente a potência do ventilador). Os resultados experimentais mostram que estratégias Fuzzy conseguem lidar bem com incertezas e manter a estabilidade do sistema mesmo com variações imprevisíveis.

4. Conclusão
Acreditamos que essa combinação é a ideal para o sucesso do projeto: o Algoritmo Genético nos dará um modelo confiável através de sua capacidade de otimização, enquanto o Controlador Fuzzy garantirá que a esfera se mantenha estável, absorvendo as instabilidades naturais do sistema pneumático que um controlador rígido poderia não suportar.
Referências Bibliográficas:
Fernando, G. M. J., Ángel, L. P. M., Genaro, G. R., Félix, S. L. J., Efrén, G. G. E., Arturo, V. R. R., & Laura, C. R. (2022). Comparison between evolutionary algorithms in height adjustment in a pneumatic levitator. Revista ELECTRO, 44(1), 83-87.
de Araújo, A. B., de Souza Bispo, C. A., Breganon, R., Alves, U. N. L. T., Martins, L. F. B., Ribeiro, F. S. F., & de Almeida, J. P. L. S. (2023). Fuzzy control strategies applied to an air levitation system. International Journal of Advances in Engineering & Technology, 16, 215-228.
Oladipo, S., Sun, Y., & Wang, Z. (2020). Optimization of PID controller with metaheuristic algorithms for DC motor drives. International Review of Electrical Engineering (I.R.E.E.), 15(5), 352-381.



