import asyncio
from agentes import ResponderAgent, CivilianAgent, SupplyVehicleAgent, ShelterAgent
from ambiente import Environment

async def main():
    env = Environment(size=10)

    #responder_position = [0, 0]
    #responder_agent = ResponderAgent("responder@localhost", "password", responder_position)
    #await responder_agent.start()

    #civilian_position = [8, 7]
    #civilian_agent = CivilianAgent("civilian_agent@localhost", "password", civilian_position)
    #await civilian_agent.start()

    supply_vehicle_position = [0, 0]
    supply_vehicle = SupplyVehicleAgent("supply_vehicle@localhost", "password", supply_vehicle_position, env)
    await supply_vehicle.start()

    shelter_position = [5, 6]
    shelter = ShelterAgent("shelter@localhost", "password", shelter_position)
    await shelter.start()

    #print(f"Posição do veiculo é: {supply_vehicle.position} ")
    #env.move_agent(supply_vehicle_position, supply_vehicle.position, 7)  # Atualiza no mapa
    #responder_agent.update_position(supply_vehicle_position)  # Atualiza no agente

    # Criar bloqueios de forma aleatória durante a execução
    #for _ in range(5):  # Exemplo de 5 tentativas de bloqueio
    #    env.random_blockage()

    await asyncio.sleep(15)
    #await responder_agent.stop()
    #await civilian_agent.stop()
    await supply_vehicle.stop()
    await shelter.stop()

    #env.move_agent(supply_vehicle_position, supply_vehicle.position, 7)
    #print(f"Posição do veiculo é: {supply_vehicle.position} ")
    env.print_city_map()

if __name__ == "__main__":
    asyncio.run(main())

