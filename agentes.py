import time

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
import ast  # Para usar ast.literal_eval
from ambiente import Environment
import asyncio
from pathfinding import a_star

class ResponderAgent(Agent):
    def __init__(self, jid, password, position, environment):
        super().__init__(jid, password)
        self.position = position
        self.environment = environment

    class ResponderBehaviour(CyclicBehaviour):
        async def run(self):
            print("Aguardando solicitações de ajuda...")

            # Recebe a mensagem de pedido de ajuda
            msg = await self.receive(timeout=10)
            if msg and msg.get_metadata("performative") == "request":
                print(f"Recebida solicitação de {msg.sender}: {msg.body}")

                # Extrai a posição do Civilian Agent
                civil_position = self.extract_coordinates(msg)
                if not civil_position:
                    return

                # Calcula o caminho até o Civilian
                path = self.calculate_path(civil_position)
                if not path:
                    print("Nenhum caminho encontrado para o Civilian!")
                    return

                # Segue o caminho até o Civilian
                await self.follow_path(path, msg)

                # Ao chegar, procura um shelter disponível
                await self.find_shelter()

        def extract_coordinates(self, msg):
            """Extrai as coordenadas do Civilian a partir da mensagem."""
            try:
                _, position_info = msg.body.split("em")
                civil_position = eval(position_info.strip())  # Converte para tupla (x, y)
                print(f"Posição do Civilian: {civil_position}")
                return civil_position
            except Exception as e:
                print(f"Erro ao interpretar a posição: {e}")
                return None

        def calculate_path(self, target_position):
            """Calcula o caminho até a posição do Civilian usando A*."""
            path = a_star(self.agent.environment, tuple(self.agent.position), tuple(target_position))
            if path:
                print(f"Caminho calculado para o Civilian: {path}")
            else:
                print("Falha ao calcular o caminho.")
            return path

        async def follow_path(self, path, msg):
            """Segue o caminho calculado até o Civilian, recalculando se encontrar bloqueios."""
            for next_position in path[1:]:  # Ignora a posição inicial
                if self.agent.environment.is_road_free(next_position):
                    self.agent.environment.move_agent(tuple(self.agent.position), next_position,
                                                      agent_type=7)  # Representando o Responder
                    self.agent.update_position(next_position)
                    print(f"Responder movido para {next_position}")
                else:
                    print(f"Caminho bloqueado em {next_position}. Recalculando caminho...")
                    path = self.calculate_path(eval(msg.body.split("em")[1].strip()))
                    if not path:
                        print("Nenhum caminho alternativo encontrado!")
                        return
                    await self.follow_path(path, msg)
                    return

                await asyncio.sleep(1)  # Pequeno atraso para simular movimento

            print("Responder chegou ao Civilian.")
            await self.confirm_arrival(msg)

        async def confirm_arrival(self, msg):
            """Envia uma mensagem de confirmação ao Civilian ao chegar na posição."""
            reply = Message(to=str(msg.sender))
            reply.body = "Cheguei ao local e estou pronto para ajudar!"
            await self.send(reply)
            print("Mensagem de chegada enviada ao Civilian.")

        async def find_shelter(self):
            """Procura um shelter disponível e envia uma mensagem de consulta."""
            print("Procurando um Shelter disponível...")

            # Aqui vamos simular o envio de uma mensagem para um Shelter Agent
            # Em um cenário real, você teria uma lista de abrigos ou uma função para encontrá-los
            shelter_jid = "shelter@localhost"  # Substitua pelo JID real do shelter
            msg = Message(to=shelter_jid)
            msg.body = f"Verificação de capacidade de shelter perto de {self.agent.position}"
            msg.set_metadata("performative", "query")  # Indicando que é uma consulta
            await self.send(msg)
            print(f"Consulta enviada para o Shelter em {shelter_jid}.")

            # Espera uma resposta do shelter sobre a capacidade
            reply = await self.receive(timeout=10)
            if reply:
                print(f"Resposta recebida do Shelter: {reply.body}")
            else:
                print("Nenhuma resposta recebida do Shelter.")

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
            print("Enviando solicitação de ajuda...")

            # Define a mensagem de pedido de ajuda com posição
            msg = Message(to="responder@localhost")  # Coloque aqui o JID correto do Responder
            msg.body = f"Ajuda necessária em {self.agent.position}"
            msg.set_metadata("performative", "request")  # Metadado para identificar a natureza da mensagem
            await self.send(msg)
            print(f"Solicitação de ajuda enviada! Posição: {self.agent.position}")

            # Aguardar resposta do Responder Agent
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


from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import asyncio

class SupplyVehicleAgent(Agent):
    def __init__(self, jid, password, position, environment):
        super().__init__(jid, password)
        self.position = position
        self.environment = environment

        # Estoque inicial de recursos no veículo
        self.recursos = {
            "agua": 200,
            "comida": 200,
            "medicamentos": 100,
            "bens": 100
        }

    class SupplyBehaviour(CyclicBehaviour):
        async def run(self):
            print("Supply Vehicle aguardando pedidos de recursos...")

            # Recebe a mensagem de solicitação de recursos via broadcast
            msg = await self.receive(timeout=10)
            #print(msg)
            if msg and msg.get_metadata("performative") == "request":
                print(f"Pedido de broadcast recebido do Shelter: {msg.body}")

                # Extrai o tipo e quantidade do recurso solicitado
                try:
                    recurso, quantidade, posicao_shelter = self.parse_request(msg.body)
                    print(f"Pedido de {quantidade} unidades de {recurso} para o shelter em {posicao_shelter}")

                    # Responde apenas se tiver capacidade suficiente
                    if self.agent.recursos[recurso] >= quantidade:
                        # Envia uma resposta com a posição do vehicle
                        response = Message(to=str(msg.sender))
                        response.body = f"resposta {self.agent.position} {recurso} {quantidade}"
                        response.set_metadata("performative", "response")
                        await self.send(response)
                        print(f"{self.agent.jid} enviou sua posição para o Shelter.")

                except Exception as e:
                    print(f"Erro ao processar o pedido: {e}")

            # Recebe o pedido de confirmação direto do shelter para a entrega
            elif msg and msg.get_metadata("performative") == "confirm":
                recurso, quantidade, posicao_shelter = self.parse_request(msg.body)
                print(f"{self.agent.jid} recebeu confirmação para entregar {quantidade} de {recurso}.")
                await self.deliver_supplies(recurso, quantidade, posicao_shelter, str(msg.sender))

        def parse_request(self, body):
            """Extrai o tipo de recurso, quantidade e posição do Shelter da mensagem."""
            try:
                parts = body.split()
                recurso = parts[1]  # Segundo elemento é o recurso
                quantidade = int(parts[2])  # Terceiro elemento é a quantidade
                posicao_shelter = eval(" ".join(parts[3:]))
                return recurso, quantidade, posicao_shelter
            except Exception as e:
                raise ValueError(f"Erro ao interpretar a mensagem: {e}")

        async def deliver_supplies(self, recurso, quantidade, posicao_shelter, shelter_jid):
            """Move o vehicle até o shelter e entrega o recurso."""
            # Calcula o caminho até o Shelter
            path = a_star(self.agent.environment, tuple(self.agent.position), tuple(posicao_shelter))
            if not path:
                print("Nenhum caminho encontrado para o Shelter!")
                return

            # Segue o caminho até o Shelter
            for next_position in path[1:]:
                if next_position == tuple(posicao_shelter):
                    self.agent.environment.move_agent(tuple(self.agent.position), next_position,
                                                      agent_type=8)  # Representando o Vehicle
                    self.agent.update_position(next_position)
                    break

                if self.agent.environment.is_road_free(next_position):
                    self.agent.environment.move_agent(tuple(self.agent.position), next_position,
                                                      agent_type=8)  # Representando o Vehicle
                    self.agent.update_position(next_position)
                    #print(f"Vehicle movido para {next_position}")
                else:
                    print(f"Caminho bloqueado em {next_position}. Recalculando caminho...")
                    path = a_star(self.agent.environment, tuple(self.agent.position), posicao_shelter)
                    if not path:
                        print("Nenhum caminho alternativo encontrado!")
                        return
                    await self.deliver_supplies(recurso, quantidade, posicao_shelter,shelter_jid)  # Tenta seguir o novo caminho
                    return
                await asyncio.sleep(1)  # Simula o movimento

            print(f"Vehicle chegou ao shelter e entregou {quantidade} unidades de {recurso}.")
            self.agent.recursos[recurso] -= quantidade

            # Envia confirmação de entrega para o Shelter
            reply = Message(to=shelter_jid)
            reply.body = f"Entrega de {quantidade} unidades de {recurso} realizada."
            reply.set_metadata("performative", "confirm")
            await self.send(reply)

    async def setup(self):
        print("Supply Vehicle Agent iniciado")
        self.supply_behaviour = self.SupplyBehaviour()
        self.add_behaviour(self.supply_behaviour)

    def update_position(self, new_position):
        self.position = new_position
        print(f"SupplyVehicle movido para {self.position}")



class ShelterAgent(Agent):
    def __init__(self, jid, password, position, max_vehicles=20):
        super().__init__(jid, password)
        self.position = position
        self.max_vehicles = max_vehicles


        # Atributos de recursos
        self.agua = 100
        self.comida = 100
        self.medicamentos = 50
        self.bens = 50

        # Limites mínimos para chamar o Vehicle
        self.limite_agua = 30
        self.limite_comida = 30
        self.limite_medicamentos = 10
        self.limite_bens = 10

        # Dicionário para rastrear quais recursos já foram solicitados
        self.solicitado = {
            "agua": False,
            "comida": False,
            "medicamentos": False,
            "bens": False
        }

        self.vehicle_positions = {}

    class ResourceCheckBehaviour(CyclicBehaviour):
        async def run(self):
            print("Verificando níveis de recursos...")

            # Verifica cada recurso e solicita apenas se abaixo do limite e ainda não solicitado
            if self.agent.agua < self.agent.limite_agua and not self.agent.solicitado["agua"]:
                self.agent.solicitado["agua"] = True  # Marca como solicitado
                await self.start_request_supplies_behaviour("agua", self.agent.limite_agua - self.agent.agua)

            if self.agent.comida < self.agent.limite_comida and not self.agent.solicitado["comida"]:
                self.agent.solicitado["comida"] = True  # Marca como solicitado
                await self.start_request_supplies_behaviour("comida", self.agent.limite_comida - self.agent.comida)

            if self.agent.medicamentos < self.agent.limite_medicamentos and not self.agent.solicitado["medicamentos"]:
                self.agent.solicitado["medicamentos"] = True  # Marca como solicitado
                await self.start_request_supplies_behaviour("medicamentos",
                                                            self.agent.limite_medicamentos - self.agent.medicamentos)

            if self.agent.bens < self.agent.limite_bens and not self.agent.solicitado["bens"]:
                self.agent.solicitado["bens"] = True  # Marca como solicitado
                await self.start_request_supplies_behaviour("bens", self.agent.limite_bens - self.agent.bens)

            await asyncio.sleep(5)  # Aguarda alguns segundos antes de verificar novamente

        async def start_request_supplies_behaviour(self, item, quantidade):
            """Inicia o RequestSuppliesBehaviour para o recurso especificado."""
            print(f"Recurso {item} abaixo do limite. Iniciando RequestSuppliesBehaviour...")
            behaviour = self.agent.RequestSuppliesBehaviour(item, quantidade)
            self.agent.add_behaviour(behaviour)

    class RequestSuppliesBehaviour(OneShotBehaviour):
        def __init__(self, item, quantidade):
            super().__init__()
            self.item = item
            self.quantidade = quantidade
            self.responses = {}  # Armazena as respostas dos veículos

        async def run(self):
            print(f"Enviando pedido de {self.item} ({self.quantidade} unidades) para os veículos...")

            # Envia broadcast para todos os veículos
            for i in range(1, self.agent.max_vehicles + 1):
                vehicle_jid = f"supply_vehicle{i}@localhost"  # Convenção de nomes para os veículos
                msg = Message(to=vehicle_jid)
                msg.body = f"pedido {self.item} {self.quantidade} {self.agent.position}"
                msg.set_metadata("performative", "request")
                await self.send(msg)
                print(f"Pedido de {self.item} enviado para {vehicle_jid}.")

            # Aguarda respostas dos veículos durante o timeout
            await self.collect_responses(timeout=5)

            # Processa as respostas e escolhe o veículo mais próximo
            await self.process_responses()

        async def collect_responses(self, timeout):
            print(f"Aguardando respostas dos veículos por {timeout} segundos...")
            start_time = time.time()

            while time.time() - start_time < timeout:
                msg = await self.receive(timeout=1)  # Verifica mensagens com pequenos intervalos
                if msg and msg.get_metadata("performative") == "response":
                    print(f"Resposta recebida de {msg.sender}: {msg.body}")

                    # Processa a mensagem e armazena a resposta
                    parts = msg.body.split()
                    position_str = f"{parts[1]} {parts[2]}"
                    vehicle_position = eval(position_str)  # Substituir por json.loads no futuro
                    self.responses[str(msg.sender)] = {
                        "position": vehicle_position,
                        "item": parts[3],
                        "quantidade": int(parts[4]),
                    }

        async def process_responses(self):
            if not self.responses:
                print("Nenhuma resposta recebida dentro do timeout.")
                return

            # Seleciona o veículo mais próximo
            closest_vehicle = self.select_closest_vehicle()
            if closest_vehicle:
                vehicle_info = self.responses[closest_vehicle]
                print(f"Veículo mais próximo selecionado: {closest_vehicle}")
                await self.send_direct_request(
                    vehicle_id=closest_vehicle,
                    item=vehicle_info["item"],
                    quantidade=vehicle_info["quantidade"],
                )

        def select_closest_vehicle(self):
            min_distance = float("inf")
            closest_vehicle = None

            for vehicle_id, info in self.responses.items():
                position = info["position"]
                distance = abs(position[0] - self.agent.position[0]) + abs(position[1] - self.agent.position[1])
                if distance < min_distance:
                    min_distance = distance
                    closest_vehicle = vehicle_id

            return closest_vehicle

        async def send_direct_request(self, vehicle_id, item, quantidade):
            msg = Message(to=vehicle_id)
            msg.body = f"pedido_confirmado {item} {quantidade} {self.agent.position}"
            msg.set_metadata("performative", "confirm")
            await self.send(msg)
            print(f"Pedido direto enviado para {vehicle_id}.")

    async def setup(self):
        print("Shelter Agent iniciado")

        # Adiciona o comportamento de verificação de recursos
        self.resource_check_behaviour = self.ResourceCheckBehaviour()
        self.add_behaviour(self.resource_check_behaviour)

    def update_resource(self, recurso, quantidade):
        """Atualiza o nível do recurso e libera a solicitação pendente se reabastecido."""
        if recurso == "agua":
            self.agua += quantidade
            self.solicitado["agua"] = False  # Libera nova solicitação quando reabastecido
        elif recurso == "comida":
            self.comida += quantidade
            self.solicitado["comida"] = False
        elif recurso == "medicamentos":
            self.medicamentos += quantidade
            self.solicitado["medicamentos"] = False
        elif recurso == "bens":
            self.bens += quantidade
            self.solicitado["bens"] = False
        print(f"{recurso.capitalize()} atualizado para {getattr(self, recurso)}")