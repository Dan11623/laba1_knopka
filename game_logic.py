import socket
import threading
import tkinter as tk
from tkinter import messagebox

# Настройки сети
PORT_UDP = 6769
PORT_TCP = 7696


class BattleshipGame:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Морской бой по сети")
        self.root.geometry("700x450")
        self.root.resizable(False, False)
        self.tcp_sock = None
        self.conn = None
        self.my_turn = False  # Флаг текущего хода

        # Матрицы полей: 0 - пусто, 1 - корабль, 2 - мимо, 3 - попал
        self.my_field = [[0] * 10 for _ in range(10)]
        self.enemy_field = [[0] * 10 for _ in range(10)]
        self.generate_random_ships()
        self.create_welcome_screen()

    def generate_random_ships(self):
        # Расставляем 6 случайных одиночных кораблей
        import random
        count = 0
        while count < 6:
            r = random.randint(0, 9)
            c = random.randint(0, 9)
            if self.my_field[r][c] == 0:
                self.my_field[r][c] = 1
                count += 1

    def create_welcome_screen(self):
        """Экран выбора режима подключения"""
        self.welcome_frame = tk.Frame(self.root)
        self.welcome_frame.pack(expand=True)
        tk.Label(self.welcome_frame, text="МОРСКОЙ БОЙ", font=("Arial", 24, "bold")).pack(pady=20)
        btn_server = tk.Button(self.welcome_frame, text="Создать игру (Сервер)", font=("Arial", 14), width=25,
                               command=self.start_server_mode)
        btn_server.pack(pady=10)
        btn_client = tk.Button(self.welcome_frame, text="Найти игру (Клиент)", font=("Arial", 14), width=25,
                               command=self.start_client_mode)
        btn_client.pack(pady=10)

    # ==================== СЕТЕВАЯ ЛОГИКА ====================
    def start_server_mode(self):
        self.welcome_frame.pack_forget()
        self.status_label = tk.Label(self.root, text="Ожидание подключения соперника...", font=("Arial", 14))
        self.status_label.pack(expand=True)
        threading.Thread(target=self.server_network_loop, daemon=True).start()

    def server_network_loop(self):
        # 1. UDP-поток: отвечаем на КАЖДЫЙ DISCOVER, пока не придёт TCP.
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(('', PORT_UDP))
        udp_sock.settimeout(0.3)
        stop = threading.Event()

        def udp_worker():
            while not stop.is_set():
                try:
                    data, addr = udp_sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if data == b"DISCOVER_BATTLESHIP":
                    try:
                        udp_sock.sendto(b"HERE_IS_BATTLESHIP_SERVER", addr)
                    except OSError:
                        pass

        threading.Thread(target=udp_worker, daemon=True).start()

        # 2. Ожидание TCP соединения
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind(('', PORT_TCP))
        self.tcp_sock.listen(1)
        self.conn, addr = self.tcp_sock.accept()
        stop.set()
        udp_sock.close()

        # Сервер ходит первым
        self.my_turn = True
        self.root.after(0, self.start_game_ui)

    def start_client_mode(self):
        self.welcome_frame.pack_forget()
        self.status_label = tk.Label(self.root, text="Поиск игры в локальной сети...", font=("Arial", 14))
        self.status_label.pack(expand=True)
        threading.Thread(target=self.client_network_loop, daemon=True).start()

    def client_network_loop(self):
        # 1. Узнаём свой IP, чтобы послать направленный broadcast в свою подсеть
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("10.255.255.255", 1))
            my_ip = probe.getsockname()[0]
        except OSError:
            my_ip = None
        finally:
            probe.close()

        targets = ["255.255.255.255"]
        if my_ip:
            targets.append(my_ip.rsplit(".", 1)[0] + ".255")

        # 2. UDP broadcast: 20 попыток × 2 адреса
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if my_ip:
            try:
                udp_sock.bind((my_ip, 0))  # пакет уйдёт через нужный адаптер
            except OSError:
                pass
        udp_sock.settimeout(0.5)

        server_ip = None
        try:
            for _ in range(20):
                for t in targets:
                    try:
                        udp_sock.sendto(b"DISCOVER_BATTLESHIP", (t, PORT_UDP))
                    except OSError:
                        pass
                try:
                    data, addr = udp_sock.recvfrom(1024)
                    if data == b"HERE_IS_BATTLESHIP_SERVER":
                        server_ip = addr[0]
                        break
                except socket.timeout:
                    continue
        finally:
            udp_sock.close()

        if not server_ip:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", "Игра не найдена! Проверьте сеть."))
            self.root.after(0, self.reset_to_welcome)
            return

        # 3. Подключение по TCP
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.conn.connect((server_ip, PORT_TCP))
            self.my_turn = False  # Клиент ходит вторым
            self.root.after(0, self.start_game_ui)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось подключиться: {e}"))
            self.root.after(0, self.reset_to_welcome)

    def reset_to_welcome(self):
        self.status_label.pack_forget()
        self.create_welcome_screen()

    # ==================== ИНТЕРФЕЙС ИГРЫ ====================
    def start_game_ui(self):
        self.status_label.pack_forget()
        self.game_frame = tk.Frame(self.root)
        self.game_frame.pack(pady=10)
        self.turn_label = tk.Label(self.root, text="", font=("Arial", 14, "bold"))
        self.turn_label.pack(pady=5)
        self.update_turn_label()

        # Моё поле (слева)
        my_frame = tk.Frame(self.game_frame)
        my_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(my_frame, text="Моё поле", font=("Arial", 12)).pack()
        self.my_buttons = [[None] * 10 for _ in range(10)]
        grid_my = tk.Frame(my_frame)
        grid_my.pack()
        for r in range(10):
            for c in range(10):
                color = "#708090" if self.my_field[r][c] == 1 else "#E0F7FA"
                btn = tk.Button(grid_my, width=2, height=1, bg=color, state="disabled")
                btn.grid(row=r, column=c)
                self.my_buttons[r][c] = btn

        # Поле противника (справа)
        enemy_frame = tk.Frame(self.game_frame)
        enemy_frame.pack(side=tk.RIGHT, padx=20)
        tk.Label(enemy_frame, text="Поле противника", font=("Arial", 12)).pack()
        self.enemy_buttons = [[None] * 10 for _ in range(10)]
        grid_enemy = tk.Frame(enemy_frame)
        grid_enemy.pack()
        for r in range(10):
            for c in range(10):
                btn = tk.Button(grid_enemy, width=2, height=1, bg="#E0F7FA",
                                command=lambda row=r, col=c: self.on_enemy_cell_click(row, col))
                btn.grid(row=r, column=c)
                self.enemy_buttons[r][c] = btn

        self.conn.setblocking(False)
        self.check_network()

    def update_turn_label(self):
        if self.my_turn:
            self.turn_label.config(text="ВАШ ХОД", fg="green")
        else:
            self.turn_label.config(text="ХОД СОПЕРНИКА", fg="red")

    # ==================== ЛОГИКА ИГРЫ ====================
    def on_enemy_cell_click(self, r, c):
        if not self.my_turn:
            return
        if self.enemy_field[r][c] != 0:
            return
        try:
            msg = f"SHOT:{r},{c}"
            self.conn.sendall(msg.encode('utf-8'))
            self.my_turn = False
            self.update_turn_label()
        except Exception:
            messagebox.showerror("Ошибка", "Связь потеряна.")

    def check_network(self):
        try:
            data = self.conn.recv(1024)
            if data:
                msg = data.decode('utf-8')
                self.process_network_message(msg)
        except BlockingIOError:
            pass
        except Exception:
            messagebox.showerror("Ошибка", "Соединение разорвано.")
            self.root.destroy()
            return
        self.root.after(100, self.check_network)

    def process_network_message(self, msg):
        if msg.startswith("SHOT:"):
            coords = msg.split(":")
            r, c = map(int, coords[1].split(","))
            if self.my_field[r][c] == 1:  # Попал
                self.my_field[r][c] = 3
                self.my_buttons[r][c].config(bg="red", text="X")
                self.conn.sendall(f"RES:{r},{c},HIT".encode('utf-8'))
                self.my_turn = False
                self.check_game_over_loss()
            else:  # Мимо
                self.my_field[r][c] = 2
                self.my_buttons[r][c].config(bg="#B0BEC5", text="•")
                self.conn.sendall(f"RES:{r},{c},MISS".encode('utf-8'))
                self.my_turn = True
        elif msg.startswith("RES:"):
            # Формат ответа: RES:строка,столбец,результат (без пробелов)
            parts = msg.split(":")[1].split(",")
            r, c = int(parts[0]), int(parts[1])
            result = parts[2]
            if result == "HIT":
                self.enemy_field[r][c] = 3
                self.enemy_buttons[r][c].config(bg="red", text="X")
                self.my_turn = True
            else:
                self.enemy_field[r][c] = 2
                self.enemy_buttons[r][c].config(bg="#B0BEC5", text="•")
                self.my_turn = False
        # Обновляем надпись хода после любого сообщения
        self.update_turn_label()

    def check_game_over_loss(self):
        for row in self.my_field:
            if 1 in row:
                return

        messagebox.showinfo("Игра окончена", "Вы проиграли! Все ваши корабли уничтожены.")
        self.root.destroy()
