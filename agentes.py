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
            "agua_comida": 200,
            "medicamentos": 100,
            "combustivel": 30
        }

        self.recursos_maximos = {
            "agua_comida": 200,
            "medicamentos": 100,
            "combustivel": 100
        }

        self.entregas_pendentes = {}
        self.ocupado= False


    class SupplyBehaviour(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self.processed_requests = set()  # Rastreia os IDs dos pedidos já processados

        async def run(self):
            print(f"{self.agent.jid} aguardando pedidos de recursos. Ocupado: {self.agent.ocupado}")

            # O veículo só processa novos pedidos se não estiver ocupado
            if self.agent.ocupado:
                print(f"{self.agent.jid} está ocupado, ignorando novos pedidos temporariamente.")
                return

            # Recebe a mensagem de solicitação de recursos via broadcast
            msg = await self.receive(timeout=10)
            if msg:
                origin = msg.get_metadata("origin")

                if msg.get_metadata("performative") == "request" and origin == "shelter":
                    await self.handle_request(msg)

                # Recebe o pedido de confirmação direto do shelter para a entrega
                elif msg.get_metadata("performative") == "confirm" and origin == "shelter":
                    await self.handle_confirmation(msg)

                # Verifica reabastecimento no depósito
                #elif msg.get_metadata("performative") == "confirm" and origin == "depot":
                #    await self.handle_refill(msg)

                elif msg.get_metadata("performative") == "query" and origin == "shelter" and "disponibilidade" in msg.body:
                    await self.handle_disponibility(msg)

        async def handle_request(self, msg):
            """Processa pedidos recebidos do Shelter."""
            parts = msg.body.split()
            unique_id = parts[-1]
            tipo = parts[0]

            if unique_id in self.processed_requests:
                print(f"Pedido já processado com ID {unique_id}: {msg.body}")
                return

            self.processed_requests.add(unique_id)  # Marca o pedido como processado

            if self.agent.ocupado:
                print(f"{self.agent.jid} está ocupado. Ignorando pedido: {msg.body}")
                return

            print(f"Pedido recebido: {msg.body}")

            # Processa pedidos do tipo "duplo" e "simples"
            if tipo == "duplo":
                recurso1, quantidade1 = parts[1], int(parts[2])
                recurso2, quantidade2 = parts[3], int(parts[4])

                # Verifica disponibilidade
                if self.agent.recursos[recurso1] >= quantidade1 and self.agent.recursos[recurso2] >= quantidade2:
                    response = Message(to=str(msg.sender))
                    response.body = f"duplo {self.agent.position} {recurso1} {quantidade1} {recurso2} {quantidade2}"
                    response.set_metadata("performative", "response")
                    await self.send(response)
                    print(f"Resposta enviada: {response.body}")

                if self.agent.recursos[recurso1] >= quantidade1 and self.agent.recursos[recurso2] < quantidade2:
                    response = Message(to=str(msg.sender))
                    # print("RESPONSE: ", response)
                    response.body = f"simples {self.agent.position} {recurso1} {quantidade1}"
                    # print("MSGGGBODYYY SIMPLES: ", response.body)
                    response.set_metadata("performative", "response")
                    await self.send(response)
                    print(f"{self.agent.jid} respondeu ao abrigo com sua posição.")

                if self.agent.recursos[recurso1] < quantidade1 and self.agent.recursos[recurso2] >= quantidade2:
                    response = Message(to=str(msg.sender))
                    # print("RESPONSE: ", response)
                    response.body = f"simples {self.agent.position} {recurso2} {quantidade2}"
                    # print("MSGGGBODYYY SIMPLES: ", response.body)
                    response.set_metadata("performative", "response")
                    await self.send(response)
                    print(f"{self.agent.jid} respondeu ao abrigo com sua posição.")

            elif tipo == "simples":
                recurso, quantidade = parts[1], int(parts[2])
                if self.agent.recursos[recurso] >= quantidade:
                    response = Message(to=str(msg.sender))
                    response.body = f"simples {self.agent.position} {recurso} {quantidade}"
                    response.set_metadata("performative", "response")
                    await self.send(response)
                    print(f"Resposta enviada: {response.body}")

        async def handle_confirmation(self, msg):
            """Processa confirmações de entrega."""
            self.agent.ocupado = True  # Marca como ocupado
            print(f"O agente {self.agent.jid} está ocupado")
            parts = msg.body.split()
            tipo = parts[0]

            if tipo == "confirmar_duplo":
                posicao_shelter = eval(" ".join(parts[1:3]))
                recurso1, quantidade1 = parts[3], int(parts[4])
                recurso2, quantidade2 = parts[5], int(parts[6])
                entregas = [
                    {"recurso": recurso1, "quantidade": quantidade1},
                    {"recurso": recurso2, "quantidade": quantidade2},
                ]
                await self.deliver_supplies(entregas, posicao_shelter, str(msg.sender))

            elif tipo == "confirmar_simples":
                posicao_shelter = eval(" ".join(parts[1:3]))
                recurso, quantidade = parts[3], int(parts[4])
                entregas = [{"recurso": recurso, "quantidade": quantidade}]
                await self.deliver_supplies(entregas, posicao_shelter, str(msg.sender))

            if (self.agent.recursos["combustivel"] <= 2 or self.agent.recursos["agua_comida"] < 30 or
                    self.agent.recursos["medicamentos"] < 10):
                print(
                    f"{self.agent.jid} tem recursos críticos. Indo reabastecer.")
                await self.refill_at_depot()
                self.agent.ocupado = False  # Libera após a entrega
            else:
                self.agent.ocupado = False  # Libera após a entrega

            print(f"o agent {self.agent.jid} está agora livre porque terminou a entrega")


        async def handle_refill(self, msg):
            print(f"Resposta do depósito recebida: {msg.body}")

            # Atualiza os recursos do veículo
            recursos_reabastecidos = eval(msg.body.split(" ", 1)[1])  # Converte de string para dicionário
            for recurso, quantidade in recursos_reabastecidos.items():
                self.agent.recursos[recurso] += quantidade

            print(f"{self.agent.jid} reabastecido: {self.agent.recursos}")

        async def handle_disponibility(self, msg):
            # Extrai a posição do Shelter da mensagem
            parts = msg.body.split()
            shelter_position = tuple(eval(" ".join(parts[1:3])))  # Exemplo: "(2, 3)"

            # Calcula o custo para ir até o Shelter
            path_to_shelter = a_star(self.agent.environment, tuple(self.agent.position), tuple(shelter_position))
            if not path_to_shelter:
                print(f"{self.agent.jid} não encontrou caminho para o Shelter em {shelter_position}.")
                return

            fuel_cost = len(path_to_shelter) - 1  # Cada passo consome 1 unidade de combustível

            # Verifica se o veículo tem combustível suficiente
            if not self.agent.ocupado and self.agent.recursos["combustivel"] > fuel_cost + 2:
                # Responde como disponível se tem combustível suficiente
                reply = Message(to=str(msg.sender))
                reply.body = "disponivel"
                reply.set_metadata("performative", "inform")
                await self.send(reply)
                print(f"{self.agent.jid} informou que está disponível para o Shelter em {shelter_position}.")
            elif self.agent.recursos["combustivel"] <= fuel_cost + 2:
                # Inicia o processo de reabastecimento se o combustível está insuficiente
                print(
                    f"{self.agent.jid} tem combustivel insuficiente para o Shelter em {shelter_position}. Indo reabastecer.")
                await self.refill_at_depot()
            else:
                print(f"{self.agent.jid} está ocupado, ignorando consulta de disponibilidade.")


        async def deliver_supplies(self, entregas, posicao_shelter, shelter_jid):
            """
            Move o veículo até o Shelter e entrega todos os recursos pendentes.
            'entregas' é uma lista de dicionários com os recursos e quantidades a entregar.
            """
            print(f"{self.agent.jid} iniciando entrega para o Shelter em {posicao_shelter}. Recursos: {entregas}")

            # Calcula o caminho até o Shelter
            path = a_star(self.agent.environment, tuple(self.agent.position), tuple(posicao_shelter))
            if not path:
                print(f"{self.agent.jid}: Nenhum caminho encontrado para o Shelter em {posicao_shelter}!")
                return

            # Move o veículo até o Shelter
            for next_position in path[1:]:
                self.agent.environment.move_agent(tuple(self.agent.position), next_position, agent_type=8)
                self.agent.update_position(next_position)
                self.agent.recursos["combustivel"] -= 1

                await asyncio.sleep(1)  # Simula o movimento

            print(f"{self.agent.jid} chegou ao Shelter em {posicao_shelter}. Iniciando entregas.")

            # Processa as entregas
            for entrega in entregas:
                recurso = entrega["recurso"]
                quantidade = entrega["quantidade"]

                if self.agent.recursos[recurso] >= quantidade:
                    self.agent.recursos[recurso] -= quantidade
                    print(f"{self.agent.jid} entregou {quantidade} unidades de {recurso} para o Shelter.")
                else:
                    print(
                        f"{self.agent.jid} não possui {quantidade} unidades de {recurso}. Entrega parcial ou abortada.")

            # Envia confirmações de entrega para o Shelter
            confirm_body = ", ".join(
                [f"{entrega['quantidade']} unidades de {entrega['recurso']}" for entrega in entregas]
            )
            reply = Message(to=shelter_jid)
            reply.body = f"Entrega concluída: {confirm_body}."
            reply.set_metadata("performative", "confirm")
            await self.send(reply)

            print(f"{self.agent.jid}: Entrega concluída para o Shelter em {posicao_shelter}. Confirmação enviada.")

        async def refill_at_depot(self):
            """Move o veículo até o depósito para reabastecimento."""
            depot_position = [0, 0]  # Substitua pela posição real do depósito
            path = a_star(self.agent.environment, tuple(self.agent.position), tuple(depot_position))
            if not path:
                print("Nenhum caminho encontrado para o depósito!")
                return

            # Move o veículo até o depósito
            for next_position in path[1:]:
                if self.agent.environment.is_road_free(next_position):
                    self.agent.environment.move_agent(tuple(self.agent.position), next_position, agent_type=8)
                    self.agent.update_position(next_position)
                    if not self.agent.recursos["combustivel"] <= 0:
                        self.agent.recursos["combustivel"] -= 1
                await asyncio.sleep(1)

            print(f"{self.agent.jid} chegou ao depósito. Solicitando reabastecimento.")

            # Inclui os recursos atuais na mensagem ao depósito
            msg = Message(to="depot@localhost")
            recursos_atual = " ".join(
                [f"{recurso} {quantidade}" for recurso, quantidade in self.agent.recursos.items()])
            msg.body = f"reabastecer {recursos_atual}"
            msg.set_metadata("performative", "request")
            await self.send(msg)

            # Aguarda a resposta do depósito
            reply = await self.receive(timeout=10)
            if reply and reply.get_metadata("performative") == "confirm":
                print(f"Resposta do depósito recebida: {reply.body}")

                # Atualiza os recursos do veículo
                recursos_reabastecidos = eval(reply.body.split(" ", 1)[1])  # Converte de string para dicionário
                for recurso, quantidade in recursos_reabastecidos.items():
                    self.agent.recursos[recurso] += quantidade

                print(f"{self.agent.jid} reabastecido: {self.agent.recursos}")
            else:
                print(f"{self.agent.jid} não conseguiu reabastecer no depósito.")


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
        self.agua_comida = 100
        self.medicamentos = 50
        self.pessoas = 40

        # Limites mínimos para chamar o Vehicle
        self.limite_agua_comida = 30
        self.limite_medicamentos = 10
        self.limite_pessoas = 50

        # Dicionário para rastrear quais recursos já foram solicitados
        self.solicitado = {
            "agua_comida": False,
            "medicamentos": False
        }

        self.resources_pending = {
            "agua_comida": True,
            "medicamentos": True
        }

        # Mensagens já processadas e posições dos veículos
        self.vehicle_positions = {}
        self.processed_messages = set()  # Rastreia mensagens únicas processadas

        self.pending_resources = {
            "agua_comida": 0,
            "medicamentos": 0,
        }

    class ResourceConsumptionBehaviour(CyclicBehaviour):
        async def run(self):
            """Simula o consumo periódico de recursos com base no número de pessoas."""
            taxa_consumo = {
                "agua_comida": 1,  # 1 unidade por pessoa
                "medicamentos": 0.2  # 0.2 unidade por pessoa
            }

            print(f"{self.agent.jid}: Consumo de recursos:")
            for recurso, taxa in taxa_consumo.items():
                consumo_total = taxa * self.agent.pessoas
                setattr(self.agent, recurso, max(0, getattr(self.agent, recurso) - consumo_total))
                print(f"  {recurso}: {getattr(self.agent, recurso)} unidades restantes após consumo.")

            # Aguarda antes de repetir o ciclo
            await asyncio.sleep(10)

    class ResourceCheckBehaviour(CyclicBehaviour):
        async def run(self):
            print("Verificando")
        # Armazena os recursos que precisam ser solicitados em um único pedido
            recursos_necessarios = {}

            # Verifica cada recurso e coleta os que estão abaixo do limite
            for recurso, limite in {
                "agua_comida": self.agent.limite_agua_comida,
                "medicamentos": self.agent.limite_medicamentos
            }.items():
                if getattr(self.agent, recurso) < limite and not self.agent.solicitado[recurso]:
                    quantidade_necessaria = limite - getattr(self.agent, recurso)
                    recursos_necessarios[recurso] = quantidade_necessaria
                    self.agent.solicitado[recurso] = True

            # Se houver recursos necessários, envia um único pedido consolidado
            if recursos_necessarios:
                await self.send_request(recursos_necessarios)

            await asyncio.sleep(5)

        async def check_vehicle_availability(self):
            """Verifica quais veículos estão disponíveis."""
            unique_id = str(uuid.uuid4())  # Gera um ID único para a verificação

            # Envia uma mensagem de verificação para todos os veículos
            for i in range(1, self.agent.max_vehicles + 1):
                vehicle_jid = f"supply_vehicle{i}@localhost"
                msg = Message(to=vehicle_jid)
                msg.body = f"disponibilidade {self.agent.position} {unique_id}"
                msg.set_metadata("origin", "shelter")
                msg.set_metadata("performative", "query")
                await self.send(msg)
                print(f"Verificação de disponibilidade enviada para {vehicle_jid} com ID {unique_id}.")

            # Coleta as respostas
            available_vehicles = []
            start_time = time.time()
            while time.time() - start_time < 5:  # Aguarda até 5 segundos pelas respostas
                reply = await self.receive(timeout=1)
                if reply and reply.get_metadata("performative") == "inform" and "disponivel" in reply.body:
                    print(f"Resposta recebida de {reply.sender}: {reply.body}")
                    available_vehicles.append(str(reply.sender))

            print(f"Veículos disponíveis: {available_vehicles}")
            return available_vehicles

        async def send_request(self, recursos_necessarios):
            available_vehicles = await self.check_vehicle_availability()
            if not available_vehicles:
                print("Nenhum veículo disponível para atender ao pedido.")
                return

            unique_id = str(uuid.uuid4())  # Gera um ID único para cada pedido

            for vehicle_jid in available_vehicles:
                if len(recursos_necessarios) == 2:
                    recursos_formatados = " ".join(
                        [f"{recurso} {quantidade}" for recurso, quantidade in recursos_necessarios.items()])
                    msg = Message(to=vehicle_jid)
                    msg.body = f"duplo {recursos_formatados} {self.agent.position} {unique_id}"
                    msg.set_metadata("origin", "shelter")
                    msg.set_metadata("performative", "request")
                    await self.send(msg)
                    print(f"Pedido duplo enviado para {vehicle_jid}: {recursos_formatados} com ID {unique_id}.")
                else:
                    recurso, quantidade = list(recursos_necessarios.items())[0]
                    msg = Message(to=vehicle_jid)
                    msg.body = f"simples {recurso} {quantidade} {self.agent.position} {unique_id}"
                    msg.set_metadata("origin", "shelter")
                    msg.set_metadata("performative", "request")
                    await self.send(msg)
                    print(f"Pedido simples enviado para {vehicle_jid}: {recurso}:{quantidade} com ID {unique_id}.")

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

            # Recebe e organiza mensagens de resposta
            msg = await self.receive(timeout=1)  # Verifica mensagens com timeout
            #print("MSG: ",msg)
            if msg:
                if msg.get_metadata("performative") == "response":
                    print(f"Resposta recebida de {msg.sender}: {msg.body}")
                    parts = msg.body.split()
                    tipo = parts[0]

                    if tipo == "duplo":
                        # Recolhe a posição, recursos e quantidades para mensagens "duplo"
                        posicao = tuple(eval(" ".join(parts[1:3])))  # Exemplo: "[2, 2]"
                        recurso1 = parts[3]
                        quantidade1 = int(parts[4])
                        recurso2 = parts[5]
                        quantidade2 = int(parts[6])

                        # Adiciona ao dicionário
                        if posicao not in self.collected_responses:
                            self.collected_responses[posicao] = {
                                "tipo": "duplo",
                                "vehicle_id": str(msg.sender),
                                "recursos": []
                            }

                        self.collected_responses[posicao]["recursos"].append(
                            {"recurso": recurso1, "quantidade": quantidade1}
                        )
                        self.collected_responses[posicao]["recursos"].append(
                            {"recurso": recurso2, "quantidade": quantidade2}
                        )

                        #print("Respostas: ", self.collected_responses)

                    elif tipo == "simples":
                        # Recolhe a posição, recurso e quantidade para mensagens "simples"
                        posicao = tuple(eval(" ".join(parts[1:3])))  # Exemplo: "[2, 2]"
                        recurso = parts[3]
                        quantidade = int(parts[4])

                        # Adiciona ao dicionário
                        if posicao not in self.collected_responses:
                            self.collected_responses[posicao] = {
                                "tipo": "simples",
                                "vehicle_id": str(msg.sender),
                                "recursos": []
                            }

                        self.collected_responses[posicao]["recursos"].append(
                            {"recurso": recurso, "quantidade": quantidade}
                        )

                        #print("Respostas: ", self.collected_responses)

                elif msg.get_metadata("performative") == "confirm":
                    # Processar mensagens de confirmação de entrega
                    print(f"Confirmação recebida de {msg.sender}: {msg.body}")
                    parts = msg.body.split(":")[1].strip().split(",")  # Parte com os detalhes da entrega

                    for entrega in parts:
                        quantidade, recurso = entrega.strip().split(" unidades de ")
                        quantidade = int(quantidade)
                        recurso = recurso.strip(".")

                        if hasattr(self.agent, recurso):
                            setattr(self.agent, recurso, getattr(self.agent, recurso) + quantidade)
                            print(f"Atualizado {recurso}: {getattr(self.agent, recurso)} unidades disponíveis.")
                        else:
                            print(f"Recurso desconhecido: {recurso}. Ignorado.")

                        # Marca o recurso como atendido
                        self.agent.resources_pending[recurso] = True
                        self.agent.solicitado[recurso] = False
                        print(f"Recurso {recurso} marcado como disponível para novas solicitações.")

            # Verifica se o tempo de coleta expirou
            if self.response_collection_start and time.time() - self.response_collection_start > 5:
                if self.collected_responses:  # Verifica se não há respostas coletadas
                    print(f"Processando respostas coletadas para os recursos: {list(self.collected_responses.keys())}")
                    #print("Respostas: ", self.collected_responses)
                    best_choice= self.evaluate_best_vehicles()

                    if best_choice["type"] == "duplo":
                        # Seleciona o veículo multirrecursos
                        vehicle = best_choice["vehicle"]
                        print(f"Confirmando entrega com veículo multirrecursos: {vehicle['vehicle_id']}")

                        # Envia confirmação para o veículo selecionado
                        msg = Message(to=vehicle["vehicle_id"])
                        recursos = vehicle["recursos"]  # Lista de recursos
                        posicao_shelter = tuple(self.agent.position)  # Posição do Shelter
                        body = f"confirmar_duplo {posicao_shelter} " + " ".join(
                            [f"{r['recurso']} {r['quantidade']}" for r in recursos]
                        )
                        msg.body = body
                        msg.set_metadata("origin", "shelter")
                        msg.set_metadata("performative", "confirm")
                        await self.send(msg)

                        # Marcar todos os recursos atendidos
                        for recurso in [r["recurso"] for r in recursos]:
                            self.agent.resources_pending[recurso] = False
                        print(f"Recursos atendidos pelo veículo multirrecursos: {vehicle['vehicle_id']}")

                    elif best_choice["type"] == "simples":
                        # Itera sobre os veículos individuais selecionados
                        for recurso, vehicle in best_choice["vehicles"].items():
                            print(
                                f"Confirmando entrega com veículo simples: {vehicle['vehicle_id']} para o recurso {recurso}")

                            # Envia confirmação para cada veículo
                            msg = Message(to=vehicle["vehicle_id"])
                            posicao_shelter = tuple(self.agent.position)  # Posição do Shelter
                            msg.body = f"confirmar_simples {posicao_shelter} {recurso} {vehicle['quantidade']}"
                            msg.set_metadata("origin", "shelter")
                            msg.set_metadata("performative", "confirm")
                            await self.send(msg)

                            # Marca o recurso como atendido
                            self.agent.resources_pending[recurso] = False
                        print("Recursos atendidos pelos veículos simples.")

                self.response_collection_start = None  # Reseta a coleta


        def evaluate_best_vehicles(self):
            best_duplo = None
            best_simples = {}

            # Iterar pelas respostas coletadas
            for posicao, response in self.collected_responses.items():
                vehicle_type = response["tipo"]
                vehicle_id = response["vehicle_id"]
                recursos = response["recursos"]

                # Avaliar veículos do tipo "duplo"
                if vehicle_type == "duplo":
                    total_distance = self.calculate_distance(posicao)  # Exemplo de função
                    total_supply = sum([r["quantidade"] for r in recursos])
                    if best_duplo is None or total_distance < best_duplo["distance"]:
                        best_duplo = {
                            "vehicle_id": vehicle_id,
                            "distance": total_distance,
                            "recursos": recursos,
                        }

                # Avaliar veículos do tipo "simples"
                elif vehicle_type == "simples":
                    for recurso in recursos:
                        tipo_recurso = recurso["recurso"]
                        quantidade = recurso["quantidade"]
                        distance = self.calculate_distance(posicao)  # Exemplo de função

                        # Verificar se o recurso já tem um "melhor" veículo associado
                        if tipo_recurso not in best_simples or distance < best_simples[tipo_recurso]["distance"]:
                            best_simples[tipo_recurso] = {
                                "vehicle_id": vehicle_id,
                                "distance": distance,
                                "quantidade": quantidade,
                            }

            # Avaliar qual solução é melhor: veículo "duplo" ou os veículos "simples"
            efficiency = self.compare_efficiency(best_duplo, best_simples)
            return efficiency

        def calculate_distance(self, posicao):
            """Calcula a distância do veículo até o shelter."""
            shelter_position = tuple(self.agent.position)
            return abs(posicao[0] - shelter_position[0]) + abs(posicao[1] - shelter_position[1])

        def compare_efficiency(self, best_duplo, best_simples):
            """
            Compara a eficiência entre um veículo "duplo" e os veículos "simples".
            Retorna a melhor opção.
            """
            if not best_duplo and not best_simples:
                return None  # Sem opções disponíveis

            if best_duplo:
                duplo_total_distance = best_duplo["distance"]
            else:
                duplo_total_distance = float("inf")

            simples_total_distance = sum([v["distance"] for v in best_simples.values()]) if best_simples else float(
                "inf")

            if duplo_total_distance <= simples_total_distance:
                print("Melhor escolha: veículo duplo que é: ", best_duplo)
                return {"type": "duplo", "vehicle": best_duplo}

            print("Melhor escolha: veículos simples que é: ", best_simples)
            return {"type": "simples", "vehicles": best_simples}


    async def setup(self):
        print("Shelter Agent iniciado")

        # Adiciona o comportamento de verificação de recursos
        self.resource_check_behaviour = self.ResourceCheckBehaviour()
        self.add_behaviour(self.resource_check_behaviour)

        # Adiciona o comportamento de coleta centralizada
        self.response_collector = self.CentralizedResponseCollector()
        self.add_behaviour(self.response_collector)

        #self.response_consumption_behavior = self.ResourceConsumptionBehaviour()
        #self.add_behaviour(self.response_consumption_behavior)

class DepotAgent(Agent):
    def __init__(self, jid, password, position, vehicle_max_resources):
        super().__init__(jid, password)
        self.position = position
        self.vehicle_max_resources = vehicle_max_resources

    class HandleRefillRequestsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg and msg.get_metadata("performative") == "request":
                parts = msg.body.split()
                comando = parts[0]  # O primeiro elemento é o comando, ex.: "reabastecer"

                if comando == "reabastecer":
                    recursos_atual = dict(zip(parts[1::2], map(int, parts[2::2])))  # Converte para um dicionário
                    vehicle_jid = str(msg.sender)

                    # Calcula os recursos necessários para completar o máximo
                    recursos_abastecidos = {}
                    for recurso, maximo in self.agent.vehicle_max_resources.items():
                        atual = recursos_atual.get(recurso, 0)
                        quantidade_abastecida = maximo - atual
                        if quantidade_abastecida > 0:
                            recursos_abastecidos[recurso] = quantidade_abastecida

                    print(f"Depot irá reabastecer {vehicle_jid}: {recursos_abastecidos}")

                    # Envia a resposta ao veículo
                    reply = Message(to=vehicle_jid)
                    reply.body = f"resposta {recursos_abastecidos}"  # Dicionário dos recursos reabastecidos
                    reply.set_metadata("performative", "confirm")
                    reply.set_metadata("origin", "depot")
                    await self.send(reply)

    async def setup(self):
        print(f"Depot iniciado na posição {self.position}.")
        print(f"Limites máximos para veículos: {self.vehicle_max_resources}")
        self.add_behaviour(self.HandleRefillRequestsBehaviour())
