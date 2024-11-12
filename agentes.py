from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
import ast  # Para usar ast.literal_eval
from ambiente import Environment
import asyncio
from pathfinding import a_star

class ResponderAgent(Agent):
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position

    class ResponderBehaviour(CyclicBehaviour):
        async def run(self):
            print("Aguardando solicitações de ajuda...")

            msg = await self.receive(timeout=10)
            if msg:
                print(f"Recebida solicitação de {msg.sender}: {msg.body}")

                reply = Message(to=str(msg.sender))
                reply.body = "Solicitação recebida. A caminho!"
                await self.send(reply)
                print("Resposta enviada ao civil.")
            else:
                print("Nenhuma solicitação  de ajuda recebida.")

    async def setup(self):
        print("Responder Agent iniciado")
        self.responder_behaviour = self.ResponderBehaviour()
        self.add_behaviour(self.responder_behaviour)

    def update_position(self, new_position):
        self.position = new_position
        print(f"Responder movido para {self.position}")

class CivilianAgent(Agent):
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position

    class RequestHelpBehaviour(OneShotBehaviour):
        async def run(self):
            print("Enviado solicitação de ajuda...")

            msg = Message(to="responder@localhost")
            msg.body = "Ajuda necessária em [coordenadas do civil]"
            await self.send(msg)
            print("Solicitação de ajuda enviada!")

            reply = await self.receive(timeout=10)
            if reply:
                print(f"Recebida resposta de ResponderAgent: {reply.body}")
            else:
                print("Nenhuma resposta recebida.")

    async def setup(self):
        print("Civilian Agent iniciado")
        self.request_help_behaviour = self.RequestHelpBehaviour()
        self.add_behaviour(self.request_help_behaviour)

    def update_position(self, new_position):
        self.position = new_position
        print(f"Civilian movido para {self.position}")

class SupplyVehicleAgent(Agent):
    def __init__(self, jid, password, position, environment):
        super().__init__(jid, password)
        self.position = position  # Posição inicial do veículo
        self.environment = environment

    class SupplyBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                print(f"Solicitação de suprimentos recebida de {msg.sender}: {msg.body}")
                await self.deliver_resources(msg)

                shelter_position = self.extract_shelter_position(msg.body)
                if shelter_position:
                    await self.move_to_shelter(shelter_position)
            else:
                print("Nenhuma solicitação de suprimentos recebida.")

        async def deliver_resources(self, msg):
            resources = msg.body
            print(f"Entregando {resources} para {msg.sender}.")
            reply = Message(to=str(msg.sender))
            reply.body = f"Suprimentos '{resources}' entregues!"
            await self.send(reply)

        def extract_shelter_position(self, msg_body):
            # Extrair a posição do abrigo da mensagem
            try:
                return ast.literal_eval(msg_body)  # Usar ast.literal_eval para maior segurança
            except:
                print("Erro ao extrair a posição do abrigo.")
                return None

        async def move_to_shelter(self, shelter_position):
            print(f"Iniciando movimento para o abrigo na posição {shelter_position}.")

            # Usa o A* para encontrar o caminho completo até o abrigo
            path = a_star(self.agent.environment, tuple(self.agent.position), tuple(shelter_position))

            if path is None:
                print("Nenhum caminho encontrado para o abrigo!")
                return

            print(f"Caminho calculado pelo A*: {path}")

            # Segue o caminho calculado
            for next_position in path[1:]:  # Ignora o primeiro ponto (posição inicial)
                if self.agent.environment.is_road_free(next_position) or next_position == tuple(shelter_position):
                    self.agent.environment.move_agent(tuple(self.agent.position), next_position, agent_type=7)
                    self.agent.update_position(next_position)
                    print(f"Movido para {next_position}")
                else:
                    print(f"Caminho bloqueado em {next_position} durante o movimento. Recalculando caminho...")
                    # Recalcula o caminho se encontrar um bloqueio
                    path = a_star(self.agent.environment, tuple(self.agent.position), tuple(shelter_position))
                    if path is None:
                        print("Nenhum caminho alternativo encontrado!")
                        return

                await asyncio.sleep(1)  # Pequeno atraso para simular movimento

            print("Chegou ao abrigo.")

    async def setup(self):
        print(f"Supply Vehicle iniciado na posição {self.position}")
        self.add_behaviour(self.SupplyBehaviour())

    def update_position(self, new_position):
        self.position = new_position  # Atualiza a posição do veículo
        print(f"SupplyVehicle movido para {self.position}")

class ShelterAgent(Agent):
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position  # Posição inicial do abrigo

    class ShelterBehaviour(OneShotBehaviour):
        async def run(self):
            print("Abrigo aguardando recursos.")
            resources_needed = "água e alimentos"
            msg = Message(to="supply_vehicle@localhost")
            msg.body = str(self.agent.position)  # Enviando a posição do abrigo

            await self.send(msg)
            print("Solicitação de suprimentos enviada.")

            reply = await self.receive(timeout=10)
            if reply:
                print(f"Suprimentos recebidos de {reply.sender}")
            else:
                print("Nenhuma resposta recebida.")

    async def setup(self):
        print(f"Shelter iniciado na posição {self.position}")
        self.add_behaviour(self.ShelterBehaviour())