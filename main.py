import asyncio
from agentes import ResponderAgent, CivilianAgent, SupplyVehicleAgent, ShelterAgent
from ambiente import Environment

async def main():
    env = Environment(size=10)

    #responder_position = [0, 0]
    #responder_agent = ResponderAgent("responder@localhost", "password", responder_position, env)
    #await responder_agent.start()

    #civilian_position = [8, 7]
    #civilian_agent = CivilianAgent("civilian_agent@localhost", "password", civilian_position)
    #await civilian_agent.start()

    #supply_vehicle_position = [0, 0]
    #supply_vehicle = SupplyVehicleAgent("supply_vehicle@localhost", "password", supply_vehicle_position, env)
    #await supply_vehicle.start()

    supply_vehicle_positions = [[0, 0], [9, 9], [2, 3]]  # Exemplo de posições iniciais para os vehicles
    supply_vehicles = []

    for i, position in enumerate(supply_vehicle_positions, start=1):
        vehicle_jid = f"supply_vehicle{i}@localhost"
        supply_vehicle = SupplyVehicleAgent(vehicle_jid, "password", position, env)
        await supply_vehicle.start()
        supply_vehicles.append(supply_vehicle)

    shelter_position = [5, 6]
    shelter = ShelterAgent("shelter@localhost", "password", shelter_position, len(supply_vehicle_positions))
    await shelter.start()

    #print(f"Posição do veiculo é: {supply_vehicle.position} ")
    #env.move_agent(supply_vehicle_position, supply_vehicle.position, 7)  # Atualiza no mapa
    #responder_agent.update_position(supply_vehicle_position)  # Atualiza no agente

    # Criar bloqueios de forma aleatória durante a execução
    #for _ in range(5):  # Exemplo de 5 tentativas de bloqueio
    #    env.random_blockage()

    #await asyncio.sleep(8)
    #print("Criando bloqueios dinâmicos no ambiente...")
    #env.random_blockage()
    #env.city_map[5][5] = 0

    # Aguarda 8 segundos e reduz o nível de água do shelter
    await asyncio.sleep(8)
    print("Reduzindo o nível de água do Shelter...")
    shelter.agua = 20  # Reduz para abaixo do limite de 30, acionando a solicitação

    # Aguarda mais alguns segundos para permitir que o veículo processe a solicitação
    await asyncio.sleep(15)

    await shelter.stop()
    for vehicle in supply_vehicles:
        await vehicle.stop()
    env.print_city_map()

if __name__ == "__main__":
    asyncio.run(main())

