import pygame
import socket
import json
import threading
import sys
import os

HOST = "127.0.0.1"
PORT = 50005

buffers = {}

def send_message(sock, data):
    msg = json.dumps(data) + "\n"
    sock.sendall(msg.encode("utf-8"))

def recv_message(sock):
    if sock not in buffers:
        buffers[sock] = ""

    while True:
        if "\n" in buffers[sock]:
            msg, buffers[sock] = buffers[sock].split("\n", 1)
            return json.loads(msg)

        chunk = sock.recv(1024)
        if not chunk:
            return None

        buffers[sock] += chunk.decode("utf-8")


class BattleshipGUI:
    def __init__(self):
        pygame.init()

        # FINESTRA RIDIMENSIONABILE
        self.screen = pygame.display.set_mode((900, 700), pygame.RESIZABLE)
        pygame.display.set_caption("Battleship - Client Pygame")

        self.font = pygame.font.SysFont("Orbitron", 36, bold=True)
        self.small_font = pygame.font.SysFont("Orbitron", 22)

        self.grid_size = 5
        self.cell_size = 80

        self.my_board = [["~"] * self.grid_size for _ in range(self.grid_size)]
        self.enemy_board = [["~"] * self.grid_size for _ in range(self.grid_size)]

        # Offset iniziali (verranno aggiornati dinamicamente)
        self.my_offset_x = 70
        self.enemy_offset_x = 500
        self.offset_y = 210

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        self.turn_active = False
        self.game_over = False
        self.winner = False

        self.placing = False
        self.ships = []
        self.max_ships = 6

        self.animations = []

        self.load_assets()
        self.menu()
        self.fade_in()

        threading.Thread(target=self.network_loop, daemon=True).start()
        self.main_loop()

    def load_image_safe(self, filename):
        if os.path.exists(filename):
            try:
                return pygame.image.load(filename).convert_alpha()
            except:
                return None
        return None

    def load_assets(self):
        self.bg = self.load_image_safe("background_sea.jpg")
        if self.bg:
            self.bg = pygame.transform.scale(self.bg, (900, 700))
        self.bg_offset = 0

        self.water = self.load_image_safe("water.png")
        if self.water:
            self.water = pygame.transform.scale(self.water, (self.cell_size, self.cell_size))

        self.ship = self.load_image_safe("ship.png")
        if self.ship:
            self.ship = pygame.transform.scale(self.ship, (self.cell_size, self.cell_size))

        self.fire_frames = []
        for i in range(1, 5):
            img = self.load_image_safe(f"fire{i}.png")
            if img:
                img = pygame.transform.scale(img, (self.cell_size, self.cell_size))
                self.fire_frames.append(img)

        self.splash_frames = []
        for i in range(1, 5):
            img = self.load_image_safe(f"splash{i}.png")
            if img:
                img = pygame.transform.scale(img, (self.cell_size, self.cell_size))
                self.splash_frames.append(img)

    def menu(self):
        clock = pygame.time.Clock()
        pulse = 0
        direction = 1

        while True:
            if self.bg:
                self.bg_offset = (self.bg_offset + 0.2) % 700
                self.screen.blit(self.bg, (0, self.bg_offset - 700))
                self.screen.blit(self.bg, (0, self.bg_offset))
            else:
                self.screen.fill((20, 20, 40))

            pulse += direction * 0.5
            if pulse > 10 or pulse < -10:
                direction *= -1

            title_text = "BATTLESHIP"
            title = self.font.render(title_text, True, (255, 255, 255))
            glow = self.font.render(title_text, True, (0, 150, 255))

            title_x = (900 - title.get_width()) // 2
            title_y = 150

            self.screen.blit(glow, (title_x - 3 + pulse/2, title_y - 3))
            self.screen.blit(title, (title_x + pulse/2, title_y))

            mx, my = pygame.mouse.get_pos()

            play_rect = pygame.Rect(330, 300, 240, 70)
            quit_rect = pygame.Rect(330, 390, 240, 70)

            def draw_button(rect, text, hover_color, normal_color):
                label = self.font.render(text, True, (255, 255, 255))
                text_x = rect.x + (rect.width - label.get_width()) // 2
                text_y = rect.y + (rect.height - label.get_height()) // 2

                if rect.collidepoint(mx, my):
                    pygame.draw.rect(self.screen, hover_color, rect, border_radius=12)
                else:
                    pygame.draw.rect(self.screen, normal_color, rect, border_radius=12)

                self.screen.blit(label, (text_x, text_y))

            draw_button(play_rect, "GIOCA", (0, 180, 255), (0, 120, 255))
            draw_button(quit_rect, "ESCI", (220, 70, 70), (180, 50, 50))

            info = self.small_font.render(
                "Posiziona le navi sulla tua griglia, poi attacca quelle nemiche.",
                True, (255, 255, 255)
            )
            info_x = (900 - info.get_width()) // 2
            self.screen.blit(info, (info_x, 500))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_rect.collidepoint(event.pos):
                        self.fade_in()
                        return
                    if quit_rect.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()

            pygame.display.flip()
            clock.tick(60)

    def fade_in(self):
        fade = pygame.Surface((900, 700))
        fade.fill((0, 0, 0))
        for alpha in range(255, -1, -5):
            fade.set_alpha(alpha)
            self.screen.blit(fade, (0, 0))
            pygame.display.update()
            pygame.time.delay(5)

    def network_loop(self):
        while True:
            data = recv_message(self.sock)
            if data is None:
                break

            t = data.get("type")

            if t == "info":
                print("[CLIENT]", data.get("msg"))

            elif t == "place_ships":
                self.placing = True
                self.ships = []
                self.my_board = [["~"] * self.grid_size for _ in range(self.grid_size)]

            elif t == "ships_ok":
                self.placing = False

            elif t == "your_turn":
                self.turn_active = True

            elif t == "result":
                r = data.get("result")
                x = data.get("x")
                y = data.get("y")

                if r in ("hit", "win"):
                    self.enemy_board[x][y] = "X"
                    self.animations.append({"x": x, "y": y, "frame": 0, "timer": 0, "type": "fire"})
                elif r == "miss":
                    self.enemy_board[x][y] = "O"
                    self.animations.append({"x": x, "y": y, "frame": 0, "timer": 0, "type": "splash"})

                if r == "win":
                    self.game_over = True
                    self.winner = True

            elif t == "enemy_shot":
                x = data.get("x")
                y = data.get("y")
                result = data.get("result")

                if result in ("hit", "win"):
                    self.my_board[x][y] = "X"
                else:
                    self.my_board[x][y] = "O"

            elif t == "game_over":
                self.game_over = True
                self.winner = data.get("winner")
                break

        self.sock.close()

    def draw_grid(self, board, offset_x, label_text):

        label = self.font.render(label_text, True, (255, 255, 255))
        label_x = offset_x + (self.grid_size*self.cell_size - label.get_width()) // 2
        self.screen.blit(label, (label_x, self.offset_y - 80))

        for i in range(self.grid_size):
            c = chr(65 + i)
            txt = self.small_font.render(c, True, (255, 255, 255))
            x_pos = offset_x + i*self.cell_size + (self.cell_size - txt.get_width())//2
            self.screen.blit(txt, (x_pos, self.offset_y - 45))

        for i in range(self.grid_size):
            txt = self.small_font.render(str(i+1), True, (255, 255, 255))
            y_pos = self.offset_y + i*self.cell_size + (self.cell_size - txt.get_height())//2
            x_num = offset_x - 25
            self.screen.blit(txt, (x_num, y_pos))

        if label_text == "NEMICO" and not self.placing:
            glow_color = (0, 200, 255) if self.turn_active else (80, 80, 80)
            pygame.draw.rect(
                self.screen,
                glow_color,
                (offset_x - 5, self.offset_y - 5,
                 self.grid_size*self.cell_size + 10,
                 self.grid_size*self.cell_size + 10),
                4,
                border_radius=8
            )

        for x in range(self.grid_size):
            for y in range(self.grid_size):
                rect = pygame.Rect(
                    offset_x + y * self.cell_size,
                    self.offset_y + x * self.cell_size,
                    self.cell_size,
                    self.cell_size
                )

                cell = board[x][y]

                if self.water:
                    self.screen.blit(self.water, rect)
                else:
                    pygame.draw.rect(self.screen, (0, 70, 140), rect)

                if board is self.my_board and cell == "S":
                    if self.ship:
                        self.screen.blit(self.ship, rect)
                    else:
                        pygame.draw.rect(self.screen, (180, 180, 180), rect)

                elif cell == "X":
                    pygame.draw.rect(self.screen, (255, 60, 60), rect)

                elif cell == "O":
                    pygame.draw.rect(self.screen, (230, 230, 230), rect)

                pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)

    def update_animations(self):
        for anim in self.animations[:]:
            frames = self.fire_frames if anim["type"] == "fire" else self.splash_frames

            if not frames:
                self.animations.remove(anim)
                continue

            if anim["frame"] >= len(frames):
                anim["frame"] = 0

            frame_img = frames[anim["frame"]]

            rect = pygame.Rect(
                self.enemy_offset_x + anim["y"] * self.cell_size,
                self.offset_y + anim["x"] * self.cell_size,
                self.cell_size,
                self.cell_size
            )

            self.screen.blit(frame_img, rect)

            anim["timer"] += 1
            if anim["timer"] > 4:
                anim["frame"] += 1
                anim["timer"] = 0

            if anim["frame"] >= len(frames):
                self.animations.remove(anim)

    def draw_hud(self):
        pygame.draw.rect(self.screen, (15, 15, 40), (0, 0, self.screen.get_width(), 120))

        title = self.font.render("BATTLESHIP", True, (255, 255, 255))
        self.screen.blit(title, ((self.screen.get_width() - title.get_width()) // 2, 20))

        if self.placing:
            text = f"Posiziona le navi: {len(self.ships)}/{self.max_ships}"
            color = (255, 255, 0)
        else:
            text = "TUO TURNO" if self.turn_active else "TURNO NEMICO"
            color = (200, 200, 50)

        label = self.font.render(text, True, color)
        label_x = (self.screen.get_width() - label.get_width()) // 2
        self.screen.blit(label, (label_x, 70))

    def handle_click(self, pos):
        if self.game_over:
            return

        mx, my = pos

        if self.placing:
            col = (mx - self.my_offset_x) // self.cell_size
            row = (my - self.offset_y) // self.cell_size

            if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                if self.my_board[row][col] != "S" and len(self.ships) < self.max_ships:
                    self.my_board[row][col] = "S"
                    self.ships.append([row, col])

                    if len(self.ships) == self.max_ships:
                        send_message(self.sock, {
                            "type": "ships",
                            "ships": self.ships
                        })
            return

        if self.turn_active:
            col = (mx - self.enemy_offset_x) // self.cell_size
            row = (my - self.offset_y) // self.cell_size

            if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                if self.enemy_board[row][col] in ("X", "O"):
                    return

                send_message(self.sock, {
                    "type": "shot",
                    "x": row,
                    "y": col
                })
                self.turn_active = False

    def main_loop(self):
        clock = pygame.time.Clock()

        while True:

            # -----------------------------------------
            # CALCOLO DINAMICO DELLE POSIZIONI
            # -----------------------------------------
            w, h = self.screen.get_size()

            grid_w = self.grid_size * self.cell_size
            grid_h = self.grid_size * self.cell_size

            self.my_offset_x = w//4 - grid_w//2
            self.enemy_offset_x = 3*w//4 - grid_w//2
            self.offset_y = h//2 - grid_h//2
            # -----------------------------------------

            if self.bg:
                self.bg = pygame.transform.scale(self.bg, (w, h))
                self.bg_offset = (self.bg_offset + 0.2) % h
                self.screen.blit(self.bg, (0, self.bg_offset - h))
                self.screen.blit(self.bg, (0, self.bg_offset))
            else:
                self.screen.fill((30, 30, 60))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)

            self.draw_hud()
            self.draw_grid(self.my_board, self.my_offset_x, "LE TUE NAVI")
            self.draw_grid(self.enemy_board, self.enemy_offset_x, "NEMICO")

            mx, my = pygame.mouse.get_pos()
            col = (mx - self.enemy_offset_x) // self.cell_size
            row = (my - self.offset_y) // self.cell_size
            if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                rect = pygame.Rect(
                    self.enemy_offset_x + col*self.cell_size,
                    self.offset_y + row*self.cell_size,
                    self.cell_size,
                    self.cell_size
                )
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 3)

            self.update_animations()

            if self.game_over:
                overlay = pygame.Surface((w, h), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.screen.blit(overlay, (0, 0))

                text = "HAI VINTO!" if self.winner else "HAI PERSO"
                color = (0, 255, 0) if self.winner else (255, 0, 0)

                msg = self.font.render(text, True, color)
                self.screen.blit(msg, ((w - msg.get_width()) // 2, h//2 - 50))

            pygame.display.flip()
            clock.tick(60)


if __name__ == "__main__":
    BattleshipGUI()
