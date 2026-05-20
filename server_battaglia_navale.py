import socket
import json

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
            try:
                return json.loads(msg)
            except:
                print("[SERVER] Errore JSON, messaggio ignorato:", msg)
                continue

        chunk = sock.recv(1024)
        if not chunk:
            return None

        buffers[sock] += chunk.decode("utf-8")


class Game:
    def __init__(self):
        self.ships = []
        self.hits = []

    def set_ships(self, ships):
        # ships: lista di [x, y]
        self.ships = [tuple(s) for s in ships]

    def shoot(self, x, y):
        if (x, y) in self.hits:
            return "already"

        self.hits.append((x, y))

        if (x, y) in self.ships:
            if self.is_dead():
                return "win"
            return "hit"

        return "miss"

    def is_dead(self):
        return all(s in self.hits for s in self.ships)


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(2)

    print("[SERVER] In attesa di 2 giocatori...")

    players = []
    for i in range(2):
        c, addr = server.accept()
        players.append(c)
        send_message(c, {"type": "info", "msg": f"Sei il Player {i+1}"})
        print(f"[SERVER] Player {i+1} connesso da {addr}")

    games = [Game(), Game()]

    # POSIZIONAMENTO NAVI
    for i in range(2):
        send_message(players[i], {"type": "place_ships"})
        while True:
            data = recv_message(players[i])
            if data is None:
                print("[SERVER] Disconnessione durante posizionamento navi")
                return

            if data.get("type") == "ships":
                ships = data.get("ships", [])
                games[i].set_ships(ships)
                send_message(players[i], {"type": "ships_ok"})
                print(f"[SERVER] Navi Player {i+1}: {ships}")
                break

    print("[SERVER] PARTITA INIZIATA")
    turn = 0
    running = True

    while running:
        current = players[turn]
        enemy_game = games[1 - turn]
        other = players[1 - turn]

        send_message(current, {"type": "your_turn"})

        data = recv_message(current)
        if data is None:
            print("[SERVER] Disconnessione durante il gioco")
            break

        if data.get("type") != "shot":
            continue

        x = data.get("x")
        y = data.get("y")

        if not isinstance(x, int) or not isinstance(y, int):
            continue

        if not (0 <= x < 5 and 0 <= y < 5):
            send_message(current, {
                "type": "result",
                "result": "invalid",
                "x": x,
                "y": y
            })
            continue

        result = enemy_game.shoot(x, y)

        # Risultato al giocatore che spara
        send_message(current, {
            "type": "result",
            "result": result,
            "x": x,
            "y": y
        })

        # Notifica all'altro giocatore
        send_message(other, {
            "type": "enemy_shot",
            "x": x,
            "y": y,
            "result": result
        })

        if result == "win":
            send_message(current, {"type": "game_over", "winner": True})
            send_message(other, {"type": "game_over", "winner": False})
            print("[SERVER] GAME OVER")
            running = False

        elif result == "miss":
            # Cambio turno solo se è mancato
            turn = 1 - turn

    for p in players:
        try:
            p.close()
        except:
            pass

    server.close()
    print("[SERVER] Chiuso.")


if __name__ == "__main__":
    main()
