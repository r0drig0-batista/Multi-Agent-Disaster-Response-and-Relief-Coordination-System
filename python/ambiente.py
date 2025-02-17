import random
import pygame

class Environment:
    def __init__(self, size):
        self.city_size = size
        self.city_map = [[1 for _ in range(self.city_size)] for _ in range(self.city_size)]  # 1 = estrada livre
        self.cell_size = 50  # Tamanho de cada célula no grid
        self.screen = pygame.display.set_mode((self.city_size * self.cell_size, self.city_size * self.cell_size))
        self.colors = {
            1: (255, 255, 255),  # Estrada livre
            #0: (0, 0, 0),  # Bloqueio
            #2: (0, 255, 0),  # Civilians
            #3: (255, 0, 0),  # Responders
            #4: (139, 69, 19),  # Prédios
            #5: (0, 0, 255),  # Abrigos
            #7: (255, 255, 0),  # Veículos de suprimento
            #9: (128, 128, 128),  # Outros
        }
        self.images = {
            2: pygame.transform.scale(pygame.image.load('civilian.jpg'), (self.cell_size, self.cell_size)),
            3: pygame.transform.scale(pygame.image.load('firefighter.jpg'), (self.cell_size, self.cell_size)),
            4: pygame.transform.scale(pygame.image.load('building.png'), (self.cell_size, self.cell_size)),
            0: pygame.transform.scale(pygame.image.load('rocks.png'), (self.cell_size, self.cell_size)),
            5: pygame.transform.scale(pygame.image.load('shelter.png'), (self.cell_size, self.cell_size)),
            7: pygame.transform.scale(pygame.image.load('supply.jpg'), (self.cell_size, self.cell_size)),
            9: pygame.transform.scale(pygame.image.load('depot.jpg'), (self.cell_size, self.cell_size))
        }
    '''''  
    def add_buildings(self):
        """Adiciona prédios aleatórios no mapa."""
        num_buildings = self.city_size //2 # Ajuste o número conforme necessário
        for _ in range(num_buildings):
            building_pos = [random.randint(0, self.city_size - 1), random.randint(0, self.city_size - 1)]
            self.city_map[building_pos[0]][building_pos[1]] = 4
    '''''

    def add_buildings(self, position):
        """Coloca um prédio na posição escolhida."""
        if 0 <= position[0] < self.city_size and 0 <= position[1] < self.city_size:
            self.city_map[position[0]][position[1]] = 4  # 4 representa um prédio
            #print(f"Prédio colocado na posição {position}")

        self.draw_city()  # Desenha o mapa atualizado

    def print_city_map(self):
        for row in self.city_map:
            print(row)


    def draw_city(self):
        """Desenha o mapa da cidade no Pygame."""
        for row in range(self.city_size):
            for col in range(self.city_size):
                cell_value = self.city_map[row][col]
                if cell_value in self.images:
                    self.screen.blit(self.images[cell_value], (col * self.cell_size, row * self.cell_size))
                elif cell_value == 1:
                    color = self.colors.get(cell_value, (255, 255, 255))
                    pygame.draw.rect(
                        self.screen,
                        color,
                        pygame.Rect(col * self.cell_size, row * self.cell_size, self.cell_size, self.cell_size)
                    )
                else:
                    color = self.colors.get(cell_value, (255, 255, 255))
                    pygame.draw.rect(
                        self.screen,
                        color,
                        pygame.Rect(col * self.cell_size, row * self.cell_size, self.cell_size, self.cell_size)
                    )
                pygame.draw.rect(  # Desenha borda das células
                    self.screen,
                    (0, 0, 0),
                    pygame.Rect(col * self.cell_size, row * self.cell_size, self.cell_size, self.cell_size),
                    1
                )
        pygame.display.flip()

    def move_agent(self, agent_pos, new_pos, agent_type):
        # Verifica o que estava na posição antiga antes de colocar o agente
        old_value = self.city_map[agent_pos[0]][agent_pos[1]]

        #print("OLDVALUE: ", old_value)

        # Atualiza a posição antiga do agente para o valor original (shelter ou vazio)
        if old_value == 5 or old_value == 9:
            self.city_map[agent_pos[0]][agent_pos[1]] = old_value  # 3 por exemplo representa um shelter
        else:
            self.city_map[agent_pos[0]][agent_pos[1]] = 1  # Caso contrário, é vazio ou outro valor

        # Atualiza a nova posição com o tipo do agente
        self.city_map[new_pos[0]][new_pos[1]] = agent_type

        # Redesenha o mapa
        self.draw_city()
    def is_road_free(self, position):
        return self.city_map[position[0]][position[1]] == 1

    def random_blockage(self):

        blockage_pos = [random.randint(0, self.city_size - 1), random.randint(0, self.city_size - 1)]
        while not self.is_road_free(blockage_pos):
            blockage_pos = [random.randint(0, self.city_size - 1), random.randint(0, self.city_size - 1)]

        self.city_map[blockage_pos[0]][blockage_pos[1]] = 0  # 0 representa um bloqueio de estrada
        print(f"Bloqueio criado na posição {blockage_pos}")

    def cause_landslides(self):
        """Cria derrocadas adjacentes aos prédios."""
        for row in range(self.city_size):
            for col in range(self.city_size):
                if self.city_map[row][col] == 4:  # Encontra prédios
                    # Verificar posições adjacentes
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = row + dx, col + dy
                        if 0 <= nx < self.city_size and 0 <= ny < self.city_size:
                            if self.city_map[nx][ny] == 1:  # Se é estrada livre
                                if random.random() < 0.1:  # Probabilidade de 30%
                                    self.city_map[nx][ny] = 0  # Transformar em bloqueio
                                    print(f"Derrocada em: ({nx}, {ny})")

        self.draw_city()