import pygame
import pyttsx3
import numpy as np
import random
import sys

# -----------------------------
# CONFIGURAÇÕES GLOBAIS & INICIALIZAÇÃO
# -----------------------------
pygame.init()
pygame.mixer.init()  # O mixer agora é inicializado em estéreo (channels=2 por padrão)
WIDTH, HEIGHT = 300, 600  # tamanho da janela (em pixels)
COLS, ROWS = 10, 20      # dimensões do tabuleiro em células
CELL_SIZE = WIDTH // COLS
FPS = 60

# Inicialização do mecanismo de síntese de voz para o menu (Analista de Sistemas)
engine = pyttsx3.init()
engine.setProperty('rate', 150)

# Cores utilizadas (Designer Gráfico)
COLORS = [
    (255, 0, 0),      # Vermelho – Nota Dó
    (0, 255, 0),      # Verde – Nota Ré
    (0, 0, 255),      # Azul – Nota Mi
    (255, 255, 0),    # Amarelo – Nota Fá
    (255, 0, 255),    # Magenta – Nota Sol
    (0, 255, 255),    # Ciano – Nota Lá
    (255, 165, 0)     # Laranja – Nota Si
]

# Frequências associadas (Designer de Som)
FREQUENCIES = [
    261.63,  # Dó
    293.66,  # Ré
    329.63,  # Mi
    349.23,  # Fá
    392.00,  # Sol
    440.00,  # Lá
    493.88   # Si
]

# Lista de formas pré-definidas (tetrominós sem rotação – Designer de Lógica)
# Cada forma é definida como lista de (dx, dy) relativa à posição de referência.
SHAPES = [
    [(0,0), (1,0), (0,1), (1,1)],      # Quadrado
    [(0,0), (0,1), (0,2), (0,3)],      # Barra vertical
    [(0,0), (1,0), (2,0), (1,1)],      # T fixo
    [(0,0), (1,0), (1,1), (2,1)],      # Z invertido
    [(1,0), (2,0), (0,1), (1,1)]       # S invertido
]

# Janela do jogo
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris Acessível")

clock = pygame.time.Clock()

# -----------------------------
# FUNÇÃO PARA GERAR TONALIDADES EM STEREO (Designer de Som)
# -----------------------------
def generate_tone(frequency, duration=0.5, volume=0.5, sample_rate=44100):
    # Gera um array de samples para o tom especificado
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone = np.sin(2 * np.pi * frequency * t)
    tone = (tone * 32767).astype(np.int16)
    # Converte o sinal mono em estéreo duplicando os dados
    tone = np.column_stack((tone, tone))
    sound = pygame.sndarray.make_sound(tone)
    sound.set_volume(volume)
    return sound

# Pré-gera os sons para cada cor/nota
PIECE_SOUNDS = [generate_tone(freq) for freq in FREQUENCIES]
# Som de colisão (nota curta de baixa duração)
COLLISION_SOUND = generate_tone(150, duration=0.2, volume=0.7)

# -----------------------------
# CLASSE Quadradinho (Unidade – Contribuição Conjunta)
# Cada quadradinho tem posição, cor e seu som associado.
# -----------------------------
class Quadradinho:
    def __init__(self, x, y, color, freq, sound):
        self.x = x  # coluna
        self.y = y  # linha
        self.color = color
        self.freq = freq
        self.sound = sound

    def draw(self, surface):
        rect = pygame.Rect(self.x * CELL_SIZE, self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(surface, self.color, rect)
        pygame.draw.rect(surface, (0,0,0), rect, 1)

    def play_sound(self):
        self.sound.play()

# -----------------------------
# CLASSE Piece (Peça em Queda – Designer de Lógica)
# Cada peça é composta por vários Quadradinhos com as mesmas características.
# -----------------------------
class Piece:
    def __init__(self):
        # Seleciona aleatoriamente uma forma e uma cor (com seu som e frequência)
        self.shape = random.choice(SHAPES)
        idx = random.randint(0, len(COLORS)-1)
        self.color = COLORS[idx]
        self.freq = FREQUENCIES[idx]
        self.sound = PIECE_SOUNDS[idx]
        # Posição de referência – começa no topo central
        self.x = COLS // 2 - 2
        self.y = -2  # inicia fora da tela para transição suave

    def get_blocks(self):
        # Retorna uma lista de Quadradinhos com posição absoluta
        return [Quadradinho(self.x + dx, self.y + dy, self.color, self.freq, self.sound)
                for (dx, dy) in self.shape]

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

# -----------------------------
# CLASSE Board (Tabuleiro – Analista de Sistemas)
# Controla o estado do jogo, incluindo o grid, a adição de peças, verificação de colisões e remoção de linhas.
# -----------------------------
class Board:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        # Cada célula pode ser None ou conter um Quadradinho
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]

    def is_valid_position(self, piece, dx=0, dy=0):
        for block in piece.get_blocks():
            new_x = block.x + dx
            new_y = block.y + dy
            # Verifica se está fora dos limites horizontais ou abaixo do tabuleiro
            if new_x < 0 or new_x >= self.cols or new_y >= self.rows:
                return False
            # Se a célula já estiver ocupada (ignorando blocos acima da tela)
            if new_y >= 0 and self.grid[new_y][new_x] is not None:
                return False
        return True

    def add_piece(self, piece):
        for block in piece.get_blocks():
            if block.y >= 0:
                self.grid[block.y][block.x] = block

    def clear_matches(self):
        remove_positions = set()

        # Checa horizontalmente
        for y in range(self.rows):
            count = 1
            for x in range(1, self.cols):
                current = self.grid[y][x]
                previous = self.grid[y][x-1]
                if current is not None and previous is not None and current.color == previous.color:
                    count += 1
                else:
                    if count >= 3:
                        for k in range(x - count, x):
                            remove_positions.add((y, k))
                    count = 1
            if count >= 3:
                for k in range(self.cols - count, self.cols):
                    remove_positions.add((y, k))

        # Checa verticalmente
        for x in range(self.cols):
            count = 1
            for y in range(1, self.rows):
                current = self.grid[y][x]
                previous = self.grid[y-1][x]
                if current is not None and previous is not None and current.color == previous.color:
                    count += 1
                else:
                    if count >= 3:
                        for k in range(y - count, y):
                            remove_positions.add((k, x))
                    count = 1
            if count >= 3:
                for k in range(self.rows - count, self.rows):
                    remove_positions.add((k, x))

        if remove_positions:
            for (y, x) in remove_positions:
                self.grid[y][x] = None
            self.apply_gravity()

    def apply_gravity(self):
        for x in range(self.cols):
            column_blocks = [self.grid[y][x] for y in range(self.rows) if self.grid[y][x] is not None]
            for y in range(self.rows-1, -1, -1):
                if column_blocks:
                    self.grid[y][x] = column_blocks.pop()
                    self.grid[y][x].y = y
                else:
                    self.grid[y][x] = None

    def draw(self, surface):
        for y in range(self.rows):
            for x in range(self.cols):
                block = self.grid[y][x]
                if block is not None:
                    block.draw(surface)

# -----------------------------
# CLASSE Cursor (Controle de Áudio – Designer de Lógica)
# Permite ao jogador mover um “cursor” pelo tabuleiro para ouvir os sons das peças.
# -----------------------------
class Cursor:
    def __init__(self):
        self.x = 0
        self.y = 0

    def move(self, dx, dy):
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < COLS and 0 <= new_y < ROWS:
            self.x = new_x
            self.y = new_y
            return True
        else:
            COLLISION_SOUND.play()
            return False

    def draw(self, surface):
        rect = pygame.Rect(self.x * CELL_SIZE, self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(surface, (255,255,255), rect, 3)

# -----------------------------
# FUNÇÃO DE MENU COM TEXT-TO-SPEECH (Analista de Sistemas)
# O menu é verbalizado e permite escolher “Iniciar” ou “Sair”
# -----------------------------
def menu():
    options = ["Iniciar Jogo", "Sair"]
    selected = 0

    while True:
        screen.fill((0, 0, 0))
        font = pygame.font.SysFont("arial", 24)
        for i, option in enumerate(options):
            color = (255,255,0) if i == selected else (200,200,200)
            text = font.render(option, True, color)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 + i * 30))
        pygame.display.flip()
        engine.say(options[selected])
        engine.runAndWait()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    return options[selected]

# -----------------------------
# LOOP PRINCIPAL DO JOGO (Integração Geral – Contribuição de Todos)
# -----------------------------
def main():
    choice = menu()
    if choice == "Sair":
        pygame.quit()
        sys.exit()

    board = Board(COLS, ROWS)
    falling_piece = Piece()
    cursor = Cursor()
    fall_timer = 0
    fall_delay = 500  # milissegundos para queda automática
    # Variável para evitar sobreposição de sons: guarda a última posição de foco (x, y)
    last_focus_position = None

    running = True
    while running:
        dt = clock.tick(FPS)
        fall_timer += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    if cursor.move(-1, 0):
                        delta = cursor.x - falling_piece.x
                        if board.is_valid_position(falling_piece, dx=delta, dy=0):
                            falling_piece.move(delta, 0)
                        else:
                            COLLISION_SOUND.play()
                elif event.key == pygame.K_RIGHT:
                    if cursor.move(1, 0):
                        delta = cursor.x - falling_piece.x
                        if board.is_valid_position(falling_piece, dx=delta, dy=0):
                            falling_piece.move(delta, 0)
                        else:
                            COLLISION_SOUND.play()
                elif event.key == pygame.K_UP:
                    cursor.move(0, -1)
                elif event.key == pygame.K_DOWN:
                    cursor.move(0, 1)
                elif event.key == pygame.K_c:
                    falling_piece.sound.play()
                elif event.key == pygame.K_SPACE:
                    if board.is_valid_position(falling_piece, dy=1):
                        falling_piece.move(0, 1)
                        fall_timer = 0

        if fall_timer >= fall_delay:
            if board.is_valid_position(falling_piece, dy=1):
                falling_piece.move(0, 1)
            else:
                board.add_piece(falling_piece)
                board.clear_matches()
                falling_piece = Piece()
                if not board.is_valid_position(falling_piece):
                    engine.say("Fim de jogo!")
                    engine.runAndWait()
                    running = False
            fall_timer = 0

        screen.fill((0, 0, 0))
        board.draw(screen)

        for block in falling_piece.get_blocks():
            if block.y >= 0:
                block.draw(screen)

        cursor.draw(screen)
        current_block = None
        if 0 <= cursor.y < ROWS and 0 <= cursor.x < COLS:
            current_block = board.grid[cursor.y][cursor.x]

        # Toca o som somente quando o foco mudar
        if current_block is not None:
            if last_focus_position != (cursor.x, cursor.y):
                current_block.play_sound()
                last_focus_position = (cursor.x, cursor.y)
        else:
            last_focus_position = None

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
