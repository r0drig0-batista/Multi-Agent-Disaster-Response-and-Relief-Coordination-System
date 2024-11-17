import random

class Environment:
    def __init__(self, size):
        self.city_size = size
        #self.city_map = [[1 for _ in range(self.city_size)] for _ in range(self.city_size)]  # 1 = estrada livre

        self.city_map =[[7, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                        [1, 1, 1, 2, 1, 2, 2, 2, 1, 3],
                        [1, 1, 1, 7, 1, 1, 2, 3, 1, 3],
                        [1, 1, 1, 1, 1, 1, 2, 3, 1, 1],
                        [1, 1, 2, 1, 1, 1, 2, 3, 1, 3],
                        [1, 1, 1, 1, 1, 1, 8, 3, 1, 3],
                        [1, 3, 1, 3, 1, 1, 1, 1, 1, 3],
                        [1, 3, 1, 3, 1, 1, 1, 7, 1, 3],
                        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                        [1, 3, 1, 3, 3, 3, 3, 3, 1, 7]]

    def print_city_map(self):
        for row in self.city_map:
            print(row)

    def move_agent(self, agent_pos, new_pos, agent_type):
        self.city_map[agent_pos[0]][agent_pos[1]] = 1  # Limpar posição antiga
        self.city_map[new_pos[0]][new_pos[1]] = agent_type  # Atualizar nova posição

    def is_road_free(self, position):
        return self.city_map[position[0]][position[1]] == 1

    def random_blockage(self):

        blockage_pos = [random.randint(0, self.city_size - 1), random.randint(0, self.city_size - 1)]
        while not self.is_road_free(blockage_pos):
            blockage_pos = [random.randint(0, self.city_size - 1), random.randint(0, self.city_size - 1)]

        self.city_map[blockage_pos[0]][blockage_pos[1]] = 0  # 0 representa um bloqueio de estrada
        print(f"Bloqueio criado na posição {blockage_pos}")
