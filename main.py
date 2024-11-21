import asyncio
from agentes import ResponderAgent, CivilianAgent, SupplyVehicleAgent, ShelterAgent, DepotAgent
from ambiente import Environment
import pygame

async def main():
    # Inicializar o ambiente
    env = Environment(size=10)
    env.draw_city()  # Desenhar mapa inicial

    responder_position = [7, 8]  # Posição inicial do depósito
    env.move_agent(responder_position,responder_position,agent_type=3)
    responder = ResponderAgent("responder1@localhost", "password", responder_position, 3, env)
    await responder.start()

    responder_position2 = [4, 5]  # Posição inicial do depósito
    env.move_agent(responder_position2, responder_position2, agent_type=3)
    responder2 = ResponderAgent("responder2@localhost", "password", responder_position2, 3, env)
    await responder2.start()

    #responder_position3 = [5, 5]  # Posição inicial do depósito
    #env.move_agent(responder_position3, responder_position3, agent_type=3)
    #responder3 = ResponderAgent("responder3@localhost", "password", responder_position3, 3, env)
    #await responder3.start()

    civilian_position1 = [2, 4]  # Posição inicial do depósito
    env.move_agent(civilian_position1, civilian_position1, agent_type=2)
    civilian1 = CivilianAgent("civilian1@localhost", "password", civilian_position1,2,3)
    await civilian1.start()

    #await asyncio.sleep(5)
    civilian_position2 = [4, 2]  # Posição inicial do depósito
    env.move_agent(civilian_position2, civilian_position2, agent_type=2)
    civilian2 = CivilianAgent("civilian2@localhost", "password", civilian_position2,2,3)
    await civilian2.start()

    #civilian_position3 = [6, 7]  # Posição inicial do depósito
    #env.move_agent(civilian_position3, civilian_position3, agent_type=2)
    #civilian3 = CivilianAgent("civilian3@localhost", "password", civilian_position3, 2, 3)
    #await civilian3.start()

    shelter1_position = [7, 7]
    env.move_agent(shelter1_position, shelter1_position, agent_type=5)
    shelter1 = ShelterAgent("shelter1@localhost", "password", shelter1_position, 3)
    await shelter1.start()

    shelter2_position = [5, 7]
    env.move_agent(shelter2_position, shelter2_position, agent_type=5)
    shelter2 = ShelterAgent("shelter2@localhost", "password", shelter2_position, 3)
    await shelter2.start()

    '''
    # Criar veículos de suprimento
    supply_vehicle_positions = [[0, 0], [0, 0], [0, 0], [0, 0]]
    supply_vehicles = []

    # Criar os veículos com os recursos especificados
    initial_resources = [
        {"agua_comida": 200,  "medicamentos": 50,  "combustivel": 100},  # Veículo 1
        {"agua_comida": 200,  "medicamentos": 50,  "combustivel": 100},  # Veículo 2
        {"agua_comida": 200,  "medicamentos": 50,  "combustivel": 100},
        {"agua_comida": 200,  "medicamentos": 50,  "combustivel": 100}
    ]

    for i, (position, resources) in enumerate(zip(supply_vehicle_positions, initial_resources), start=1):
        vehicle_jid = f"supply_vehicle{i}@localhost"
        env.move_agent(position, position, agent_type=7)
        supply_vehicle = SupplyVehicleAgent(vehicle_jid, "password", position, env)

        # Configurar os recursos iniciais do veículo
        supply_vehicle.recursos = resources

        await supply_vehicle.start()
        supply_vehicles.append(supply_vehicle)

    # Criar o depósito central
    depot_position = [0, 0]  # Posição inicial do depósito
    vehicle_max_resources = {"agua_comida": 200, "medicamentos": 100, "combustivel": 100}
    env.move_agent(depot_position, depot_position, agent_type=9)
    depot = DepotAgent("depot@localhost", "password", depot_position, vehicle_max_resources)
    await depot.start()

    # Criar os abrigos com capacidades e posições diferentes
    shelter1_position = [7, 7]
    env.move_agent(shelter1_position, shelter1_position, agent_type=5)
    shelter1 = ShelterAgent("shelter1@localhost", "password", shelter1_position, len(supply_vehicle_positions))
    await shelter1.start()

    shelter2_position = [5, 5]
    env.move_agent(shelter2_position, shelter2_position, agent_type=5)
    shelter2 = ShelterAgent("shelter2@localhost", "password", shelter2_position, len(supply_vehicle_positions))
    await shelter2.start()

    # Atualiza o mapa para incluir os abrigos
    #env.move_agent(shelter1_position, shelter1_position, agent_type=5)  # Representa o Shelter 1
    #env.move_agent(shelter2_position, shelter2_position, agent_type=5)  # Representa o Shelter 2

    # Simulação
    print("\nMapa inicial da cidade:")
    env.print_city_map()

    print("\nIniciando simulação de 60 segundos...")

    # Evento 1: Abrigos esgotam seus recursos
    await asyncio.sleep(5)
    print("\n[Evento] Shelter 1 esgota seus recursos.")
    shelter1.pessoas=50
    shelter2.pessoas = 30
    print("Shelter 1 agora sem água e comida.")

    #await asyncio.sleep(12)
    print("\n[Evento] Shelter 2 esgota seus recursos.")
    #shelter2.agua_comida = 0
    #shelter2.medicamentos = 0
    print("Shelter 2 agora sem água e medicamentos.")

    # Espera até o fim da simulação
    #await asyncio.sleep(50)
    print("\nFim da simulação de 60 segundos")

    print("\nEstado final do mapa:")
    env.print_city_map()
    '''

    async def game_loop():
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            await asyncio.sleep(0.1)  # Pequeno delay para não travar o programa

    # Rodar a simulação e o loop do jogo
    await asyncio.gather(
        game_loop(),
        asyncio.sleep(60)  # Simulação principal
    )

    # Finalizar agentes
    await responder.stop()
    await responder2.stop()
    await civilian1.stop()
    await shelter1.stop()
    #await civilian2.stop()

    #await shelter2.stop()
    #for vehicle in supply_vehicles:
    #    await vehicle.stop()
    #await depot.stop()




if __name__ == "__main__":
    asyncio.run(main())
