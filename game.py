"""A two-player, wraparound Othello prototype built with pygame."""

from __future__ import annotations

import sys
import random

import pygame


BOARD_SIZE = 8
CELL_SIZE = 72
BOARD_X = 32
BOARD_Y = 112
BOARD_PIXELS = BOARD_SIZE * CELL_SIZE
WINDOW_WIDTH = BOARD_X * 2 + BOARD_PIXELS
WINDOW_HEIGHT = BOARD_Y + BOARD_PIXELS + 32

BACKGROUND = (25, 29, 34)
PANEL = (36, 42, 48)
GREEN = (35, 122, 83)
GRID = (20, 77, 55)
WHITE = (245, 244, 232)
BLACK = (27, 30, 34)
GOLD = (255, 210, 90)
MUTED = (176, 187, 190)
ASSIST = (105, 225, 255)

DIRECTIONS = tuple(
    (dx, dy)
    for dy in (-1, 0, 1)
    for dx in (-1, 0, 1)
    if (dx, dy) != (0, 0)
)

JAPANESE_FONTS = (
    "Noto Sans CJK JP",
    "Yu Gothic",
    "Meiryo",
    "Hiragino Sans",
    "IPAexGothic",
    "IPAGothic",
    "Droid Sans Fallback",
)


def japanese_font(size: int) -> pygame.font.Font:
    """Pick an installed font with Japanese glyphs instead of pygame's default."""
    for name in JAPANESE_FONTS:
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def new_board() -> list[list[int]]:
    board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    board[3][3] = board[4][4] = -1
    board[3][4] = board[4][3] = 1
    return board


def captures_for(board: list[list[int]], x: int, y: int, player: int) -> list[tuple[int, int]]:
    """Return opponent pieces flipped by a move; rays wrap at every edge."""
    if board[y][x] != 0:
        return []

    captured: set[tuple[int, int]] = set()
    for dx, dy in DIRECTIONS:
        ray: list[tuple[int, int]] = []
        for distance in range(1, BOARD_SIZE):
            nx = (x + dx * distance) % BOARD_SIZE
            ny = (y + dy * distance) % BOARD_SIZE
            piece = board[ny][nx]
            if piece == -player:
                ray.append((nx, ny))
            elif piece == player:
                if ray:
                    captured.update(ray)
                break
            else:
                break
    return sorted(captured)


def legal_moves(board: list[list[int]], player: int) -> dict[tuple[int, int], list[tuple[int, int]]]:
    moves: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            captured = captures_for(board, x, y, player)
            if captured:
                moves[(x, y)] = captured
    return moves


def wrap_links_for(board: list[list[int]], x: int, y: int, player: int) -> list[tuple[tuple[int, int], tuple[int, int], int, int]]:
    """Find edge crossings that are part of a successful capture ray."""
    links = []
    for dx, dy in DIRECTIONS:
        crossed = []
        has_opponent = False
        for distance in range(1, BOARD_SIZE):
            raw_x = x + dx * distance
            raw_y = y + dy * distance
            nx, ny = raw_x % BOARD_SIZE, raw_y % BOARD_SIZE
            previous = ((x + dx * (distance - 1)) % BOARD_SIZE,
                        (y + dy * (distance - 1)) % BOARD_SIZE)
            if raw_x != nx or raw_y != ny:
                crossed.append((previous, (nx, ny), dx, dy))

            piece = board[ny][nx]
            if piece == -player:
                has_opponent = True
            elif piece == player:
                if has_opponent:
                    links.extend(crossed)
                break
            else:
                break
    return links


def apply_move(board: list[list[int]], move: tuple[int, int], captured: list[tuple[int, int]], player: int) -> list[list[int]]:
    next_board = [row[:] for row in board]
    x, y = move
    next_board[y][x] = player
    for fx, fy in captured:
        next_board[fy][fx] = player
    return next_board


def evaluate_board(board: list[list[int]]) -> float:
    """Evaluate from White's perspective; toroidal boards have no special corners."""
    black_discs = sum(cell == 1 for row in board for cell in row)
    white_discs = sum(cell == -1 for row in board for cell in row)
    occupied = black_discs + white_discs
    phase = occupied / (BOARD_SIZE * BOARD_SIZE)

    white_mobility = len(legal_moves(board, -1))
    black_mobility = len(legal_moves(board, 1))
    return (white_discs - black_discs) * (1 + 4 * phase) + (white_mobility - black_mobility) * 10 * (1 - phase)


def minimax(board: list[list[int]], player: int, depth: int, alpha: float, beta: float) -> float:
    moves = legal_moves(board, player)
    if depth == 0:
        return evaluate_board(board)
    if not moves:
        if not legal_moves(board, -player):
            return evaluate_board(board) * 100
        return minimax(board, -player, depth - 1, alpha, beta)

    if player == -1:
        best = float("-inf")
        for move, captured in moves.items():
            score = minimax(apply_move(board, move, captured, player), 1, depth - 1, alpha, beta)
            best = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best

    best = float("inf")
    for move, captured in moves.items():
        score = minimax(apply_move(board, move, captured, player), -1, depth - 1, alpha, beta)
        best = min(best, score)
        beta = min(beta, best)
        if beta <= alpha:
            break
    return best


def choose_computer_move(board: list[list[int]], difficulty: str) -> tuple[int, int]:
    moves = legal_moves(board, -1)
    if not moves:
        raise ValueError("Computer has no legal move")
    if difficulty == "easy":
        return random.choice(list(moves))

    empty_count = BOARD_SIZE * BOARD_SIZE - sum(cell != 0 for row in board for cell in row)
    if difficulty == "hard":
        depth = 6 if empty_count <= 10 else 4
    else:
        depth = 5 if empty_count <= 10 else 3
    best_move = next(iter(moves))
    best_score = float("-inf")
    for move, captured in moves.items():
        score = minimax(apply_move(board, move, captured, -1), 1, depth - 1,
                        float("-inf"), float("inf"))
        if score > best_score:
            best_score = score
            best_move = move
    return best_move


class LoopingOthello:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("ループオセロ")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = japanese_font(30)
        self.small_font = japanese_font(22)
        self.title_font = japanese_font(52)
        self.button_font = japanese_font(26)
        self.view = "title"
        self.pvp_button = pygame.Rect(WINDOW_WIDTH // 2 - 230, 510, 220, 58)
        self.cpu_button = pygame.Rect(WINDOW_WIDTH // 2 + 10, 510, 220, 58)
        self.quit_button = pygame.Rect(WINDOW_WIDTH // 2 - 135, 584, 270, 48)
        self.difficulty_buttons = {
            "easy": pygame.Rect(WINDOW_WIDTH // 2 - 220, 255, 440, 58),
            "normal": pygame.Rect(WINDOW_WIDTH // 2 - 220, 330, 440, 58),
            "hard": pygame.Rect(WINDOW_WIDTH // 2 - 220, 405, 440, 58),
        }
        self.back_button = pygame.Rect(WINDOW_WIDTH // 2 - 120, 505, 240, 48)
        self.mode = "pvp"
        self.difficulty = "normal"
        self.show_wrap_map = False
        self.assist_enabled = True
        self.wrap_animations: list[tuple[int, list[tuple[tuple[int, int], tuple[int, int], int, int]]]] = []
        self.computer_due_at: int | None = None
        self.reset()

    def reset(self) -> None:
        self.computer_due_at = None
        self.wrap_animations.clear()
        self.board = new_board()
        self.player = 1
        self.passed = False
        self.game_over = False
        self.winner: int | None = None
        self.moves = legal_moves(self.board, self.player)
        self.message = "黒の番です"

    def play(self, x: int, y: int) -> None:
        if self.game_over:
            return
        captured = self.moves.get((x, y))
        if captured is None:
            return

        wrap_links = wrap_links_for(self.board, x, y, self.player)
        if wrap_links:
            self.wrap_animations.append((pygame.time.get_ticks() + 1300, wrap_links))

        self.board[y][x] = self.player
        for fx, fy in captured:
            self.board[fy][fx] = self.player

        self.player = -self.player
        self.moves = legal_moves(self.board, self.player)
        if not self.moves:
            other_moves = legal_moves(self.board, -self.player)
            if not other_moves:
                self.finish()
                return
            self.message = f"{'白' if self.player == 1 else '黒'}は置ける場所がありません。自動パスします"
            self.player = -self.player
            self.moves = other_moves
            self.passed = True
        else:
            self.message = f"{'黒' if self.player == 1 else '白'}の番です"
            self.passed = False

    def schedule_computer_turn(self) -> None:
        if self.mode == "cpu" and not self.game_over and self.player == -1 and self.moves:
            self.computer_due_at = pygame.time.get_ticks() + 800
            self.message = "CPUが考えています..."

    def play_computer_turn(self) -> None:
        if self.mode == "cpu" and not self.game_over and self.player == -1 and self.moves:
            x, y = choose_computer_move(self.board, self.difficulty)
            self.play(x, y)

    def start_game(self, mode: str) -> None:
        self.mode = mode
        self.reset()
        self.view = "game"

    def finish(self) -> None:
        self.game_over = True
        black = sum(cell == 1 for row in self.board for cell in row)
        white = sum(cell == -1 for row in self.board for cell in row)
        self.winner = 1 if black > white else -1 if white > black else 0
        if self.winner == 0:
            self.message = f"引き分け！ 黒 {black} - 白 {white}"
        else:
            name = "黒" if self.winner == 1 else "白"
            self.message = f"{name}の勝ち！ 黒 {black} - 白 {white}"

    def board_layout(self) -> tuple[int, int, int]:
        if not self.show_wrap_map:
            return CELL_SIZE, BOARD_X, BOARD_Y
        tile = 40
        map_size = (BOARD_SIZE + 6) * tile
        map_x = (WINDOW_WIDTH - map_size) // 2
        map_y = BOARD_Y
        return tile, map_x + 3 * tile, map_y + 3 * tile

    def hovered_captures(self) -> set[tuple[int, int]]:
        if not self.assist_enabled or self.computer_due_at is not None:
            return set()
        if self.mode == "cpu" and self.player == -1:
            return set()
        tile, board_x, board_y = self.board_layout()
        mx, my = pygame.mouse.get_pos()
        if not (board_x <= mx < board_x + BOARD_SIZE * tile
                and board_y <= my < board_y + BOARD_SIZE * tile):
            return set()
        move = ((mx - board_x) // tile, (my - board_y) // tile)
        return set(self.moves.get(move, ()))

    def draw_game(self) -> None:
        self.screen.fill(BACKGROUND)
        pygame.draw.rect(self.screen, PANEL, (0, 0, WINDOW_WIDTH, 96))

        title = self.font.render("ループオセロ", True, WHITE)
        self.screen.blit(title, (BOARD_X, 18))
        map_hint = "E: 通常表示" if self.show_wrap_map else "E: 周囲3マス"
        assist_hint = "A: アシストON" if self.assist_enabled else "A: アシストOFF"
        hint_text = f"{map_hint}   {assist_hint}"
        hint = self.small_font.render(hint_text, True, MUTED)
        self.screen.blit(hint, (BOARD_X, 55))

        black = sum(cell == 1 for row in self.board for cell in row)
        white = sum(cell == -1 for row in self.board for cell in row)
        score = self.font.render(f"黒 {black}     白 {white}", True, WHITE)
        self.screen.blit(score, (WINDOW_WIDTH - 205, 18))
        status_color = GOLD if self.game_over else (WHITE if self.player == 1 else MUTED)
        status = self.font.render(self.message, True, status_color)
        self.screen.blit(status, (BOARD_X, 80))
        restart_text = "Enter: タイトルへ" if self.game_over else "R: 最初から"
        restart = self.small_font.render(restart_text, True, MUTED)
        self.screen.blit(restart, (WINDOW_WIDTH - 130, 82))

        tile, board_x, board_y = self.board_layout()
        captures_preview = self.hovered_captures()
        if self.show_wrap_map:
            map_x, map_y = board_x - 3 * tile, board_y - 3 * tile
            for vy in range(BOARD_SIZE + 6):
                for vx in range(BOARD_SIZE + 6):
                    x, y = (vx - 3) % BOARD_SIZE, (vy - 3) % BOARD_SIZE
                    main_board = 3 <= vx < 11 and 3 <= vy < 11
                    rect = pygame.Rect(map_x + vx * tile, map_y + vy * tile, tile, tile)
                    pygame.draw.rect(self.screen, GREEN if main_board else (34, 91, 70), rect)
                    pygame.draw.rect(self.screen, GRID, rect, 1)
                    piece = self.board[y][x]
                    center = rect.center
                    if piece:
                        color = BLACK if piece == 1 else WHITE
                        pygame.draw.circle(self.screen, color, center, tile // 2 - 4)
                        pygame.draw.circle(self.screen, (12, 48, 35), center, tile // 2 - 4, 1)
                        if (x, y) in captures_preview:
                            pygame.draw.circle(self.screen, ASSIST, center, tile // 2 - 2, 3)
                    elif (x, y) in self.moves and self.computer_due_at is None:
                        pygame.draw.circle(self.screen, (158, 220, 174), center, 4)
            main_rect = pygame.Rect(board_x, board_y, BOARD_SIZE * tile, BOARD_SIZE * tile)
            pygame.draw.rect(self.screen, GOLD, main_rect, 3)
        else:
            board_rect = pygame.Rect(board_x, board_y, BOARD_SIZE * tile, BOARD_SIZE * tile)
            pygame.draw.rect(self.screen, GREEN, board_rect)
            for i in range(BOARD_SIZE + 1):
                px = board_x + i * tile
                py = board_y + i * tile
                pygame.draw.line(self.screen, GRID, (px, board_y), (px, board_y + BOARD_SIZE * tile), 2)
                pygame.draw.line(self.screen, GRID, (board_x, py), (board_x + BOARD_SIZE * tile, py), 2)

            for y, row in enumerate(self.board):
                for x, piece in enumerate(row):
                    center = (board_x + x * tile + tile // 2, board_y + y * tile + tile // 2)
                    if piece:
                        color = BLACK if piece == 1 else WHITE
                        pygame.draw.circle(self.screen, color, center, tile // 2 - 7)
                        pygame.draw.circle(self.screen, (12, 48, 35), center, tile // 2 - 7, 1)
                        if (x, y) in captures_preview:
                            pygame.draw.circle(self.screen, ASSIST, center, tile // 2 - 3, 3)
                    elif (x, y) in self.moves and self.computer_due_at is None:
                        pygame.draw.circle(self.screen, (158, 220, 174), center, 6)

        self.draw_wrap_animations()
        if self.show_wrap_map and not self.wrap_animations:
            footer = self.small_font.render("外側のマスは反対側の続きです", True, MUTED)
            self.screen.blit(footer, footer.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 15)))

        pygame.display.flip()

    def draw_wrap_animations(self) -> None:
        now = pygame.time.get_ticks()
        self.wrap_animations = [(expires, links) for expires, links in self.wrap_animations if expires > now]
        if not self.wrap_animations:
            return

        pulse = (now // 90) % 2
        tile, board_x, board_y = self.board_layout()
        radius = min(tile // 4, 13 + pulse * 4)
        for _, links in self.wrap_animations:
            for exit_cell, entry_cell, dx, dy in links:
                for cell in (exit_cell, entry_cell):
                    cx = board_x + cell[0] * tile + tile // 2
                    cy = board_y + cell[1] * tile + tile // 2
                    pygame.draw.circle(self.screen, GOLD, (cx, cy), radius, 3)
                    arrow_length = tile // 3
                    end = (cx + dx * arrow_length, cy + dy * arrow_length)
                    pygame.draw.line(self.screen, GOLD, (cx, cy), end, 3)
                    # Arrowhead makes the direction through the edge clear.
                    px, py = -dy, dx
                    tip = end
                    base_x, base_y = end[0] - dx * 7, end[1] - dy * 7
                    pygame.draw.polygon(self.screen, GOLD, [
                        tip,
                        (base_x + px * 5, base_y + py * 5),
                        (base_x - px * 5, base_y - py * 5),
                    ])

        label = self.small_font.render("反対側へつながった！", True, GOLD)
        self.screen.blit(label, label.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 15)))

    def draw_title(self) -> None:
        self.screen.fill(BACKGROUND)
        pygame.draw.rect(self.screen, PANEL, (0, 0, WINDOW_WIDTH, 12))

        title = self.title_font.render("ループオセロ", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 105)))
        subtitle = self.small_font.render("つながる盤面で、いつものオセロに新しい一手を。", True, MUTED)
        self.screen.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 158)))

        # Small board illustration with pieces near the wrapped edges.
        tile = 42
        board_size = tile * 4
        board_x = (WINDOW_WIDTH - board_size) // 2
        board_y = 205
        pygame.draw.rect(self.screen, GREEN, (board_x, board_y, board_size, board_size), border_radius=5)
        for i in range(5):
            pygame.draw.line(self.screen, GRID, (board_x + i * tile, board_y),
                             (board_x + i * tile, board_y + board_size), 2)
            pygame.draw.line(self.screen, GRID, (board_x, board_y + i * tile),
                             (board_x + board_size, board_y + i * tile), 2)
        for x, y, color in ((0, 1, BLACK), (3, 2, WHITE), (1, 1, WHITE), (2, 2, BLACK)):
            center = (board_x + x * tile + tile // 2, board_y + y * tile + tile // 2)
            pygame.draw.circle(self.screen, color, center, tile // 2 - 5)

        rule_lines = (
            "盤面の左右・上下がつながっています",
            "端を越えて相手の石を挟んでみよう",
            "黒が先手。CPU戦では白がCPUです",
        )
        for index, line in enumerate(rule_lines):
            rendered = self.small_font.render(line, True, WHITE if index == 0 else MUTED)
            self.screen.blit(rendered, rendered.get_rect(center=(WINDOW_WIDTH // 2, 400 + index * 30)))

        mouse_pos = pygame.mouse.get_pos()
        pvp_hover = self.pvp_button.collidepoint(mouse_pos)
        pvp_color = (55, 154, 105) if pvp_hover else GREEN
        pygame.draw.rect(self.screen, pvp_color, self.pvp_button, border_radius=10)
        pvp_label = self.button_font.render("人 対 人", True, WHITE)
        self.screen.blit(pvp_label, pvp_label.get_rect(center=self.pvp_button.center))

        cpu_hover = self.cpu_button.collidepoint(mouse_pos)
        cpu_color = (55, 154, 105) if cpu_hover else GREEN
        pygame.draw.rect(self.screen, cpu_color, self.cpu_button, border_radius=10)
        cpu_label = self.button_font.render("人 対 CPU", True, WHITE)
        self.screen.blit(cpu_label, cpu_label.get_rect(center=self.cpu_button.center))

        quit_hover = self.quit_button.collidepoint(mouse_pos)
        quit_color = (60, 68, 75) if quit_hover else PANEL
        pygame.draw.rect(self.screen, quit_color, self.quit_button, border_radius=10)
        quit_label = self.small_font.render("終了", True, MUTED)
        self.screen.blit(quit_label, quit_label.get_rect(center=self.quit_button.center))
        pygame.display.flip()

    def draw_difficulty(self) -> None:
        self.screen.fill(BACKGROUND)
        pygame.draw.rect(self.screen, PANEL, (0, 0, WINDOW_WIDTH, 12))
        title = self.title_font.render("CPUの強さ", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 125)))
        subtitle = self.small_font.render("対戦相手のレベルを選んでください", True, MUTED)
        self.screen.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, 185)))

        labels = {"easy": "かんたん  —  ランダムに着手", "normal": "ふつう  —  数手先まで読む",
                  "hard": "つよい  —  より深く読む"}
        mouse_pos = pygame.mouse.get_pos()
        for level, rect in self.difficulty_buttons.items():
            color = (55, 154, 105) if rect.collidepoint(mouse_pos) else GREEN
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            label = self.button_font.render(labels[level], True, WHITE)
            self.screen.blit(label, label.get_rect(center=rect.center))

        back_color = (60, 68, 75) if self.back_button.collidepoint(mouse_pos) else PANEL
        pygame.draw.rect(self.screen, back_color, self.back_button, border_radius=10)
        back_label = self.small_font.render("タイトルへ戻る", True, MUTED)
        self.screen.blit(back_label, back_label.get_rect(center=self.back_button.center))
        pygame.display.flip()

    def draw(self) -> None:
        if self.view == "title":
            self.draw_title()
        elif self.view == "difficulty":
            self.draw_difficulty()
        else:
            self.draw_game()

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if self.view == "title" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_game("pvp")
                    elif self.view == "title" and event.key == pygame.K_ESCAPE:
                        running = False
                    elif self.view == "difficulty" and event.key == pygame.K_ESCAPE:
                        self.view = "title"
                    elif self.view == "difficulty" and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        self.difficulty = {pygame.K_1: "easy", pygame.K_2: "normal", pygame.K_3: "hard"}[event.key]
                        self.start_game("cpu")
                    elif self.view == "game" and self.game_over and event.key == pygame.K_RETURN:
                        self.computer_due_at = None
                        self.view = "title"
                    elif self.view == "game" and event.key == pygame.K_r:
                        self.reset()
                    elif self.view == "game" and event.key == pygame.K_e:
                        self.show_wrap_map = not self.show_wrap_map
                    elif self.view == "game" and event.key == pygame.K_a:
                        self.assist_enabled = not self.assist_enabled
                    elif self.view == "game" and event.key == pygame.K_ESCAPE:
                        self.computer_due_at = None
                        self.view = "title"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if self.view == "title":
                        if self.pvp_button.collidepoint(event.pos):
                            self.start_game("pvp")
                        elif self.cpu_button.collidepoint(event.pos):
                            self.view = "difficulty"
                        elif self.quit_button.collidepoint(event.pos):
                            running = False
                    elif self.view == "difficulty":
                        selected = next((level for level, rect in self.difficulty_buttons.items()
                                         if rect.collidepoint(event.pos)), None)
                        if selected:
                            self.difficulty = selected
                            self.start_game("cpu")
                        elif self.back_button.collidepoint(event.pos):
                            self.view = "title"
                    else:
                        tile, board_x, board_y = self.board_layout()
                        if (self.computer_due_at is None
                                and board_x <= mx < board_x + BOARD_SIZE * tile
                                and board_y <= my < board_y + BOARD_SIZE * tile):
                            x = (mx - board_x) // tile
                            y = (my - board_y) // tile
                            self.play(x, y)
                            self.schedule_computer_turn()
            if self.computer_due_at is not None and pygame.time.get_ticks() >= self.computer_due_at:
                self.computer_due_at = None
                self.play_computer_turn()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    LoopingOthello().run()
