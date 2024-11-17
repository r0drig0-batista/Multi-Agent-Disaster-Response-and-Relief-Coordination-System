import time
import uuid

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
            "bens": 100,
            "combustivel": 30
        }

    class SupplyBehaviour(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self.processed_requests = set()  # Rastreia os IDs dos pedidos já processados

        async def run(self):
            print("Supply Vehicle aguardando pedidos de recursos...")

            # Recebe a mensagem de solicitação de recursos via broadcast
            msg = await self.receive(timeout=10)
            if msg:

                origin = msg.get_metadata("origin")

                if msg.get_metadata("performative") == "request":
                    parts = msg.body.split()
                    unique_id = parts[-1]  # O último elemento é o ID

                    if unique_id in self.processed_requests:
                        print(f"Pedido já processado com ID {unique_id}: {msg.body}")
                        return  # Ignora pedidos duplicados

                    self.processed_requests.add(unique_id)  # Marca o pedido como processado
                    print(f"Pedido de {origin} recebido: {msg.body}")

                    # Extrai o tipo e quantidade do recurso solicitado
                    try:
                        recurso, quantidade, posicao = self.parse_request(msg.body)
                        print(f"Pedido de {quantidade} unidades de {recurso} vindo de {origin} em {posicao}")

                        # Lógica para o pedido do abrigo (Shelter)
                        if origin == "shelter":
                            if self.agent.recursos[recurso] >= quantidade:
                                response = Message(to=str(msg.sender))
                                response.body = f"resposta {self.agent.position} {recurso} {quantidade}"
                                response.set_metadata("performative", "response")
                                await self.send(response)
                                print(f"{self.agent.jid} respondeu ao abrigo com sua posição.")

                    except Exception as e:
                            print(f"Erro ao processar o pedido: {e}")

                # Recebe o pedido de confirmação direto do shelter para a entrega
                if msg.get_metadata("performative") == "confirm":
                    if origin == "depot":
                        parts = msg.body.split()
                        print("Parts: ", parts)
                        recurso = parts[1]  # O último elemento é o ID
                        quantidade = int(parts[2])
                        self.agent.recursos[recurso] += quantidade
                        print("Recurso de combustivel: ", self.agent.recursos["combustivel"])

                    if origin == "shelter":
                        recurso, quantidade, posicao_shelter = self.parse_request(msg.body)
                        print(f"{self.agent.jid} recebeu confirmação para entregar {quantidade} de {recurso}.")
                        await self.deliver_supplies(recurso, quantidade, posicao_shelter, str(msg.sender))

        def parse_request(self, body):
            """Extrai o tipo de recurso, quantidade e posição do Shelter da mensagem."""
            try:
                parts = body.split()
                print("PARTS: " ,parts)
                recurso = parts[1]  # Segundo elemento é o recurso
                quantidade = int(parts[2])  # Terceiro elemento é a quantidade
                position_str = f"{parts[3]} {parts[4]}"
                shelter_position = eval(position_str)
                return recurso, quantidade, shelter_position
            except Exception as e:
                raise ValueError(f"Erro ao interpretar a mensagem: {e}")

        async def deliver_supplies(self, recurso, quantidade, posicao_shelter, shelter_jid):
            """Move o vehicle até o shelter e entrega o recurso."""
            if self.agent.recursos["combustivel"] <= 2:
                print(f"{self.agent.jid} com combustível baixo. Retornando ao depósito para reabastecimento.")
                await self.refill_at_depot()
                return

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
                    self.agent.recursos["combustivel"] -= 1
                    break

                if self.agent.environment.is_road_free(next_position):
                    self.agent.environment.move_agent(tuple(self.agent.position), next_position,
                                                      agent_type=8)  # Representando o Vehicle
                    self.agent.update_position(next_position)
                    self.agent.recursos["combustivel"] -= 1
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
            #print("recursos depois de perder", self.agent.recursos[recurso])

            # Envia confirmação de entrega para o Shelter
            reply = Message(to=shelter_jid)
            reply.body = f"Entrega de {quantidade} unidades de {recurso} realizada."
            reply.set_metadata("performative", "confirm")
            await self.send(reply)

        async def refill_at_depot(self):
            """Move o veículo até o depósito para reabastecimento."""
            depot_position = [0, 0]  # Substitua pela posição real do depósito
            path = a_star(self.agent.environment, tuple(self.agent.position), tuple(depot_position))
            if not path:
                print("Nenhum caminho encontrado para o depósito!")
                return

            for next_position in path[1:]:
                if self.agent.environment.is_road_free(next_position):
                    self.agent.environment.move_agent(tuple(self.agent.position), next_position, agent_type=8)
                    self.agent.update_position(next_position)
                    self.agent.recursos["combustivel"] -= 1
                await asyncio.sleep(1)

            print(f"{self.agent.jid} chegou ao depósito. Solicitando reabastecimento.")
            msg = Message(to="depot@localhost")
            msg.body = f"request combustivel {30}"  # Exemplo de solicitação
            msg.set_metadata("performative", "request")
            await self.send(msg)

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

        self.resources_pending = {
            "agua": True,
            "comida": True,
            "medicamentos": True,
            "bens": True
        }

        # Mensagens já processadas e posições dos veículos
        self.vehicle_positions = {}
        self.processed_messages = set()  # Rastreia mensagens únicas processadas

    class ResourceCheckBehaviour(CyclicBehaviour):
        async def run(self):
            print("Verificando níveis de recursos...")

            # Verifica cada recurso e envia pedidos se necessário
            for recurso, limite in {
                "agua": self.agent.limite_agua,
                "comida": self.agent.limite_comida,
                "medicamentos": self.agent.limite_medicamentos,
                "bens": self.agent.limite_bens
            }.items():
                if getattr(self.agent, recurso) < limite and not self.agent.solicitado[recurso]:
                    print(f"Recurso {recurso} abaixo do limite. Enviando pedido.")
                    self.agent.solicitado[recurso] = True
                    await self.send_request(recurso, limite - getattr(self.agent, recurso))

            await asyncio.sleep(5)

        async def send_request(self, recurso, quantidade):
            """Envia pedidos de recurso para todos os veículos."""
            print(f"Enviando pedido de {recurso} ({quantidade} unidades).")
            unique_id = str(uuid.uuid4())  # Gera um ID único para cada pedido

            for i in range(1, self.agent.max_vehicles + 1):
                vehicle_jid = f"supply_vehicle{i}@localhost"
                msg = Message(to=vehicle_jid)
                msg.body = f"pedido {recurso} {quantidade} {self.agent.position} {unique_id}"  # Inclui o ID único
                msg.set_metadata("origin", "shelter")  # Para pedidos do Shelter
                msg.set_metadata("performative", "request")
                await self.send(msg)
                print(f"Pedido de {recurso} enviado para {vehicle_jid} com ID {unique_id}.")

    class CentralizedResponseCollector(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self.response_collection_start = None
            self.collected_responses = {}

        async def run(self):
            """Coleta e organiza respostas temporariamente."""
            if not self.response_collection_start:
                # Inicia a coleta quando necessário
                self.response_collection_start = time.time()
                self.collected_responses = {}

            """Recebe e organiza mensagens de resposta."""
            msg = await self.receive(timeout=1)  # Verifica mensagens com timeout
            #print("MSG: ", msg)
            if msg:
                #print("Recebu msg: ", msg.body)
                # Processar mensagem de confirmação
                if msg.get_metadata("performative") == "confirm":
                    print(f"Confirmação recebida de {msg.sender}: {msg.body}")
                    parts = msg.body.split()
                    #print("PARTS: ",parts)
                    quantidade = int(parts[2])
                    recurso = parts[5]
                    self.agent.update_resource(recurso, quantidade)
                    print(f"Recursos atualizados após confirmação de {msg.sender}.")
                    return

                # Processar mensagens de resposta
                if msg.get_metadata("performative") == "response":
                    # Verifica se a mensagem já foi processada
                    if msg.body in self.agent.processed_messages:
                        print(f"[DEBUG] Mensagem duplicada ignorada: {msg.body}")
                        return

                    # Adiciona a mensagem ao conjunto de mensagens processadas
                    self.agent.processed_messages.add(msg.body)

                    # Processa a mensagem
                    parts = msg.body.split()
                    position_str = f"{parts[1]} {parts[2]}"
                    vehicle_position = eval(position_str)
                    recurso = parts[3]
                    quantidade = int(parts[4])

                    #print("Estado do recurso: ", self.agent.resources_pending.get(recurso))

                    if not self.agent.resources_pending.get(recurso, False):
                        print(f"Recurso {recurso} já foi atendido. Ignorando resposta.")
                        return

                    if recurso not in self.collected_responses:
                        self.collected_responses[recurso] = []

                    self.collected_responses[recurso].append({
                        "vehicle_id": str(msg.sender),
                        "position": vehicle_position,
                        "quantidade": quantidade,
                    })
                    #print(f"Resposta recebida e registrada: {msg.body}")

                    # Processar a melhor resposta diretamente

            # Verifica se o tempo de coleta expirou (ex.: 5 segundos)
            if self.response_collection_start and time.time() - self.response_collection_start > 10:
                if self.collected_responses:  # Verifica se não há respostas coletadas
                    print(f"Processando respostas coletadas para os recursos: {list(self.collected_responses.keys())}")
                    await self.process_responses()
                self.response_collection_start = None  # Reseta a coleta

        async def process_responses(self):

            # Imprime as respostas coletadas para análise
            #print(f"Respostas coletadas para {recurso}: {responses}")
            #print("COLLECTED: ", self.collected_responses)

            # Identificar veículos multirrecursos
            multi_resource_vehicles = self.find_multi_resource_vehicles()

            print(f"Veículos multirrecursos encontrados: {multi_resource_vehicles}")
            best_choice = self.evaluate_efficiency(multi_resource_vehicles, self.collected_responses)

            print("BEST CHOICE: ", best_choice)

            if best_choice["type"] == "multi":
                vehicle = best_choice["vehicle"]
                print(f"Usando veículo multirrecursos: {vehicle['vehicle_id']}")

                # Enviar pedidos separados para cada recurso atendido pelo veículo multirrecursos
                for res in vehicle["recursos"]:
                    #print("RESSSSSS: ", res)
                    quantidade = self.collected_responses[res][0][
                        "quantidade"]  # Usa a quantidade solicitada para o recurso
                    await self.send_direct_request(
                        vehicle_id=vehicle["vehicle_id"],
                        item=res,
                        quantidade=quantidade,
                    )
                    # Marca o recurso como atendido
                    self.agent.resources_pending[res] = False
                    print(f"Recurso {res} marcado como atendido pelo veículo multirrecursos.")
                return

            if best_choice["type"] == "separate":
                print("Usando veículos separados para atender os recursos.")

                # Itera sobre os veículos selecionados para cada recurso
                for vehicle in best_choice["vehicles"]:
                    # Extrai o recurso associado ao veículo (se houver um campo específico para isso)
                    resource = next((res for res, responses in self.collected_responses.items()
                                     if any(v["vehicle_id"] == vehicle["vehicle_id"] for v in responses)), None)

                    if resource:
                        quantidade = vehicle["quantidade"]  # Usa a quantidade fornecida pelo veículo
                        await self.send_direct_request(
                            vehicle_id=vehicle["vehicle_id"],
                            item=resource,
                            quantidade=quantidade,
                        )
                        # Marca o recurso como atendido
                        self.agent.resources_pending[resource] = False
                        print(f"Recurso {resource} marcado como atendido pelo veículo {vehicle['vehicle_id']}.")
                    else:
                        print(f"Recurso não encontrado para o veículo {vehicle['vehicle_id']}.")

        def find_multi_resource_vehicles(self):
            """
            Identifica veículos que aparecem em mais de um recurso.
            Retorna uma lista de veículos multirrecursos e os recursos atendidos.
            """
            vehicle_resource_map = {}

            # Itera por cada recurso e seus veículos associados
            for recurso, vehicles in self.collected_responses.items():
                for vehicle in vehicles:
                    vehicle_id = vehicle["vehicle_id"]
                    if vehicle_id not in vehicle_resource_map:
                        vehicle_resource_map[vehicle_id] = []
                    vehicle_resource_map[vehicle_id].append(recurso)

            # Filtra veículos que atendem a mais de um recurso
            multi_resource_vehicles = [
                {"vehicle_id": vehicle_id, "recursos": recursos}
                for vehicle_id, recursos in vehicle_resource_map.items()
                if len(recursos) > 1
            ]

            return multi_resource_vehicles

        def evaluate_efficiency(self, multi_resource_vehicles, collected_responses):
            """
            Compara a eficiência de usar veículos multirrecursos contra veículos separados.
            Retorna a melhor opção.
            """
            best_choice = None
            min_distance = float("inf")

            # Opção 1: Usar veículos multirrecursos
            for vehicle in multi_resource_vehicles:
                vehicle_id = vehicle["vehicle_id"]
                distance = self.calculate_distance(vehicle_id)

                # Soma a quantidade de recursos atendidos como um fator de eficiência
                efficiency_score = distance / len(vehicle["recursos"])

                if efficiency_score < min_distance:
                    min_distance = efficiency_score
                    best_choice = {"type": "multi", "vehicle": vehicle}

            # Opção 2: Usar veículos separados para cada recurso
            separate_vehicles = []
            total_distance = 0

            for recurso, vehicles in collected_responses.items():
                closest_vehicle = self.select_closest_vehicle(vehicles)
                if closest_vehicle:
                    separate_vehicles.append(closest_vehicle)
                    total_distance += self.calculate_distance(closest_vehicle["vehicle_id"])

            if total_distance < min_distance:
                best_choice = {"type": "separate", "vehicles": separate_vehicles}

            return best_choice

        def calculate_distance(self, vehicle_id):
            """Calcula a distância entre o abrigo e um veículo."""
            for recurso, vehicles in self.collected_responses.items():
                for vehicle in vehicles:
                    if vehicle["vehicle_id"] == vehicle_id:
                        position = vehicle["position"]
                        return abs(position[0] - self.agent.position[0]) + abs(position[1] - self.agent.position[1])
            return float("inf")

        def select_closest_vehicle(self, vehicles):
            """Seleciona o veículo mais próximo."""
            min_distance = float("inf")
            closest_vehicle = None

            for vehicle in vehicles:
                position = vehicle["position"]
                distance = abs(position[0] - self.agent.position[0]) + abs(position[1] - self.agent.position[1])
                if distance < min_distance:
                    min_distance = distance
                    closest_vehicle = vehicle

            return closest_vehicle

        async def send_direct_request(self, vehicle_id, item, quantidade):
            """Envia uma mensagem direta ao veículo selecionado."""

            print("VehicleID: ", vehicle_id)
            print("item: ", item)
            print("quantidade: ", quantidade)

            msg = Message(to=vehicle_id)
            msg.body = f"pedido_confirmado {item} {quantidade} {self.agent.position}"
            msg.set_metadata("performative", "confirm")
            msg.set_metadata("origin", "shelter")  # Para pedidos do Shelter
            await self.send(msg)
            print(f"Pedido direto enviado para {vehicle_id}.")


    async def setup(self):
        print("Shelter Agent iniciado")

        # Adiciona o comportamento de verificação de recursos
        self.resource_check_behaviour = self.ResourceCheckBehaviour()
        self.add_behaviour(self.resource_check_behaviour)

        # Adiciona o comportamento de coleta centralizada
        self.response_collector = self.CentralizedResponseCollector()
        self.add_behaviour(self.response_collector)

    def update_resource(self, recurso, quantidade):
        """Atualiza o nível do recurso e libera a solicitação pendente se reabastecido."""
        if recurso == "agua":
            print("agua: ", self.agua)
            self.agua += quantidade
            self.solicitado["agua"] = False  # Libera nova solicitação quando reabastecido
            self.resources_pending["agua"] = True
            #print("Atualizou")
        elif recurso == "comida":
            print("comida: ", self.comida)
            self.comida += quantidade
            self.solicitado["comida"] = False
            self.resources_pending["comida"] = True
        elif recurso == "medicamentos":
            self.medicamentos += quantidade
            self.solicitado["medicamentos"] = False
            self.resources_pending["medicamentos"] = True
        elif recurso == "bens":
            self.bens += quantidade
            self.solicitado["bens"] = False
            self.resources_pending["bens"] = True
        print(f"{recurso.capitalize()} atualizado para {getattr(self, recurso)}")

class DepotAgent(Agent):
    def __init__(self, jid, password, position, initial_resources):
        super().__init__(jid, password)
        self.position = position
        self.resources = initial_resources  # {"agua": 500, "comida": 500, ...}

    class HandleRefillRequestsBehaviour(CyclicBehaviour):
        async def run(self):
            print("Depot aguardando solicitações de reabastecimento...")

            msg = await self.receive(timeout=1)
            if msg and msg.get_metadata("performative") == "request":
                parts = msg.body.split()
                recurso = parts[1]
                quantidade = int(parts[2])
                vehicle_jid = str(msg.sender)

                if self.agent.resources[recurso] >= quantidade:
                    self.agent.resources[recurso] -= quantidade
                    print(f"Depot forneceu {quantidade} de {recurso} para {vehicle_jid}.")

                    reply = Message(to=vehicle_jid)
                    reply.body = f"resposta {recurso} {quantidade} fornecidos."
                    reply.set_metadata("performative", "confirm")
                    reply.set_metadata("origin", "depot")  # Para pedidos do Depot
                    await self.send(reply)
                else:
                    print(f"Depot sem recursos suficientes de {recurso}.")
                    reply = Message(to=vehicle_jid)
                    reply.body = f"Recursos insuficientes de {recurso}."
                    reply.set_metadata("performative", "refuse")
                    reply.set_metadata("origin", "depot")  # Para pedidos do Depot
                    await self.send(reply)

    async def setup(self):
        print(f"Depot iniciado na posição {self.position}. Recursos iniciais: {self.resources}")
        self.add_behaviour(self.HandleRefillRequestsBehaviour())

