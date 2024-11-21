import random
import time
import uuid

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
import ast  # Para usar ast.literal_eval
import asyncio
from pathfinding import a_star

class ResponderAgent(Agent):
    def __init__(self, jid, password, position, max_responders, environment):
        super().__init__(jid, password)
        self.position = position
        self.environment = environment
        self.ocupado = False  # Estado do agente
        self.candidates = []  # Lista de pedidos analisados
        self.current_request = None  # Pedido atualmente em processamento
        self.max_responders = max_responders
        self.coleta_timer = 0  # Timer para gerenciar a coleta de pedidos


    class ResponderBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.ocupado:
                return
            # Escuta mensagens de civilians do tipo "request"
            msg = await self.receive(timeout=1)  # Reduz o timeout para processar com mais frequência
            if msg and msg.get_metadata("performative") == "request":
                print(f"Pedido recebido: {msg.body}")
                self.process_request(msg)

            # Verifica se está na janela de coleta ou se já é hora de negociar
            if not getattr(self.agent, "negociando", False):
                #print("Entrou")
                if self.agent.coleta_timer == 0:
                    # Inicia o timer de coleta
                    self.agent.coleta_timer = asyncio.get_event_loop().time()
                    print(f"{self.agent.jid}: Janela de coleta iniciada.")

                elapsed_time = asyncio.get_event_loop().time() - self.agent.coleta_timer
                if elapsed_time >= 5:  # 5 segundos para coletar pedidos
                    print(f"{self.agent.jid}: Janela de coleta encerrada. Iniciando negociação.")
                    self.agent.coleta_timer = 0  # Reseta o timer
                    self.agent.negociando = True
                    self.agent.add_behaviour(self.agent.NegotiationBehaviour())

        def process_request(self, msg):
            # Extrai informações do pedido
            parts = msg.body.split()
            #print("Parts: ",parts)
            urgency = int(parts[0])
            position = eval(" ".join(parts[1:3]))  # Converte posição para tuplo
            civilian_id = msg.sender

            # Calcula a distância
            distance = abs(self.agent.position[0] - position[0]) + abs(self.agent.position[1] - position[1])

            # Armazena o pedido analisado
            self.agent.candidates.append({
                "civilian_id": civilian_id,
                "position": position,
                "urgency": urgency,
                "distance": distance
            })

            #print(self.agent.candidates)

    class NegotiationBehaviour(OneShotBehaviour):
        async def run(self):
            print(f"{self.agent.jid} iniciou a negociação com candidatos: {self.agent.candidates}")

            while self.agent.candidates:

                #print("dsadasdaCANDIDDSDADSA: ", self.agent.candidates)

                # Seleciona o pedido mais próximo
                # Filtra os candidatos com a maior urgência
                highest_urgency = max(self.agent.candidates, key=lambda x: x["urgency"], default={"urgency": None})[
                    "urgency"]
                if highest_urgency is None:
                    print("Nenhum pedido restante para negociar.")
                    break

                # Filtra apenas os candidatos com a maior urgência
                urgent_candidates = [c for c in self.agent.candidates if c["urgency"] == highest_urgency]

                # Entre os candidatos com maior urgência, encontra os mais próximos
                min_distance = min(c["distance"] for c in urgent_candidates)
                closest_candidates = [c for c in urgent_candidates if c["distance"] == min_distance]

                # Escolhe aleatoriamente entre os candidatos mais próximos
                best_candidate = random.choice(closest_candidates)
                print(f"Candidato escolhido: {best_candidate}")

                if not best_candidate:
                    print("Nenhum pedido restante para negociar.")
                    break

                # Envia proposta para todos os outros responders
                unique_id = str(uuid.uuid4())  # Gera um ID único para este processo
                for i in range(1, self.agent.max_responders + 1):  # Substituir com o número de responders
                    responder_jid = f"responder{i}@localhost"
                    if str(responder_jid) != str(self.agent.jid):  # Evita enviar para si mesmo
                        msg = Message(to=str(responder_jid))
                        msg.body = f"proposta {best_candidate['civilian_id']} {best_candidate['distance']} {unique_id}"
                        msg.set_metadata("performative", "propose")
                        await self.send(msg)
                        print(f"Proposta enviada para {responder_jid} sobre {best_candidate['civilian_id']} "
                              f"com distância {best_candidate['distance']}.")

                #print("dsadasdaCANDIDDSDADSA: ", self.agent.candidates)

                # Aguarda respostas dos outros responders
                replies = []
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < 5:  # 5 segundos para receber respostas
                    reply = await self.receive(timeout=1)
                    if reply and reply.get_metadata("performative") == "propose-reply":
                        replies.append(reply.body)
                        print(f"Resposta recebida: {reply.body}")

                #print("dsadasdaCANDIDDSDADSA: ", self.agent.candidates)
                # Limpa duplicados após a primeira metade do processo
                unique_candidates = []
                for candidate in self.agent.candidates:
                    if candidate not in unique_candidates:
                        unique_candidates.append(candidate)
                self.agent.candidates = unique_candidates  # Atualiza com a lista sem duplicados

                #print("CANDIDDSDADSA: ", self.agent.candidates)

                # Avalia as respostas
                empates = [r for r in replies if "empate" in r]
                if len(empates) > 0 and len(empates) == len(replies):  # Todos estão em empate
                    print(f"{self.agent.jid}: Empate detectado entre responders. Resolvendo aleatoriamente.")

                    # Gere um número aleatório e compartilhe com outros responders
                    my_random = random.randint(1, 100)
                    print(f"{self.agent.jid}: Meu valor aleatório para desempate: {my_random}")

                    # Envia mensagem de desempate para outros responders
                    for i in range(1, self.agent.max_responders + 1):
                        responder_jid = f"responder{i}@localhost"
                        if responder_jid != str(self.agent.jid):  # Evita enviar para si mesmo
                            msg = Message(to=responder_jid)
                            msg.body = f"desempate {my_random} {best_candidate['civilian_id']}"
                            msg.set_metadata("performative", "resolve-tie")
                            await self.send(msg)

                    # Aguarda mensagens de desempate
                    desempate_replies = []
                    start_time = asyncio.get_event_loop().time()
                    while asyncio.get_event_loop().time() - start_time < 5:  # 5 segundos para receber respostas
                        reply = await self.receive(timeout=1)
                        if reply and reply.get_metadata("performative") == "resolve-tie":
                            desempate_replies.append(int(reply.body.split()[1]))
                            print(f"{self.agent.jid} recebeu valor de desempate: {reply.body}")

                    # Verifica se o responder venceu o desempate
                    all_randoms = desempate_replies + [my_random]
                    if my_random == max(all_randoms):  # Apenas o maior número atende
                        print(f"{self.agent.jid}: Venci o desempate. Atendendo {best_candidate['civilian_id']}.")
                        self.agent.current_request = best_candidate
                        self.agent.add_behaviour(self.agent.ProcessingBehaviour())
                        self.agent.ocupado = True
                        break
                    else:
                        print(f"{self.agent.jid}: Perdi o desempate. Não atenderei {best_candidate['civilian_id']}.")
                        self.agent.candidates.remove(best_candidate)
                        continue  # Tenta o próximo candidato

                # Avalia as respostas
                if any("mais próximo" in r for r in replies):
                    print(
                        f"{self.agent.jid}: Outro responder mais próximo foi escolhido para {best_candidate['civilian_id']}."
                    )
                    #print("CANDIDDSDADSA: ",self.agent.candidates)
                    # Remove o candidato rejeitado
                    self.agent.candidates.remove(best_candidate)
                    print(f"{self.agent.jid}: Reavaliando candidatos restantes: {self.agent.candidates}")
                    continue  # Volta para o próximo candidato

                else:
                    print(f"{self.agent.jid}: Atendendo {best_candidate['civilian_id']}.")
                    self.agent.current_request = best_candidate
                    self.agent.add_behaviour(self.agent.ProcessingBehaviour())
                    self.agent.ocupado=True
                    break

            # Finaliza negociação
            print(f"{self.agent.jid}: Negociação finalizada.")
            self.agent.negociando = False
            self.agent.candidates = []  # Limpa o buffer de candidatos
            self.agent.coleta_timer = 0  # Permite uma nova rodada de coleta

    class ProcessingBehaviour(OneShotBehaviour):
        async def run(self):
            pedido = self.agent.current_request
            if not pedido:
                print("Nenhum pedido para processar.")
                return

            civilian_id = pedido["civilian_id"]
            position = tuple(pedido["position"])

            print(f"{self.agent.jid}: A caminho do Civilian {civilian_id}...")

            # Envia mensagem para notificar o Civilian que o pedido está "em progresso"
            progress_msg = Message(to=str(civilian_id))
            progress_msg.body = "in_progress"
            progress_msg.set_metadata("performative", "inform")
            await self.send(progress_msg)
            print(f"{self.agent.jid}: Notificou {civilian_id} que o pedido está em progresso.")


            path = self.agent.calculate_path(pedido["position"])
            if not path:
                print(f"{self.agent.jid} não conseguiu calcular o caminho para {pedido['civilian_id']}.")
                self.agent.ocupado = False
                return

            # Segue o caminho até o Civilian
            await self.agent.follow_path(path, tuple(pedido["position"]))
            print(f"{self.agent.jid} chegou ao Civilian {pedido['civilian_id']}. Pedido concluído.")

            # Envia uma mensagem de confirmação para o Civilian
            msg = Message(to=str(pedido["civilian_id"]))
            msg.body = "atendido"
            msg.set_metadata("performative", "inform")
            await self.send(msg)
            print(f"{self.agent.jid} informou {pedido['civilian_id']} que o pedido foi atendido.")

            # Etapa de transporte para o Shelter
            print(f"{self.agent.jid}: Solicitando disponibilidade de Shelters para transportar {civilian_id}.")
            # Envia mensagem para todos os Shelters
            shelter_replies = []
            shelter_positions = {}
            for i in range(1, self.agent.max_responders + 1):  # Substitua por max_shelters ou similar
                shelter_jid = f"shelter{i}@localhost"
                shelter_msg = Message(to=shelter_jid)
                shelter_msg.body = f"solicitação {civilian_id} posição {position}"
                shelter_msg.set_metadata("performative", "query")
                await self.send(shelter_msg)
                print(f"{self.agent.jid}: Enviou solicitação de transporte para {shelter_jid}.")

            # Aguarda respostas dos Shelters
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 5:  # Espera até 5 segundos
                reply = await self.receive(timeout=1)
                if reply and reply.get_metadata("performative") == "inform":
                    shelter_replies.append(reply.body)
                    shelter_position = eval(" ".join(reply.body.split()[1:3]))  # Extrai a posição do Shelter
                    shelter_positions[tuple(shelter_position)] = str(reply.sender)  # Mapeia a posição ao JID
                    print(f"Resposta recebida de {reply.sender}: {reply.body}")

            if not shelter_replies:
                print(f"{self.agent.jid}: Nenhuma resposta de Shelters. Concluindo sem transporte.")
                self.agent.ocupado = False
                return

            # Escolhe o Shelter mais próximo com base nas respostas
            best_shelters = []
            min_distance = float("inf")
            for shelter_info in shelter_replies:
                parts = shelter_info.split()  # Supõe que posição está no corpo da mensagem
                shelter_position = eval(" ".join(parts[1:3]))


                distance = abs(self.agent.position[0] - shelter_position[0]) + abs(
                    self.agent.position[1] - shelter_position[1])

                # Atualiza a lista de melhores shelters
                if distance < min_distance:
                    min_distance = distance
                    best_shelters = [shelter_position]  # Reinicia a lista com o novo menor
                elif distance == min_distance:
                    best_shelters.append(shelter_position)  # Adiciona ao empate

            if not best_shelters:
                print(f"{self.agent.jid}: Nenhum Shelter adequado encontrado.")
                self.agent.ocupado = False
                return

            best_shelter = random.choice(best_shelters)
            best_shelter_jid = shelter_positions[tuple(best_shelter)]
            print(f"{self.agent.jid}: Levando {civilian_id} para o Shelter em {best_shelter}.")

            # Calcula o caminho até o Shelter
            path_to_shelter = self.agent.calculate_path(best_shelter)
            if not path_to_shelter:
                print(f"{self.agent.jid} não conseguiu calcular o caminho para o Shelter em {best_shelter}.")
                self.agent.ocupado = False
                return

            # Segue o caminho até o Shelter
            await self.agent.follow_path(path_to_shelter, tuple(best_shelter))
            print(f"{self.agent.jid}: Chegou ao Shelter em {best_shelter}. Transporte concluído.")

            # Envia confirmação ao Shelter
            shelter_msg = Message(to=str(best_shelter_jid))  # 'jid' deve estar no dicionário do Shelter
            shelter_msg.body = "confirm"
            shelter_msg.set_metadata("performative", "inform")
            shelter_msg.set_metadata("origin", "responder")  # Indica que a origem é um responder
            await self.send(shelter_msg)
            print(f"{self.agent.jid}: Confirmação enviada ao Shelter {best_shelter_jid}.")

            # Atualiza o estado e limpa o pedido atual
            self.agent.current_request = None
            self.agent.ocupado = False

    class HandleProposalsBehaviour(CyclicBehaviour):
        async def run(self):
            # Escuta propostas de outros responders
            msg = await self.receive(timeout=5)
            if msg and msg.get_metadata("performative") == "propose":
                print(f"{self.agent.jid} recebeu proposta: {msg.body}")
                await self.process_proposal(msg)

        async def process_proposal(self, msg):
            # Extrai os dados da proposta
            parts = msg.body.split()
            civilian_id = parts[1]
            distance = int(parts[2])
            unique_id = parts[3]

            #print("SELF AGENT CANDIDATES: ",self.agent.candidates)

            #print("Civilian ID: ", civilian_id)

            # Calcula a distância deste responder ao pedido
            my_distance = min([c["distance"] for c in self.agent.candidates if str(c["civilian_id"]) == civilian_id],
                              default=None)

            #print("MY DISTANCE: ", my_distance)
            #print("DISTANCE: ", distance)

            # Decide se responde com "mais próximo" ou "proposta rejeitada"
            if my_distance is not None and my_distance < distance:
                response = "mais próximo"

            if my_distance == distance:
                response = "empate"

            else:
                response = "proposta rejeitada"

            # Envia a resposta de volta ao remetente
            reply = Message(to=str(msg.sender))
            reply.body = response
            reply.set_metadata("performative", "propose-reply")
            await self.send(reply)
            print(f"{self.agent.jid} enviou resposta: {response} para {msg.sender}.")

    def calculate_path(self, target_position):
        """Calcula o caminho até a posição alvo usando A*."""
        path = a_star(self.environment, tuple(self.position), tuple(target_position))
        return path

    async def follow_path(self, path, target_position):
        """Segue o caminho calculado até a posição alvo."""
        for next_position in path[1:]:
            if next_position == target_position:
                self.environment.move_agent(tuple(self.position), next_position, self.environment.city_map[target_position[0]][target_position[1]])
                self.update_position(next_position)
                print(f"{self.jid} chegou ao civilian.")

            elif self.environment.is_road_free(next_position):
                self.environment.move_agent(tuple(self.position), next_position, agent_type=3)
                self.update_position(next_position)
                print(f"{self.jid} movido para {next_position}.")

            else:
                print(f"Caminho bloqueado em {next_position}. Recalculando...")
                path = self.calculate_path(target_position)
                if not path:
                    print(f"{self.jid} não conseguiu recalcular o caminho!")
                    return
                await self.follow_path(path, target_position)
                return
            await asyncio.sleep(1)



    async def setup(self):
        print(f"Responder Agent iniciado na posição {self.position}.")
        self.add_behaviour(self.ResponderBehaviour())
        self.add_behaviour(self.HandleProposalsBehaviour())

    def update_position(self, new_position):
        self.position = new_position


class CivilianAgent(Agent):
    def __init__(self, jid, password, position, urgency, max_responders):
        super().__init__(jid, password)
        self.position = position
        self.urgency = urgency
        self.max_responders = max_responders
        self.attended = False  # Estado de atendimento
        self.in_progress = False  # Estado de pedido em progresso

    class SendHelpRequestBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.attended or self.agent.in_progress:
                return  # Não envia novos pedidos se já está a ser atendido ou em progresso

            # Gera um pedido de socorro
            urgency = self.agent.urgency
            position = self.agent.position
            unique_id = str(uuid.uuid4())  # ID único para o pedido

            # Envia para todos os responders
            for i in range(1, self.agent.max_responders + 1):
                responder_jid = f"responder{i}@localhost"
                msg = Message(to=str(responder_jid))
                msg.body = f"{urgency} {position} {unique_id}"
                msg.set_metadata("performative", "request")
                await self.send(msg)
                print(f"{self.agent.jid} enviou pedido de socorro para {responder_jid}. Urgência: {urgency}.")

            await asyncio.sleep(10)  # Espera antes de reenviar

    class UpdateStateBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.attended or self.agent.in_progress:
                return  # Civilian já foi atendido

            self.agent.in_progress = True
            # Aguarda uma mensagem do responder
            msg = await self.receive(timeout=5)
            if not msg or msg.get_metadata("performative") != "inform":
                self.agent.in_progress = False
                return  # Ignora mensagens irrelevantes

            if msg.body == "in_progress":
                print(f"{self.agent.jid}: Pedido em progresso. Responder {msg.sender} a caminho.")
                self.agent.in_progress = True  # Atualiza o estado para "em progresso"
                return

            if msg.body == "atendido":
                print(f"{self.agent.jid}: Pedido atendido por {msg.sender}.")
                self.agent.attended = True  # Atualiza o estado para "atendido"
                self.agent.in_progress = False  # Libera o estado "em progresso"


    async def setup(self):
        print(f"{self.jid} iniciado na posição {self.position} com urgência {self.urgency}.")
        self.add_behaviour(self.SendHelpRequestBehaviour())
        self.add_behaviour(self.UpdateStateBehaviour())

    def update_position(self, new_position):
        self.position = new_position
        print(f"{self.jid} movido para {self.position}")


class SupplyVehicleAgent(Agent):
    def __init__(self, jid, password, position, environment):
        super().__init__(jid, password)
        self.position = position
        self.environment = environment
        self.combustivel_consumido = 0

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

            if (self.agent.recursos["combustivel"] <= 2 or self.agent.recursos["agua_comida"] < 51 or
                    self.agent.recursos["medicamentos"] < 21):
                print(
                    f"{self.agent.jid} tem recursos críticos. Indo reabastecer.")
                await self.refill_at_depot()
                self.agent.ocupado = False  # Libera após a entrega
            else:
                self.agent.ocupado = False  # Libera após a entrega

            print(f"o agent {self.agent.jid} está agora livre porque terminou a entrega")

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

            path = self.agent.calculate_path(posicao_shelter)
            if not path:
                print(f"Não foi possível encontrar caminho para o Depot.")
                return

            # Move até o Civilian
            await self.agent.follow_path(path, tuple(posicao_shelter))

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

            path = self.agent.calculate_path(depot_position)
            if not path:
                print(f"Não foi possível encontrar caminho para o Depot.")
                return

            # Move até o Civilian
            await self.agent.follow_path(path, tuple(depot_position))

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

    async def follow_path(self, path, target_position):
        """Segue o caminho calculado até a posição alvo."""
        for next_position in path[1:]:
            if next_position == target_position:
                self.environment.move_agent(tuple(self.position), next_position, self.environment.city_map[target_position[0]][target_position[1]])
                self.update_position(next_position)
                print(f"{self.jid} chegou ao civilian.")
                if self.recursos["combustivel"] > 0:
                    self.combustivel_consumido += 1
                    self.recursos["combustivel"]-=1

            elif self.environment.is_road_free(next_position):
                self.environment.move_agent(tuple(self.position), next_position, agent_type=7)
                self.update_position(next_position)
                print(f"{self.jid} movido para {next_position}.")
                if self.recursos["combustivel"] > 0:
                    self.combustivel_consumido += 1
                    self.recursos["combustivel"]-=1

            else:
                print(f"Caminho bloqueado em {next_position}. Recalculando...")
                path = self.calculate_path(target_position)
                if not path:
                    print(f"{self.jid} não conseguiu recalcular o caminho!")
                    return
                await self.follow_path(path, target_position)
                return
            await asyncio.sleep(1)

    def calculate_path(self, target_position):
        """Calcula o caminho até a posição alvo usando A*."""
        path = a_star(self.environment, tuple(self.position), tuple(target_position))
        return path

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
        self.agua_comida = 200
        self.medicamentos = 50
        self.pessoas = 0

        # Limites mínimos para chamar o Vehicle
        self.limite_agua_comida = 150
        self.limite_medicamentos = 30
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
                "agua_comida": 0.7,  # 1 unidade por pessoa
                "medicamentos": 0.2  # 0.2 unidade por pessoa
            }

            print(f"{self.agent.jid}: Consumo de recursos:")
            for recurso, taxa in taxa_consumo.items():
                consumo_total = int(taxa * self.agent.pessoas)
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

            if msg and msg.get_metadata("performative") == "query" and self.agent.pessoas < 50:
                reply = Message(to=str(msg.sender))
                reply.body = f"disponível {self.agent.position}"
                reply.set_metadata("performative", "inform")
                await self.send(reply)
                print(f"{self.agent.jid}: Respondeu a {msg.sender} com posição {self.agent.position}.")

            if msg and msg.get_metadata("performative") == "inform" and msg.get_metadata("origin") == "responder":
                self.agent.pessoas += 1
                print(f"{self.agent.jid}: Pessoa adicionada. Total de pessoas: {self.agent.pessoas}.")

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

        self.response_consumption_behavior = self.ResourceConsumptionBehaviour()
        self.add_behaviour(self.response_consumption_behavior)

class DepotAgent(Agent):
    def __init__(self, jid, password, position, vehicle_max_resources):
        super().__init__(jid, password)
        self.position = position
        self.vehicle_max_resources = vehicle_max_resources
        self.recursos_distribuidos = {"medicamentos": 0, "agua_comida": 0}


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

                            if recurso in self.agent.recursos_distribuidos:
                                self.agent.recursos_distribuidos[recurso] += quantidade_abastecida

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
