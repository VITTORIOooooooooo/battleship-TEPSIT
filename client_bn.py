import pygame
import socket
import json
import threading
import sys
import math
import random

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


# ══════════════════════════════════════════
#  PALETTE
# ══════════════════════════════════════════
C_BG       = (8,  18,  32)
C_OCEAN    = (10, 40,  80)
C_OCEAN_LT = (15, 60, 110)
C_GRID     = (20, 60,  100)
C_SHIP     = (155, 165, 175)
C_SHIP_DK  = (85,  90, 105)
C_HIT      = (230, 80,  30)
C_MISS     = (180, 200, 220)
C_GOLD     = (210, 170,  60)
C_GOLD_LT  = (255, 215,  80)
C_WHITE    = (235, 240, 245)
C_CYAN     = (50,  200, 230)
C_RED      = (210,  50,  50)
C_GREEN    = (50,  200, 100)
C_DIM      = (80,  100, 120)
C_BG2      = (12,  26,  48)

# colori per tipologia messaggio chat
CHAT_COLORS = {
    "system":      (160, 140, 60),
    "player":      (235, 240, 245),
    "action_hit":  (230, 110, 40),
    "action_miss": (100, 160, 200),
    "action_win":  (255, 215, 80),
    "me":          (50,  200, 230),
}

GRID_SIZE = 10
CHAT_W    = 280   # larghezza pannello chat

# Flotta classica
FLEET = [
    ("PORTAEREI",          5, (180, 80,  80)),
    ("CORAZZATA",          4, (80,  140, 200)),
    ("INCROCIATORE",       3, (80,  200, 120)),
    ("SOTTOMARINO",        3, (160, 120, 200)),
    ("CACCIATORPEDINIERE", 2, (200, 160, 80)),
]
TOTAL_SHIP_CELLS = sum(s[1] for s in FLEET)  # 17


# ══════════════════════════════════════════
#  PARTICELLE
# ══════════════════════════════════════════
class Particle:
    def __init__(self, x, y, color, vx=0, vy=0, life=40, radius=3):
        self.x, self.y   = float(x), float(y)
        self.color        = color
        self.vx, self.vy  = vx, vy
        self.life = self.max_life = life
        self.radius       = radius

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.vy += 0.11;   self.life -= 1

    def draw(self, surf):
        alpha = int(255 * self.life / self.max_life)
        r = max(1, int(self.radius * self.life / self.max_life))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (int(self.x)-r, int(self.y)-r))

def spawn_explosion(px, py, particles, color):
    for _ in range(20):
        a = random.uniform(0, math.tau); sp = random.uniform(1.5, 5.5)
        particles.append(Particle(px, py, color,
            math.cos(a)*sp, math.sin(a)*sp-2,
            random.randint(25,55), random.randint(2,5)))

def spawn_splash(px, py, particles):
    for _ in range(12):
        a = random.uniform(-math.pi, 0); sp = random.uniform(1,3.5)
        particles.append(Particle(px, py, C_MISS,
            math.cos(a)*sp, math.sin(a)*sp-1,
            random.randint(18,36), 2))


# ══════════════════════════════════════════
#  DRAW HELPERS
# ══════════════════════════════════════════
def draw_panel(surf, rect, alpha=200, color=C_BG2, radius=10):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), (0,0,rect.width,rect.height), border_radius=radius)
    surf.blit(s, rect.topleft)

def draw_border(surf, rect, color, width=2, radius=8):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)

def glow_rect(surf, rect, color, spread=8):
    for i in range(spread, 0, -2):
        a = int(55 * i / spread)
        s = pygame.Surface((rect.width+i*2, rect.height+i*2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, a), (0,0,s.get_width(),s.get_height()), border_radius=12)
        surf.blit(s, (rect.x-i, rect.y-i))

def draw_scanlines(surf, alpha=12):
    for y in range(0, surf.get_height(), 4):
        s = pygame.Surface((surf.get_width(), 2), pygame.SRCALPHA)
        s.fill((0,0,0,alpha)); surf.blit(s, (0,y))

def make_stars(w, h, n=140):
    return [(random.randint(0,w), random.randint(0,h), random.uniform(0.3,1.2)) for _ in range(n)]

def draw_stars(surf, stars, t):
    for sx, sy, sp in stars:
        y = int(sy + t*sp) % surf.get_height()
        a = int(70 + 55*math.sin(t*0.05+sx))
        s = pygame.Surface((2,2), pygame.SRCALPHA); s.fill((*C_OCEAN_LT, a))
        surf.blit(s, (sx, y))

def wrap_text(font, text, max_w):
    """Spezza il testo in righe che stanno in max_w pixel."""
    words = text.split(" ")
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if font.size(test)[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines if lines else [""]


# ══════════════════════════════════════════
#  CLASSE PRINCIPALE
# ══════════════════════════════════════════
class BattleshipGUI:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("BATTLESHIP  //  Naval Combat  10×10")
        info = pygame.display.Info()
        default_w = min(1400, info.current_w)
        default_h = min(860,  info.current_h)
        self.fullscreen    = False
        self.windowed_size = (default_w, default_h)
        self.screen = pygame.display.set_mode((default_w, default_h), pygame.RESIZABLE)

        def tf(names, size, bold=False):
            for n in names:
                try:
                    f = pygame.font.SysFont(n, size, bold=bold)
                    if f: return f
                except: pass
            return pygame.font.SysFont(None, size, bold=bold)

        self.f_title  = tf(["Orbitron","Rajdhani","Impact"],       50, bold=True)
        self.f_big    = tf(["Orbitron","Rajdhani","Verdana"],       28, bold=True)
        self.f_med    = tf(["Orbitron","Rajdhani","Verdana"],       19, bold=True)
        self.f_small  = tf(["Consolas","Courier New","Monospace"],  14)
        self.f_input  = tf(["Consolas","Courier New","Monospace"],  22, bold=True)
        self.f_lb     = tf(["Consolas","Courier New","Monospace"],  15)
        self.f_chat   = tf(["Consolas","Courier New","Monospace"],  13)
        self.f_chat_b = tf(["Consolas","Courier New","Monospace"],  13, bold=True)

        self.grid_size = GRID_SIZE
        w0, h0 = self.screen.get_size()
        self.stars = make_stars(w0, h0)

        self.my_board    = [["~"]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.enemy_board = [["~"]*GRID_SIZE for _ in range(GRID_SIZE)]

        self.turn_active  = False
        self.game_over    = False
        self.winner       = False
        self.placing      = False
        self.particles    = []
        self.t            = 0
        self.status_msg   = ""
        self.status_timer = 0

        # posizionamento navi
        self.placed_ships     = []
        self.current_ship_idx = 0
        self.ship_orientation = "H"
        self.hover_cells      = []
        self.hover_valid      = False

        self.player_name   = "COMANDANTE"
        self.enemy_name    = "AVVERSARIO"
        self.player_number = 1
        self.leaderboard   = []

        # ── CHAT ──
        self.chat_messages  = []   # lista di dict {sender, text, kind}
        self.chat_input     = ""   # testo in digitazione
        self.chat_focused   = False
        self.chat_blink     = 0
        self.chat_scroll    = 0    # righe scrollate dal fondo (0 = fondo)
        self._chat_lock     = threading.Lock()

        self.sock = None

        self.run_menu()
        self.run_connect_screen()
        threading.Thread(target=self.network_loop, daemon=True).start()
        self.main_loop()

    # ──────────────────────────────────────
    #  LAYOUT DINAMICO
    #  Riserva CHAT_W px sulla destra per la chat
    # ──────────────────────────────────────
    def _layout(self):
        w, h = self.screen.get_size()
        gs   = GRID_SIZE
        usable_w = w - CHAT_W - 12          # spazio disponibile per le due griglie
        cs = min((usable_w - 120) // (gs * 2 + 2), (h - 200) // (gs + 4))
        cs = max(28, min(cs, 56))
        total_grid_w = gs * cs
        gap = max(40, (usable_w - 2*total_grid_w - 40) // 3)
        ox_my    = gap
        ox_enemy = gap * 2 + total_grid_w
        oy       = max(110, h // 2 - total_grid_w // 2 + 20)
        return w, h, cs, ox_my, ox_enemy, oy

    # ──────────────────────────────────────
    #  MENU
    # ──────────────────────────────────────
    def run_menu(self):
        clock = pygame.time.Clock()
        t = 0; name_buf = ""; blink = 0
        w, h = self.screen.get_size()
        btn_play = pygame.Rect(w//2-150, h//2+80,  300, 58)
        btn_quit = pygame.Rect(w//2-150, h//2+154, 300, 58)

        while True:
            t += 1; blink += 1
            w, h = self.screen.get_size()
            self.screen.fill(C_BG)
            draw_stars(self.screen, self.stars, t*0.5)
            for xi in range(0, w, 3):
                yi = int(h*0.80 + 18*math.sin(xi*0.016 + t*0.038))
                pygame.draw.line(self.screen, C_OCEAN, (xi, yi), (xi, h), 1)

            ts = self.f_title.render("BATTLESHIP", True, C_GOLD)
            tx = w//2 - ts.get_width()//2
            for off in [(3,3),(-3,3),(3,-3),(-3,-3)]:
                gs2 = self.f_title.render("BATTLESHIP", True, C_OCEAN_LT)
                self.screen.blit(gs2, (tx+off[0], h//4+off[1]))
            self.screen.blit(ts, (tx, h//4))
            sub = self.f_med.render("NAVAL COMBAT  //  10×10  MULTIPLAYER", True, C_DIM)
            self.screen.blit(sub, (w//2-sub.get_width()//2, h//4+ts.get_height()+6))

            pr = pygame.Rect(w//2-230, h//2-50, 460, 120)
            draw_panel(self.screen, pr, alpha=190); draw_border(self.screen, pr, C_GOLD, 1)
            lbl = self.f_med.render("INSERISCI IL TUO NOME OPERATIVO:", True, C_GOLD)
            self.screen.blit(lbl, (w//2-lbl.get_width()//2, h//2-34))
            ir = pygame.Rect(w//2-175, h//2, 350, 50)
            draw_panel(self.screen, ir, alpha=220, color=C_OCEAN)
            draw_border(self.screen, ir, C_CYAN, 2)
            cur = "|" if (blink//30)%2==0 else " "
            it = self.f_input.render(name_buf + cur, True, C_WHITE)
            self.screen.blit(it, (ir.x+12, ir.y+(ir.h-it.get_height())//2))

            mx, my = pygame.mouse.get_pos()
            for rect, txt, hc, nc in [
                (btn_play, "INIZIA PARTITA", C_CYAN, C_OCEAN),
                (btn_quit, "ESCI",           C_RED,  (55,18,18))]:
                hover = rect.collidepoint(mx, my)
                if hover: glow_rect(self.screen, rect, hc, 10)
                draw_panel(self.screen, rect, 230, hc if hover else nc, 8)
                draw_border(self.screen, rect, hc, 2)
                bt = self.f_big.render(txt, True, C_WHITE)
                self.screen.blit(bt, (rect.x+(rect.w-bt.get_width())//2,
                                      rect.y+(rect.h-bt.get_height())//2))

            hint = self.f_small.render(
                "Portaerei(5)  Corazzata(4)  Incrociatore(3)  Sottomarino(3)  Cacciatorpediniere(2)  •  R=ruota  F11=fullscreen",
                True, C_DIM)
            self.screen.blit(hint, (w//2-hint.get_width()//2, h-32))
            draw_scanlines(self.screen); pygame.display.flip(); clock.tick(60)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        w, h = ev.w, ev.h
                        self.windowed_size = (w, h)
                        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                        self.stars = make_stars(w, h)
                        btn_play = pygame.Rect(w//2-150, h//2+80,  300, 58)
                        btn_quit = pygame.Rect(w//2-150, h//2+154, 300, 58)
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                    if ev.key == pygame.K_F11: self._toggle_fullscreen()
                    if ev.key == pygame.K_RETURN:
                        self.player_name = name_buf.strip().upper() or "COMANDANTE"
                        self._fade("out"); return
                    elif ev.key == pygame.K_BACKSPACE:
                        name_buf = name_buf[:-1]
                    elif len(name_buf) < 16 and ev.unicode.isprintable():
                        name_buf += ev.unicode.upper()
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    if btn_play.collidepoint(ev.pos):
                        self.player_name = name_buf.strip().upper() or "COMANDANTE"
                        self._fade("out"); return
                    if btn_quit.collidepoint(ev.pos): pygame.quit(); sys.exit()

    # ──────────────────────────────────────
    #  CONNESSIONE
    # ──────────────────────────────────────
    def run_connect_screen(self):
        clock = pygame.time.Clock()
        t = 0; connected = False; err_msg = ""

        def do_connect():
            nonlocal connected, err_msg
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((HOST, PORT))
                connected = True
            except Exception as e:
                err_msg = str(e)

        threading.Thread(target=do_connect, daemon=True).start()
        dots = 0; dtimer = 0

        while True:
            t += 1; dtimer += 1
            if dtimer > 18: dots = (dots+1)%4; dtimer = 0
            w, h = self.screen.get_size()
            self.screen.fill(C_BG)
            draw_stars(self.screen, self.stars, t*0.4)

            cx, cy, rm = w//2, h//2, 155
            for ri in range(6): pygame.draw.circle(self.screen, C_OCEAN_LT, (cx,cy), rm-ri*24, 1)
            ang = (t*2.5) % 360; rad = math.radians(ang)
            for i in range(1, 65, 3):
                a2 = math.radians(ang-i)
                sx = cx+int(rm*math.cos(a2)); sy = cy+int(rm*math.sin(a2))
                al = int(115*(1-i/65))
                s = pygame.Surface((4,4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*C_GREEN, al), (2,2), 2)
                self.screen.blit(s, (sx-2,sy-2))
            pygame.draw.line(self.screen, C_GREEN, (cx,cy),
                             (cx+int(rm*math.cos(rad)), cy+int(rm*math.sin(rad))), 2)

            msg_t, col = ("CONNESSIONE IN CORSO"+"."*dots, C_GOLD) if not connected and not err_msg \
                    else (("CONNESSO  —  IN ATTESA AVVERSARIO...", C_GREEN) if connected \
                    else (f"ERRORE: {err_msg}", C_RED))
            mt = self.f_big.render(msg_t, True, col)
            self.screen.blit(mt, (w//2-mt.get_width()//2, cy+rm+38))
            sv = self.f_small.render(f"SERVER  {HOST}:{PORT}", True, C_DIM)
            self.screen.blit(sv, (w//2-sv.get_width()//2, cy+rm+80))
            nl = self.f_med.render(f"OPERATORE:  {self.player_name}", True, C_CYAN)
            self.screen.blit(nl, (w//2-nl.get_width()//2, cy-rm-58))
            draw_scanlines(self.screen); pygame.display.flip(); clock.tick(60)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

            if connected: pygame.time.delay(500); self._fade("out"); return
            if err_msg:   pygame.time.delay(3000); pygame.quit(); sys.exit()

    # ──────────────────────────────────────
    #  FADE
    # ──────────────────────────────────────
    def _fade(self, direction="out", steps=38):
        w, h = self.screen.get_size()
        fade = pygame.Surface((w,h)); fade.fill((0,0,0))
        rng = range(0,256,256//steps) if direction=="out" else range(255,-1,-256//steps)
        for a in rng:
            fade.set_alpha(a); self.screen.blit(fade,(0,0))
            pygame.display.update(); pygame.time.delay(7)

    # ──────────────────────────────────────
    #  CHAT: aggiungi messaggio
    # ──────────────────────────────────────
    def _chat_add(self, sender, text, kind="player"):
        with self._chat_lock:
            self.chat_messages.append({"sender": sender, "text": text, "kind": kind})
            # torna al fondo automaticamente
            self.chat_scroll = 0

    # ──────────────────────────────────────
    #  NETWORK LOOP
    # ──────────────────────────────────────
    def network_loop(self):
        while True:
            data = recv_message(self.sock)
            if data is None: break
            t = data.get("type")
            if t == "info":
                msg = data.get("msg","")
                if "Player 1" in msg: self.player_number = 1
                elif "Player 2" in msg: self.player_number = 2
            elif t == "ask_name":
                send_message(self.sock, {"type":"my_name","name": self.player_name})
            elif t == "name_ok":
                pass
            elif t == "leaderboard":
                self.leaderboard = data.get("data", [])
            elif t == "enemy_name":
                self.enemy_name = data.get("name","AVVERSARIO")
            elif t == "place_ships":
                self.placing = True
                self.placed_ships = []
                self.current_ship_idx = 0
                self.ship_orientation = "H"
                self.my_board = [["~"]*GRID_SIZE for _ in range(GRID_SIZE)]
                self.set_status("POSIZIONA LE TUE NAVI — R per ruotare", 0)
                break

        while True:
            data = recv_message(self.sock)
            if data is None: break
            t = data.get("type")

            if t == "ships_ok":
                self.placing = False
                self.set_status("NAVI PRONTE — IN ATTESA...", 0)

            elif t == "ships_error":
                self.set_status("ERRORE NAVI — RIPOSIZIONA", 3000)
                self.placed_ships = []
                self.current_ship_idx = 0
                self.ship_orientation = "H"
                self.my_board = [["~"]*GRID_SIZE for _ in range(GRID_SIZE)]
                self.placing = True

            elif t == "your_turn":
                self.turn_active = True
                self.set_status("FUOCO A PIACERE!", 2500)

            elif t == "chat":
                self._chat_add(
                    data.get("sender",""),
                    data.get("text",""),
                    data.get("kind","player")
                )

            elif t == "result":
                r = data.get("result"); x = data.get("x"); y = data.get("y")
                _, _, cs, _, ox_enemy, oy = self._layout()
                px = ox_enemy + y*cs + cs//2
                py = oy       + x*cs + cs//2
                if r in ("hit","win"):
                    self.enemy_board[x][y] = "X"
                    spawn_explosion(px,py,self.particles,C_HIT)
                    self.set_status("COLPITO!", 1800)
                elif r == "miss":
                    self.enemy_board[x][y] = "O"
                    spawn_splash(px,py,self.particles)
                    self.set_status("MANCATO", 1500)
                elif r == "already":
                    self.set_status("GIÀ COLPITA!", 1200); self.turn_active = True
                if r == "win":
                    self.game_over = True; self.winner = True

            elif t == "enemy_shot":
                x,y = data.get("x"),data.get("y"); res = data.get("result")
                _, _, cs, ox_my, _, oy = self._layout()
                px = ox_my + y*cs + cs//2
                py = oy    + x*cs + cs//2
                if res in ("hit","win"):
                    self.my_board[x][y] = "X"; spawn_explosion(px,py,self.particles,(200,50,20))
                else:
                    self.my_board[x][y] = "O"; spawn_splash(px,py,self.particles)

            elif t == "game_over":
                self.game_over = True; self.winner = data.get("winner")
                lb = data.get("leaderboard")
                if lb: self.leaderboard = lb
                break

        self.sock.close()

    def set_status(self, msg, dur):
        self.status_msg = msg; self.status_timer = dur

    # ──────────────────────────────────────
    #  HUD
    # ──────────────────────────────────────
    def draw_hud(self, w, h):
        draw_panel(self.screen, pygame.Rect(0,0,w,82), alpha=235, color=C_BG, radius=0)
        pygame.draw.line(self.screen, C_GOLD, (0,81), (w,81), 2)

        title = self.f_big.render("B A T T L E S H I P   10×10", True, C_GOLD)
        usable_cx = (w - CHAT_W) // 2
        self.screen.blit(title, (usable_cx - title.get_width()//2, 10))
        sub = self.f_small.render("NAVAL COMBAT  //  MULTIPLAYER", True, C_DIM)
        self.screen.blit(sub, (usable_cx - sub.get_width()//2, 46))

        pn = self.f_med.render(f"◈  {self.player_name}", True, C_CYAN)
        self.screen.blit(pn, (16, 18))
        pl = self.f_small.render(f"PLAYER {self.player_number}", True, C_DIM)
        self.screen.blit(pl, (18, 48))

        # stato turno — a sinistra del pannello chat
        chat_x = w - CHAT_W
        if self.placing:
            if self.current_ship_idx < len(FLEET):
                nm, ln, _ = FLEET[self.current_ship_idx]
                ori = "ORIZ." if self.ship_orientation=="H" else "VERT."
                st = f"{nm} ({ln})  [{ori}] R=ruota"
            else:
                st = "TUTTE LE NAVI PIAZZATE"
            sc = C_GOLD
        elif self.turn_active:
            st, sc = "● TUO TURNO", C_GREEN
        else:
            st, sc = "○ TURNO NEMICO", C_DIM
        sm = self.f_med.render(st, True, sc)
        self.screen.blit(sm, (chat_x - sm.get_width() - 16, 12))

        en = self.f_med.render(f"◈  {self.enemy_name}", True, (180,130,50))
        self.screen.blit(en, (chat_x - en.get_width() - 16, 46))

        if self.status_msg:
            smsg = self.f_med.render(self.status_msg, True, C_WHITE)
            sx = usable_cx - smsg.get_width()//2
            draw_panel(self.screen, pygame.Rect(sx-12,h-44,smsg.get_width()+24,32),
                       180, C_OCEAN, 6)
            self.screen.blit(smsg, (sx, h-41))

    # ──────────────────────────────────────
    #  PANNELLO CHAT
    # ──────────────────────────────────────
    def draw_chat(self, w, h):
        chat_x  = w - CHAT_W
        INPUT_H = 38
        HEADER_H = 32
        panel_h = h - 84   # sotto la HUD

        # sfondo pannello
        pr = pygame.Rect(chat_x, 82, CHAT_W, panel_h)
        draw_panel(self.screen, pr, alpha=230, color=(6,14,26), radius=0)
        pygame.draw.line(self.screen, C_GOLD, (chat_x, 82), (chat_x, h), 2)

        # intestazione
        header_r = pygame.Rect(chat_x, 82, CHAT_W, HEADER_H)
        draw_panel(self.screen, header_r, alpha=255, color=(10,22,42), radius=0)
        pygame.draw.line(self.screen, C_GRID, (chat_x, 82+HEADER_H), (w, 82+HEADER_H), 1)
        ht = self.f_chat_b.render("◎  COMUNICAZIONI", True, C_GOLD)
        self.screen.blit(ht, (chat_x + 10, 82 + (HEADER_H - ht.get_height())//2))

        # area messaggi (sopra input)
        msg_area_y = 82 + HEADER_H
        msg_area_h = panel_h - HEADER_H - INPUT_H - 2
        inner_w    = CHAT_W - 16

        # costruisci lista di righe renderizzate (dal più vecchio al più nuovo)
        rendered_lines = []   # (surface, kind)
        with self._chat_lock:
            msgs = list(self.chat_messages)
        for m in msgs:
            kind   = m["kind"]
            sender = m["sender"]
            text   = m["text"]
            # riga mittente (non per system)
            if kind != "system":
                is_me = (sender == self.player_name.upper())
                sc    = CHAT_COLORS["me"] if is_me else CHAT_COLORS["player"]
                prefix = "▶ " + sender if not is_me else sender + " ◀"
                s = self.f_chat_b.render(prefix[:26], True, sc)
                rendered_lines.append((s, kind, True))
            # righe testo (wrap)
            tc = CHAT_COLORS.get(kind, C_WHITE)
            for ln in wrap_text(self.f_chat, text, inner_w - 8):
                s = self.f_chat.render(ln, True, tc)
                rendered_lines.append((s, kind, False))
            # separatore leggero
            rendered_lines.append((None, kind, False))

        line_h   = self.f_chat.get_height() + 2
        total_h  = len(rendered_lines) * line_h
        max_scroll = max(0, total_h - msg_area_h)
        self.chat_scroll = max(0, min(self.chat_scroll, max_scroll))
        scroll_offset = max_scroll - self.chat_scroll  # 0 = in cima, max = in fondo

        # clip area messaggi
        clip = pygame.Rect(chat_x+2, msg_area_y, CHAT_W-4, msg_area_h)
        self.screen.set_clip(clip)
        cy = msg_area_y - scroll_offset
        for surf, kind, is_header in rendered_lines:
            if surf is not None:
                if is_header:
                    self.screen.blit(surf, (chat_x + 8, cy))
                else:
                    self.screen.blit(surf, (chat_x + 14, cy))
            cy += line_h
        self.screen.set_clip(None)

        # scrollbar
        if total_h > msg_area_h:
            sb_x = w - 6
            sb_h = max_scroll and int(msg_area_h * msg_area_h / total_h)
            sb_y = msg_area_y + int((msg_area_h - sb_h) * (max_scroll - self.chat_scroll) / max_scroll)
            pygame.draw.rect(self.screen, C_DIM, (sb_x, msg_area_y, 4, msg_area_h), border_radius=2)
            pygame.draw.rect(self.screen, C_GOLD, (sb_x, sb_y, 4, sb_h), border_radius=2)

        # box input
        input_y = 82 + panel_h - INPUT_H
        input_r = pygame.Rect(chat_x + 2, input_y + 2, CHAT_W - 4, INPUT_H - 4)
        bc = C_CYAN if self.chat_focused else C_DIM
        draw_panel(self.screen, input_r, alpha=200, color=C_OCEAN, radius=6)
        draw_border(self.screen, input_r, bc, 2, 6)

        # placeholder o testo
        if self.chat_input:
            display_text = self.chat_input[-28:]  # mostra ultimi 28 char
        else:
            display_text = ""
        cur = "|" if self.chat_focused and (self.chat_blink//30)%2==0 else " "
        it = self.f_chat.render(display_text + cur, True, C_WHITE if self.chat_input else C_DIM)
        self.screen.blit(it, (input_r.x + 8, input_r.y + (input_r.h - it.get_height())//2))

        if not self.chat_input and not self.chat_focused:
            ph = self.f_chat.render("Scrivi e premi Invio…", True, C_DIM)
            self.screen.blit(ph, (input_r.x + 8, input_r.y + (input_r.h - ph.get_height())//2))

        # etichetta invio
        hint = self.f_chat.render("[Enter] invia  [↑↓] scolla", True, (50,70,90))
        self.screen.blit(hint, (chat_x + 8, input_y - 14))

        return input_r  # restituisce il rettangolo per hit-test click

    # ──────────────────────────────────────
    #  PANNELLO FLOTTA (durante posizionamento)
    # ──────────────────────────────────────
    def draw_fleet_panel(self, w, h, oy, cs):
        chat_x  = w - CHAT_W
        panel_w = min(260, chat_x - 20)
        panel_x = chat_x - panel_w - 8
        row_h   = 34
        ph      = 20 + len(FLEET) * row_h + 16
        pr      = pygame.Rect(panel_x, oy, panel_w, ph)
        draw_panel(self.screen, pr, alpha=210, color=C_BG, radius=10)
        draw_border(self.screen, pr, C_GOLD, 1, radius=10)
        tl = self.f_med.render("FLOTTA", True, C_GOLD)
        self.screen.blit(tl, (panel_x+12, oy+6))
        pygame.draw.line(self.screen, C_GRID, (panel_x+8, oy+30), (panel_x+panel_w-8, oy+30), 1)

        for i, (nm, ln, col) in enumerate(FLEET):
            ry     = oy + 36 + i * row_h
            placed = i < self.current_ship_idx
            active = i == self.current_ship_idx
            if active:
                hs = pygame.Surface((panel_w-16, row_h-4), pygame.SRCALPHA)
                hs.fill((*C_CYAN, 18)); self.screen.blit(hs, (panel_x+8, ry-1))
            nc = C_GREEN if placed else (C_GOLD_LT if active else C_DIM)
            nt = self.f_small.render(("✓ " if placed else ("▶ " if active else "  ")) + nm, True, nc)
            self.screen.blit(nt, (panel_x+12, ry+4))
            for ci in range(ln):
                cr = pygame.Rect(panel_x + panel_w - 14 - (ln-ci)*13, ry+7, 11, 18)
                bc = col if placed or active else C_DIM
                pygame.draw.rect(self.screen, bc, cr, border_radius=2)
                if active: draw_border(self.screen, cr, C_WHITE, 1, 2)

    # ──────────────────────────────────────
    #  GRIGLIA
    # ──────────────────────────────────────
    def draw_grid(self, board, offset_x, oy, cs, label, is_enemy=False):
        gsz    = GRID_SIZE
        is_turn = is_enemy and self.turn_active and not self.placing

        lc = C_GOLD_LT if not is_enemy else (C_CYAN if is_turn else C_DIM)
        lt = self.f_med.render(label, True, lc)
        self.screen.blit(lt, (offset_x+(gsz*cs-lt.get_width())//2, oy-48))
        for i in range(gsz):
            c = self.f_small.render(chr(65+i), True, C_DIM)
            self.screen.blit(c, (offset_x+i*cs+(cs-c.get_width())//2, oy-24))
        for i in range(gsz):
            n = self.f_small.render(str(i+1), True, C_DIM)
            self.screen.blit(n, (offset_x-22, oy+i*cs+(cs-n.get_height())//2))

        gr = pygame.Rect(offset_x-2, oy-2, gsz*cs+4, gsz*cs+4)
        if is_turn: glow_rect(self.screen, gr, C_CYAN, 10)
        draw_border(self.screen, gr, C_GOLD if not is_enemy else (C_CYAN if is_turn else C_GRID), 2)

        mx_pos, my_pos = pygame.mouse.get_pos()
        for x in range(gsz):
            for y in range(gsz):
                r    = pygame.Rect(offset_x+y*cs, oy+x*cs, cs, cs)
                cell = board[x][y]
                if cell=="X":   pygame.draw.rect(self.screen, (68,18,8), r)
                elif cell=="O": pygame.draw.rect(self.screen, (18,38,68), r)
                elif board is self.my_board and cell=="S":
                    pygame.draw.rect(self.screen, (38,48,68), r)
                else:           pygame.draw.rect(self.screen, C_OCEAN, r)

                if cell=="~":
                    wy2 = int(2*math.sin(self.t*0.055+x*0.7+y*0.5))
                    ws  = pygame.Surface((cs,3), pygame.SRCALPHA)
                    ws.fill((*C_OCEAN_LT, 35))
                    self.screen.blit(ws, (r.x, r.y+cs//2+wy2))

                if board is self.my_board and cell=="S":
                    ri = r.inflate(-max(4,cs//6), -max(4,cs//6))
                    pygame.draw.rect(self.screen, C_SHIP_DK, ri, border_radius=3)
                    pygame.draw.rect(self.screen, C_SHIP, ri.inflate(-4,-4), border_radius=2)
                    if cs >= 38:
                        for wi in range(2):
                            wx2 = r.x+8+wi*14; wy3 = r.y+cs//2-3
                            pygame.draw.rect(self.screen, C_GOLD, (wx2,wy3,6,6), border_radius=1)
                elif cell=="X":
                    ri = r.inflate(-6,-6)
                    pygame.draw.line(self.screen, C_HIT, ri.topleft, ri.bottomright, 2)
                    pygame.draw.line(self.screen, C_HIT, ri.topright, ri.bottomleft, 2)
                    pygame.draw.circle(self.screen, C_GOLD, r.center, cs//5, 1)
                elif cell=="O":
                    pygame.draw.circle(self.screen, C_MISS, r.center, cs//4, 1)
                    pygame.draw.circle(self.screen, C_DIM,  r.center, cs//8)

                if is_enemy and not self.placing and self.turn_active:
                    if r.collidepoint(mx_pos, my_pos) and cell not in ("X","O"):
                        hs = pygame.Surface((cs,cs), pygame.SRCALPHA)
                        hs.fill((*C_CYAN, 45)); self.screen.blit(hs, r.topleft)
                        draw_border(self.screen, r, C_CYAN, 2)

                if board is self.my_board and self.placing:
                    if [x, y] in self.hover_cells:
                        col_h = C_GREEN if self.hover_valid else C_RED
                        hs = pygame.Surface((cs,cs), pygame.SRCALPHA)
                        hs.fill((*col_h, 80)); self.screen.blit(hs, r.topleft)
                        draw_border(self.screen, r, col_h, 2)

                pygame.draw.rect(self.screen, C_GRID, r, 1)

        if board is self.my_board and self.placing:
            bw = gsz*cs
            br = pygame.Rect(offset_x, oy+gsz*cs+12, bw, 8)
            pygame.draw.rect(self.screen, C_OCEAN_LT, br, border_radius=4)
            fw = int(bw * len(self.placed_ships) / len(FLEET))
            if fw > 0:
                pygame.draw.rect(self.screen, C_GOLD, (br.x,br.y,fw,8), border_radius=4)
            draw_border(self.screen, br, C_DIM, 1, radius=4)

    # ──────────────────────────────────────
    #  CLASSIFICA
    # ──────────────────────────────────────
    def draw_leaderboard(self, x, y, title="CLASSIFICA"):
        lb = self.leaderboard
        panel_w = 260; row_h = 22
        rows = min(len(lb), 8)
        ph = 50 + rows * row_h + 10
        pr = pygame.Rect(x, y, panel_w, ph)
        draw_panel(self.screen, pr, alpha=210, color=C_BG, radius=10)
        draw_border(self.screen, pr, C_GOLD, 1, radius=10)
        tl = self.f_med.render(f"▲  {title}", True, C_GOLD)
        self.screen.blit(tl, (x+12, y+10))
        pygame.draw.line(self.screen, C_GRID, (x+8,y+34), (x+panel_w-8,y+34), 1)
        for i, p in enumerate(lb[:8]):
            ry = y + 40 + i*row_h
            rc = [C_GOLD_LT,(190,190,190),(180,120,60)][i] if i<3 else C_DIM
            self.screen.blit(self.f_lb.render(f"#{i+1}", True, rc), (x+10, ry))
            self.screen.blit(self.f_lb.render(p["name"][:14], True, C_WHITE), (x+42, ry))
            stat = self.f_lb.render(f"{p['wins']}V  {p['losses']}S", True, C_DIM)
            self.screen.blit(stat, (x+panel_w-stat.get_width()-10, ry))
            if i%2==0:
                hs = pygame.Surface((panel_w-16, row_h-2), pygame.SRCALPHA)
                hs.fill((255,255,255,6)); self.screen.blit(hs, (x+8, ry-1))

    # ──────────────────────────────────────
    #  GAME OVER
    # ──────────────────────────────────────
    def draw_game_over(self, w, h):
        ov = pygame.Surface((w,h), pygame.SRCALPHA)
        ov.fill((0,0,0,185)); self.screen.blit(ov,(0,0))
        pulse = 0.5 + 0.5*math.sin(self.t*0.07)
        if self.winner:
            mt, col, sub, sc = "VITTORIA!", C_GOLD, "Hai affondato la flotta nemica", C_GREEN
            if random.random() < 0.08:
                spawn_explosion(random.randint(w//4,3*w//4),
                                random.randint(h//4,3*h//4),
                                self.particles, C_GOLD)
        else:
            mt, col, sub, sc = "SCONFITTA", C_RED, "La tua flotta è stata affondata", C_DIM
        pr = pygame.Rect(w//2-280, h//2-140, 560, 260)
        draw_panel(self.screen, pr, 225, C_BG, 16)
        glow_rect(self.screen, pr, col, 22)
        draw_border(self.screen, pr, col, 3, 16)
        try: big = pygame.font.SysFont("Orbitron", int(52+7*pulse), bold=True)
        except: big = self.f_big
        mt_s = big.render(mt, True, col)
        self.screen.blit(mt_s, (w//2-mt_s.get_width()//2, h//2-110))
        sub_s = self.f_med.render(sub, True, sc)
        self.screen.blit(sub_s, (w//2-sub_s.get_width()//2, h//2-22))
        hint = self.f_small.render("Premi ESC per uscire", True, C_DIM)
        self.screen.blit(hint, (w//2-hint.get_width()//2, h//2+50))
        if self.leaderboard:
            self.draw_leaderboard(w//2-130, h//2+90, "CLASSIFICA GLOBALE")

    # ──────────────────────────────────────
    #  POSIZIONAMENTO HOVER
    # ──────────────────────────────────────
    def _ship_cells(self, row, col, length, orientation):
        cells = []
        for i in range(length):
            cells.append([row, col + i] if orientation=="H" else [row + i, col])
        return cells

    def _cells_valid(self, cells):
        occupied = set()
        for ship in self.placed_ships:
            for c in ship: occupied.add((c[0], c[1]))
        for c in cells:
            r2, c2 = c
            if not (0 <= r2 < GRID_SIZE and 0 <= c2 < GRID_SIZE): return False
            if (r2, c2) in occupied: return False
        return True

    def _update_hover(self, mx, my, ox_my, oy, cs):
        if not self.placing or self.current_ship_idx >= len(FLEET):
            self.hover_cells = []; return
        col = (mx - ox_my) // cs; row = (my - oy) // cs
        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            _, length, _ = FLEET[self.current_ship_idx]
            cells = self._ship_cells(row, col, length, self.ship_orientation)
            self.hover_cells = cells
            self.hover_valid = self._cells_valid(cells)
        else:
            self.hover_cells = []

    # ──────────────────────────────────────
    #  CLICK
    # ──────────────────────────────────────
    def handle_click(self, pos, chat_input_rect):
        mx, my = pos

        # click sulla chat input box → focus
        if chat_input_rect and chat_input_rect.collidepoint(mx, my):
            self.chat_focused = True
            return
        else:
            self.chat_focused = False

        if self.game_over: return
        _, _, cs, ox_my, ox_enemy, oy = self._layout()

        if self.placing:
            if self.current_ship_idx >= len(FLEET): return
            col = (mx - ox_my) // cs; row = (my - oy) // cs
            if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                _, length, _ = FLEET[self.current_ship_idx]
                cells = self._ship_cells(row, col, length, self.ship_orientation)
                if self._cells_valid(cells):
                    self.placed_ships.append(cells)
                    for c in cells:
                        self.my_board[c[0]][c[1]] = "S"
                        px = ox_my + c[1]*cs + cs//2
                        py = oy    + c[0]*cs + cs//2
                        spawn_explosion(px, py, self.particles, C_SHIP)
                    self.current_ship_idx += 1
                    if self.current_ship_idx >= len(FLEET):
                        all_cells = [c for ship in self.placed_ships for c in ship]
                        send_message(self.sock, {"type":"ships","ships": all_cells})
                        self.set_status("NAVI INVIATE — IN ATTESA...", 0)
                else:
                    self.set_status("POSIZIONE NON VALIDA!", 1000)
            return

        if self.turn_active:
            col = (mx - ox_enemy) // cs; row = (my - oy) // cs
            if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                if self.enemy_board[row][col] in ("X","O"):
                    self.set_status("CELLA GIÀ COLPITA", 1200); return
                send_message(self.sock, {"type":"shot","x":row,"y":col})
                self.turn_active = False

    # ──────────────────────────────────────
    #  TOGGLE FULLSCREEN (F11)
    # ──────────────────────────────────────
    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode(
                (0,0), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        w, h = self.screen.get_size()
        self.stars = make_stars(w, h)

    # ──────────────────────────────────────
    #  MAIN LOOP
    # ──────────────────────────────────────
    def main_loop(self):
        clock = pygame.time.Clock()
        self._fade("in")
        chat_input_rect = None

        while True:
            dt = clock.tick(60); self.t += 1
            self.chat_blink += 1
            if self.status_timer > 0: self.status_timer -= dt
            else: self.status_msg = ""

            w, h, cs, ox_my, ox_enemy, oy = self._layout()

            self.screen.fill(C_BG)
            draw_stars(self.screen, self.stars, self.t*0.25)
            for xi in range(0, w, 3):
                yi = int(h*0.96 + 8*math.sin(xi*0.014 + self.t*0.022))
                pygame.draw.line(self.screen, C_OCEAN, (xi,yi), (xi,h), 1)

            mx, my = pygame.mouse.get_pos()
            if self.placing:
                self._update_hover(mx, my, ox_my, oy, cs)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.windowed_size = (ev.w, ev.h)
                        self.screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                        self.stars = make_stars(ev.w, ev.h)
                if ev.type == pygame.MOUSEWHEEL:
                    # scroll chat: positivo = su, negativo = giù
                    self.chat_scroll = max(0, self.chat_scroll + ev.y * 20)
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        if self.chat_focused:
                            self.chat_focused = False
                        else:
                            pygame.quit(); sys.exit()
                    if ev.key == pygame.K_F11:
                        self._toggle_fullscreen()

                    if self.chat_focused:
                        # input chat
                        if ev.key == pygame.K_RETURN:
                            txt = self.chat_input.strip()
                            if txt and self.sock:
                                send_message(self.sock, {"type":"chat","text": txt})
                            self.chat_input = ""
                        elif ev.key == pygame.K_BACKSPACE:
                            self.chat_input = self.chat_input[:-1]
                        elif ev.key == pygame.K_UP:
                            self.chat_scroll += 20
                        elif ev.key == pygame.K_DOWN:
                            self.chat_scroll = max(0, self.chat_scroll - 20)
                        elif ev.unicode and ev.unicode.isprintable():
                            if len(self.chat_input) < 120:
                                self.chat_input += ev.unicode
                    else:
                        # tasti di gioco
                        if ev.key == pygame.K_r and self.placing:
                            self.ship_orientation = "V" if self.ship_orientation=="H" else "H"
                        if ev.key == pygame.K_UP:
                            self.chat_scroll += 20
                        if ev.key == pygame.K_DOWN:
                            self.chat_scroll = max(0, self.chat_scroll - 20)

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1:
                        self.handle_click(ev.pos, chat_input_rect)
                    if ev.button == 3 and self.placing and not (chat_input_rect and chat_input_rect.collidepoint(*ev.pos)):
                        self.ship_orientation = "V" if self.ship_orientation=="H" else "H"

            # disegna griglie
            self.draw_grid(self.my_board,    ox_my,    oy, cs, f"◈ {self.player_name}", False)
            self.draw_grid(self.enemy_board, ox_enemy, oy, cs, f"◈ {self.enemy_name}",  True)

            if self.placing:
                self.draw_fleet_panel(w, h, oy, cs)

            # classifica in game (solo se c'è spazio tra le griglie e la chat)
            if self.leaderboard and not self.game_over and not self.placing:
                lb_x = ox_enemy + GRID_SIZE*cs + 10
                lb_max_x = w - CHAT_W - 10
                if lb_max_x - lb_x >= 180:
                    self.draw_leaderboard(lb_x, oy, "CLASSIFICA")

            for p in self.particles[:]:
                p.update(); p.draw(self.screen)
                if p.life <= 0: self.particles.remove(p)

            # HUD sopra tutto (tranne chat e game_over)
            self.draw_hud(w, h)

            # chat sempre visibile a destra
            chat_input_rect = self.draw_chat(w, h)

            draw_scanlines(self.screen)
            if self.game_over: self.draw_game_over(w, h)
            pygame.display.flip()


if __name__ == "__main__":
    BattleshipGUI()
