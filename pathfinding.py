def get_neighbors(node, environment, goal=None):
    # Define as direções N, S, L, O
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    neighbors = []

    for direction in directions:
        neighbor = (node[0] + direction[0], node[1] + direction[1])

        # Verifica se o vizinho está dentro dos limites do mapa
        if 0 <= neighbor[0] < environment.city_size and 0 <= neighbor[1] < environment.city_size:
            # Permite o destino final (goal) mesmo se não for uma estrada livre
            if environment.is_road_free(neighbor) or neighbor == goal:
                neighbors.append(neighbor)

    return neighbors


def heuristic(current, goal):
    # Calcula a distância Manhattan
    return abs(current[0] - goal[0]) + abs(current[1] - goal[1])

def a_star(environment, start, goal):
    open_list = []
    closed_list = set()
    parents = {}

    # `g` armazena o custo para chegar a cada nó

    g = {start: 0}
    open_list.append((start, heuristic(start, goal)))

    parents[start] = None

    while open_list:
        # Ordena a lista aberta para sempre escolher o nó com menor f(n)
        open_list.sort(key=lambda x: g[x[0]] + heuristic(x[0], goal))
        current = open_list.pop(0)[0]
        #print("Atual: ", current)

        # Se chegamos ao objetivo, vamos reconstruir o caminho
        if current == goal:
            path = []
            while current is not None:
                path.append(current)
                current = parents[current]
            path.reverse()
            return path  # Retorna o caminho do start ao goal

        # Marca o nó atual como processado
        closed_list.add(current)

        # Processa cada vizinho
        for neighbor in get_neighbors(current, environment, goal):

            if neighbor in closed_list:
                continue

            # Calcula o custo `g` para o vizinho
            tentative_g = g[current] + 1

            if neighbor not in g or tentative_g < g[neighbor]:
                # Atualiza o custo e o pai do vizinho
                g[neighbor] = tentative_g
                f_cost = tentative_g + heuristic(neighbor, goal)
                open_list.append((neighbor, f_cost))
                parents[neighbor] = current

    return None  # Se nenhum caminho for encontrado
