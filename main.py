import asyncio
from agentes import ResponderAgent, CivilianAgent, SupplyVehicleAgent, ShelterAgent
from ambiente import Environment

async def main():
    # Inicializar o ambiente
    env = Environment(size=10)

    # Criar veículos de suprimento
    supply_vehicle_positions = [[0, 0], [9, 9], [2, 3], [7, 7]]
    supply_vehicles = []

    # Criar os veículos com os recursos especificados
    initial_resources = [
        {"comida": 30, "agua": 0},  # Veículo 1
        {"comida": 0, "agua": 60},  # Veículo 2
        {"comida": 50, "agua": 40},   # Veículo 3
        {"comida": 30, "agua": 50}  # Veículo 4
    ]

    for i, (position, resources) in enumerate(zip(supply_vehicle_positions, initial_resources), start=1):
        vehicle_jid = f"supply_vehicle{i}@localhost"
        supply_vehicle = SupplyVehicleAgent(vehicle_jid, "password", position, env)

        # Configurar os recursos iniciais do veículo
        supply_vehicle.recursos = resources

        await supply_vehicle.start()
        supply_vehicles.append(supply_vehicle)

    # Criar o abrigo
    shelter_position = [5, 6]
    shelter = ShelterAgent("shelter@localhost", "password", shelter_position, len(supply_vehicle_positions))
    await shelter.start()

    # Imprimir o estado inicial do mapa
    print("\nMapa inicial da cidade:")
    env.print_city_map()

    print("\nIniciando simulação de 60 segundos...")

    # **Evento 1**: Aos 10 segundos, aparecem 2 `Civilian Agents`
    #await asyncio.sleep(10)

    '''
    print("\n[Evento] Aos 10 segundos: Aparecem 2 novos Civilian Agents")
    civilian1_position = [8, 7]
    civilian2_position = [6, 3]
    civilian1 = CivilianAgent("civilian1@localhost", "password", civilian1_position)
    civilian2 = CivilianAgent("civilian2@localhost", "password", civilian2_position)
    await civilian1.start()
    await civilian2.start()
    env.move_agent(civilian1_position, civilian1_position, 4)  # 4 representa `Civilian Agent`
    env.move_agent(civilian2_position, civilian2_position, 4)


    # Atualizar o mapa após surgirem os civis
    env.print_city_map()

    '''

    # **Evento 2**: Aos 30 segundos, o shelter esgota os recursos
    await asyncio.sleep(5)  # Total: 10 + 20 = 30 segundos
    print("\n[Evento] Aos 30 segundos: O Shelter esgota seus recursos")
    shelter.agua = 0
    #shelter.comida = 0
    print("O Shelter está agora sem recursos de água e comida.")

    # Esperar até o fim da simulação (60 segundos)
    await asyncio.sleep(20)  # Total: 30 + 30 = 60 segundos
    print(shelter.agua)
    print(shelter.comida)
    print("\nvai reduzir agua a seguir")

    shelter.agua = 10

    await asyncio.sleep(20)
    print(shelter.agua)
    print(shelter.comida)
    print("\nFim da simulação de 60 segundos")

    # Parar todos os agentes
    await shelter.stop()
    for vehicle in supply_vehicles:
        await vehicle.stop()

    # Imprimir estado final do mapa
    print("\nEstado final do mapa:")
    env.print_city_map()

if __name__ == "__main__":
    asyncio.run(main())
