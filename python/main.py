import asyncio
from agentes import ResponderAgent, CivilianAgent, SupplyVehicleAgent, ShelterAgent, DepotAgent
from ambiente import Environment
import pygame
import random
import time

async def spawn_civilians(env, civilians, responders):
    civilian_count = len(civilians)

    while True:
        await asyncio.sleep(random.randint(10, 20))  # Intervalo aleatório entre 10 e 20 segundos

        # Encontrar células disponíveis
        available_positions = [
            (i, j)
            for i in range(env.city_size)
            for j in range(env.city_size)
            if env.city_map[i][j] == 1
        ]

        if not available_positions:
            print("Nenhuma posição disponível para criar novos civilians.")
            continue

        # Escolher uma posição aleatória
        new_position = random.choice(available_positions)

        # Criar um novo civilian
        civilian_count += 1
        civilian_jid = f"civilian{civilian_count}@localhost"
        env.move_agent(new_position, new_position, agent_type=2)
        new_civilian = CivilianAgent(civilian_jid, "password", new_position, 2, len(responders))
        new_civilian.grau_urgencia = random.randint(1, 5)  # Grau de urgência aleatório
        await new_civilian.start()
        civilians.append(new_civilian)

        print(f"Novo civilian criado: {civilian_jid} na posição {new_position}.")



async def main():
    # Inicializar o ambiente
    env = Environment(size=10)
    env.draw_city()  # Desenhar mapa inicial

    env.add_buildings((2, 3))
    env.add_buildings((4, 8))
    env.add_buildings((7, 2))
    env.add_buildings((5, 5))

    # Criar Responders
    responders = []
    responder_positions = [[2, 6], [5, 2]]
    for i, pos in enumerate(responder_positions, start=1):
        env.move_agent(pos, pos, agent_type=3)
        responder = ResponderAgent(f"responder{i}@localhost", "password", pos, len(responder_positions), env)
        await responder.start()
        responders.append(responder)

    # Criar Civis
    civilians = []
    civilian_positions = [[4, 4], [3, 8]]
    for i, pos in enumerate(civilian_positions, start=1):
        env.move_agent(pos, pos, agent_type=2)
        civilian = CivilianAgent(f"civilian{i}@localhost", "password", pos, 2, len(responder_positions))
        civilian.grau_urgencia = random.randint(1, 5)  # Grau de urgência aleatório
        await civilian.start()
        civilians.append(civilian)

    # Criar Veículos de Suprimentos
    supply_vehicles = []
    supply_vehicle_positions = [[0, 0], [0, 0], [0, 0], [0, 0]]
    initial_resources = [
        {"agua_comida": 200, "medicamentos": 50, "combustivel": 100},
        {"agua_comida": 200, "medicamentos": 50, "combustivel": 100},
        {"agua_comida": 200, "medicamentos": 50, "combustivel": 100},
        {"agua_comida": 200, "medicamentos": 50, "combustivel": 100},
    ]
    for i, (pos, resources) in enumerate(zip(supply_vehicle_positions, initial_resources), start=1):
        env.move_agent(pos, pos, agent_type=7)
        vehicle = SupplyVehicleAgent(f"supply_vehicle{i}@localhost", "password", pos, env)
        vehicle.recursos = resources
        await vehicle.start()
        supply_vehicles.append(vehicle)

    shelters = []
    shelter_positions = [[1, 1], [9, 0], [6, 6]]  # Posições predefinidas para os shelters
    for i, pos in enumerate(shelter_positions, start=1):
        env.move_agent(pos, pos, agent_type=5)  # Supondo que o tipo de agente para shelters é 5
        shelter = ShelterAgent(f"shelter{i}@localhost", "password", pos)
        await shelter.start()
        shelters.append(shelter)

    #print(f"Total de shelters criados: {len(shelters)}")

    # Criar Depósito
    depot_position = [0, 0]
    vehicle_max_resources = {"agua_comida": 200, "medicamentos": 100, "combustivel": 100}
    env.move_agent(depot_position, depot_position, agent_type=9)
    depot = DepotAgent("depot@localhost", "password", depot_position, vehicle_max_resources)
    await depot.start()

    # Loop principal do jogo
    async def game_loop():
        await spawn_civilians(env, civilians, responders)

        start_time = time.time()  # Marca o tempo de início do loop
        duration = 3 * 60  # Duração de 3 minutos (em segundos)

        while time.time() - start_time < duration:  # Verifica se ainda está dentro do tempo permitido
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            # Simular derrocadas aleatórias
            if random.random() < 0.05:
                env.cause_landslides()

            await asyncio.sleep(0.1)  # Intervalo curto para atualizar o loop

        print("Fim do tempo de simulação. Encerrando agentes e saindo.")

    # Rodar o loop do jogo
    await asyncio.gather(game_loop())

    for responder in responders:
        await responder.stop()
    for vehicle in supply_vehicles:
        await vehicle.stop()
    for civilian in civilians:
        await civilian.stop()
    for shelter in shelters:
        await shelter.stop()
    await depot.stop()


if __name__ == "__main__":
    asyncio.run(main())
