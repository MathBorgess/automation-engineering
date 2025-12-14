from simulador import SimuladorExperimento

if __name__ == '__main__':
    print("=" * 60)
    print("Experimento com Controladores (Fuzzy e Proporcional) - Dados Reais")
    print("=" * 60)
    print("O controlador tentará manter a bolinha na altura desejada.")
    print("Certifique-se de que o Arduino está conectado e o código está carregado.")
    print("\nControles:")
    print("- Botão: alterna Manual -> Proporcional -> Fuzzy")
    print("- Slider: controla o fan apenas no modo Manual")
    print("=" * 60)
    print()
    
    # Criar simulador (já conecta ao Arduino automaticamente)
    simulador = SimuladorExperimento()
    
    # Mostrar interface
    simulador.mostrar()
