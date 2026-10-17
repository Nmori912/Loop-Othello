"""A two-player, wraparound Othello prototype built with pygame."""

from __future__ import annotations

import sys

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


def choose_computer_move(board: list[list[int]]) -> tuple[int, int]:
    moves = legal_moves(board, -1)
    if not moves:
        raise ValueError("Computer has no legal move")
    empty_count = BOARD_SIZE * BOARD_SIZE - sum(cell != 0 for row in board for cell in row)
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
        self.mode = "pvp"
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
            x, y = choose_computer_move(self.board)
            self.play(x, y)

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

    def draw_game(self) -> None:
        self.screen.fill(BACKGROUND)
        pygame.draw.rect(self.screen, PANEL, (0, 0, WINDOW_WIDTH, 96))

        title = self.font.render("ループオセロ", True, WHITE)
        self.screen.blit(title, (BOARD_X, 18))
        hint = self.small_font.render("端を越えると反対側から出てきます", True, MUTED)
        self.screen.blit(hint, (BOARD_X, 55))

        black = sum(cell == 1 for row in self.board for cell in row)
        white = sum(cell == -1 for row in self.board for cell in row)
        score = self.font.render(f"黒 {black}     白 {white}", True, WHITE)
        self.screen.blit(score, (WINDOW_WIDTH - 205, 18))
        status_color = GOLD if self.game_over else (WHITE if self.player == 1 else MUTED)
        status = self.font.render(self.message, True, status_color)
        self.screen.blit(status, (BOARD_X, 80))
        restart = self.small_font.render("R: 最初から", True, MUTED)
        self.screen.blit(restart, (WINDOW_WIDTH - 130, 82))

        board_rect = pygame.Rect(BOARD_X, BOARD_Y, BOARD_PIXELS, BOARD_PIXELS)
        pygame.draw.rect(self.screen, GREEN, board_rect)
        for i in range(BOARD_SIZE + 1):
            px = BOARD_X + i * CELL_SIZE
            py = BOARD_Y + i * CELL_SIZE
            pygame.draw.line(self.screen, GRID, (px, BOARD_Y), (px, BOARD_Y + BOARD_PIXELS), 2)
            pygame.draw.line(self.screen, GRID, (BOARD_X, py), (BOARD_X + BOARD_PIXELS, py), 2)

        for y, row in enumerate(self.board):
            for x, piece in enumerate(row):
                center = (BOARD_X + x * CELL_SIZE + CELL_SIZE // 2,
                          BOARD_Y + y * CELL_SIZE + CELL_SIZE // 2)
                if piece:
                    color = BLACK if piece == 1 else WHITE
                    pygame.draw.circle(self.screen, color, center, CELL_SIZE // 2 - 7)
                    pygame.draw.circle(self.screen, (12, 48, 35), center, CELL_SIZE // 2 - 7, 1)
                elif (x, y) in self.moves and self.computer_due_at is None:
                    pygame.draw.circle(self.screen, (158, 220, 174), center, 6)

        self.draw_wrap_animations()

        pygame.display.flip()

    def draw_wrap_animations(self) -> None:
        now = pygame.time.get_ticks()
        self.wrap_animations = [(expires, links) for expires, links in self.wrap_animations if expires > now]
        if not self.wrap_animations:
            return

        pulse = (now // 90) % 2
        radius = 13 + pulse * 4
        for _, links in self.wrap_animations:
            for exit_cell, entry_cell, dx, dy in links:
                for cell in (exit_cell, entry_cell):
                    cx = BOARD_X + cell[0] * CELL_SIZE + CELL_SIZE // 2
                    cy = BOARD_Y + cell[1] * CELL_SIZE + CELL_SIZE // 2
                    pygame.draw.circle(self.screen, GOLD, (cx, cy), radius, 3)
                    end = (cx + dx * 22, cy + dy * 22)
                    pygame.draw.line(self.screen, GOLD, (cx, cy), end, 4)
                    # Arrowhead makes the direction through the edge clear.
                    px, py = -dy, dx
                    tip = end
                    base_x, base_y = end[0] - dx * 8, end[1] - dy * 8
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

    def draw(self) -> None:
        if self.view == "title":
            self.draw_title()
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
                        self.reset()
                        self.view = "game"
                    elif self.view == "title" and event.key == pygame.K_ESCAPE:
                        running = False
                    elif self.view == "game" and event.key == pygame.K_r:
                        self.reset()
                    elif self.view == "game" and event.key == pygame.K_ESCAPE:
                        self.computer_due_at = None
                        self.view = "title"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if self.view == "title":
                        if self.pvp_button.collidepoint(event.pos):
                            self.mode = "pvp"
                            self.reset()
                            self.view = "game"
                        elif self.cpu_button.collidepoint(event.pos):
                            self.mode = "cpu"
                            self.reset()
                            self.view = "game"
                        elif self.quit_button.collidepoint(event.pos):
                            running = False
                    elif (self.computer_due_at is None
                          and BOARD_X <= mx < BOARD_X + BOARD_PIXELS
                          and BOARD_Y <= my < BOARD_Y + BOARD_PIXELS):
                        x = (mx - BOARD_X) // CELL_SIZE
                        y = (my - BOARD_Y) // CELL_SIZE
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
