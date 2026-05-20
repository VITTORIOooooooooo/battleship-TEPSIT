import socket
import json
import os
import threading

HOST = "127.0.0.1"
PORT = 50005
LEADERBOARD_FILE = "leaderboard.json"
GRID_SIZE = 10
MAX_SHIPS = 17  # 5+4+3+3+2 celle totali della flotta classica

buffers  = {}
buf_lock = threading.Lock()

# ─────────────────────────────────────────────
#  RETE
# ─────────────────────────────────────────────
def send_message(sock, data):
    try:
        sock.sendall((json.dumps(data) + "\n").encode("utf-8"))
    except Exception:
        pass

def recv_message(sock):
    with buf_lock:
        if sock not in buffers:
            buffers[sock] = ""
    while True:
        with buf_lock:
            buf = buffers.get(sock, "")
        if "\n" in buf:
            with buf_lock:
                line, buffers[sock] = buffers[sock].split("\n", 1)
            try:
                return json.loads(line)
            except Exception:
                continue
        try:
            chunk = sock.recv(4096)
        except Exception:
            return None
        if not chunk:
            return None
        with buf_lock:
            buffers[sock] = buffers.get(sock, "") + chunk.decode("utf-8", errors="replace")

# ─────────────────────────────────────────────
#  LEADERBOARD
# ─────────────────────────────────────────────
def load_lb():
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_lb(lb):
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(lb, f, indent=2, ensure_ascii=False)

def update_lb(winner, loser):
    lb = load_lb()
    for n in [winner, loser]:
        if n not in lb:
            lb[n] = {"wins": 0, "losses": 0, "games": 0}
    lb[winner]["wins"]  += 1
    lb[winner]["games"] += 1
    lb[loser]["losses"] += 1
    lb[loser]["games"]  += 1
    save_lb(lb)
    return lb

def top_players(lb, n=15):
    ranked = sorted(lb.items(),
                    key=lambda x: (x[1]["wins"], -x[1]["losses"]),
                    reverse=True)
    return [{"name": k, **v} for k, v in ranked[:n]]

# ─────────────────────────────────────────────
#  GIOCO
# ─────────────────────────────────────────────
class Game:
    def __init__(self):
        self.ships = []
        self.hits  = []

    def set_ships(self, ships):
        self.ships = [tuple(s) for s in ships]

    def shoot(self, x, y):
        if (x, y) in self.hits:
            return "already"
        self.hits.append((x, y))
        if (x, y) in self.ships:
            return "win" if self.is_dead() else "hit"
        return "miss"

    def is_dead(self):
        return all(s in self.hits for s in self.ships)

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(2)
    print(f"[SERVER] In attesa su {HOST}:{PORT}  |  {GRID_SIZE}x{GRID_SIZE}, {MAX_SHIPS} navi")

    players = []
    names   = ["ANONIMO", "ANONIMO"]

    # ── connessione e scambio nomi ──
    for i in range(2):
        c, addr = server.accept()
        players.append(c)
        send_message(c, {"type": "info", "msg": f"Sei il Player {i+1}"})
        print(f"[SERVER] Player {i+1} connesso da {addr}")
        send_message(c, {"type": "ask_name"})
        while True:
            d = recv_message(c)
            if d and d.get("type") == "my_name":
                names[i] = d.get("name", "ANONIMO").strip().upper() or "ANONIMO"
                lb = load_lb()
                send_message(c, {"type": "name_ok"})
                send_message(c, {"type": "leaderboard", "data": top_players(lb)})
                print(f"[SERVER] Benvenuto {names[i]}")
                break

    send_message(players[0], {"type": "enemy_name", "name": names[1]})
    send_message(players[1], {"type": "enemy_name", "name": names[0]})

    def broadcast(msg):
        send_message(players[0], msg)
        send_message(players[1], msg)

    # ── posizionamento navi ──
    # Raccoglie le navi da entrambi i giocatori PRIMA di procedere
    # Usiamo due Game objects inizializzati qui
    games = [Game(), Game()]
    ship_sets = [None, None]

    for i in range(2):
        send_message(players[i], {"type": "place_ships"})

    for i in range(2):
        while True:
            d = recv_message(players[i])
            if d is None:
                print("[SERVER] Disconnessione durante posizionamento")
                return
            if d.get("type") == "ships":
                ships = d.get("ships", [])
                valid = [s for s in ships
                         if isinstance(s, list) and len(s) == 2
                         and 0 <= s[0] < GRID_SIZE and 0 <= s[1] < GRID_SIZE]
                if len(valid) != MAX_SHIPS:
                    send_message(players[i], {"type": "ships_error"})
                    continue
                games[i].set_ships(valid)
                send_message(players[i], {"type": "ships_ok"})
                print(f"[SERVER] Navi {names[i]}: OK ({MAX_SHIPS})")
                break

    print("[SERVER] ══ PARTITA INIZIATA ══")
    broadcast({"type": "chat", "sender": "SISTEMA",
               "text": "⚓ La battaglia ha inizio!", "kind": "system"})
    broadcast({"type": "chat", "sender": "SISTEMA",
               "text": f"⚔  {names[0]}  VS  {names[1]}", "kind": "system"})

    turn    = 0
    running = True

    while running:
        current    = players[turn]
        enemy_game = games[1 - turn]
        other      = players[1 - turn]
        attacker   = names[turn]

        send_message(current, {"type": "your_turn"})

        # Il giocatore corrente può sparare O inviare chat
        while True:
            d = recv_message(current)
            if d is None:
                print("[SERVER] Disconnessione in gioco")
                running = False
                break

            if d.get("type") == "chat":
                text = str(d.get("text", ""))[:200]
                broadcast({"type": "chat", "sender": names[turn],
                           "text": text, "kind": "player"})
                # non consumiamo il turno, ridiamo il controllo
                continue

            if d.get("type") == "shot":
                break   # esce dal loop interno

        if not running:
            break

        # gestione chat dall'altro giocatore mentre aspetta
        # (è non-bloccante perché il server legge sequenzialmente;
        #  i messaggi di chat dell'altro arriveranno al prossimo recv)

        x = d.get("x"); y = d.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            continue
        if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
            send_message(current, {"type": "result", "result": "invalid", "x": x, "y": y})
            continue

        result = enemy_game.shoot(x, y)
        col_lbl = chr(65 + y)
        coord   = f"{col_lbl}{x+1}"

        send_message(current, {"type": "result",     "result": result, "x": x, "y": y})
        send_message(other,   {"type": "enemy_shot", "result": result, "x": x, "y": y})

        # azione in chat
        if result == "miss":
            broadcast({"type": "chat", "sender": "SISTEMA",
                       "text": f"💦  {attacker}  →  {coord}  ACQUA",
                       "kind": "action_miss"})
            turn = 1 - turn
        elif result == "hit":
            broadcast({"type": "chat", "sender": "SISTEMA",
                       "text": f"🔥  {attacker}  →  {coord}  COLPITO!",
                       "kind": "action_hit"})
            # turno rimane al giocatore che ha colpito
        elif result == "win":
            broadcast({"type": "chat", "sender": "SISTEMA",
                       "text": f"💥  {attacker}  →  {coord}  AFFONDATA!  VITTORIA!",
                       "kind": "action_win"})
            lb  = update_lb(attacker, names[1 - turn])
            top = top_players(lb)
            send_message(current, {"type": "game_over", "winner": True,  "leaderboard": top})
            send_message(other,   {"type": "game_over", "winner": False, "leaderboard": top})
            broadcast({"type": "leaderboard", "data": top})
            print(f"[SERVER] ══ {attacker} VINCE ══")
            running = False
        elif result == "already":
            # restituisci il turno senza cambiarlo
            pass

    for p in players:
        try: p.close()
        except: pass
    server.close()
    print("[SERVER] Chiuso.\n")


if __name__ == "__main__":
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("\n[SERVER] Terminato.")
            break
        except Exception as e:
            import traceback; traceback.print_exc()
            import time; time.sleep(2)
            print("[SERVER] Riavvio...")