import socket
import threading
import tkinter as tk
from tkinter import messagebox

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
        self.my_turn = False
        self.my_field = [[0] * 10 for _ in range(10)]
        self.enemy_field = [[0] * 10 for _ in range(10)]
        self.generate_random_ships()
        self.create_welcome_screen()

    def generate_random_ships(self):
        import random
        count = 0
        while count < 6:
            r = random.randint(0, 9)
            c = random.randint(0, 9)
            if self.my_field[r][c] == 0:
                self.my_field[r][c] = 1
                count += 1

    def create_welcome_screen(self):
        self.welcome_frame = tk.Frame(self.root)
        self.welcome_frame.pack(expand=True)
        tk.Label(self.welcome_frame, text="МОРСКОЙ БОЙ", font=("Arial", 24, "bold")).pack(pady=20)
        btn_server = tk.Button(self.welcome_frame, text="Создать игру (Сервер)", font=("Arial", 14), width=25, command=self.start_server_mode)
        btn_server.pack(pady=10)
        btn_client = tk.Button(self.welcome_frame, text="Найти игру (Клиент)", font=("Arial", 14), width=25, command=self.start_client_mode)
        btn_client.pack(pady=10)

    def start_server_mode(self):
        self.welcome_frame.pack_forget()
        self.status_label = tk.Label(self.root, text="Ожидание подключения соперника...", font=("Arial", 14))
        self.status_label.pack(expand=True)
        threading.Thread(target=self.server_network_loop, daemon=True).start()

    def server_network_loop(self):
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(('', PORT_UDP))
        udp_sock.settimeout(0.3)
        stop = threading.Event()
        def udp_worker():
            while not stop.is_set():
                try: data, addr = udp_sock.recvfrom(1024)
                except socket.timeout: continue
                except OSError: break
                if data == b"DISCOVER_BATTLESHIP":
                    try: udp_sock.sendto(b"HERE_IS_BATTLESHIP_SERVER", addr)
                    except OSError: pass
        threading.Thread(target=udp_worker, daemon=True).start()

        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind(('', PORT_TCP))
        self.tcp_sock.listen(1)
        self.conn, addr = self.tcp_sock.accept()
        stop.set()
        udp_sock.close()
        self.my_turn = True
        # Ссылка на интерфейс игры появится в следующем коммите

    def start_client_mode(self):
        self.welcome_frame.pack_forget()
        self.status_label = tk.Label(self.root, text="Поиск игры в локальной сети...", font=("Arial", 14))
        self.status_label.pack(expand=True)
        threading.Thread(target=self.client_network_loop, daemon=True).start()

    def client_network_loop(self):
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("10.255.255.255", 1))
            my_ip = probe.getsockname()[0]
        except OSError: my_ip = None
        finally: probe.close()
        targets = ["255.255.255.255"]
        if my_ip: targets.append(my_ip.rsplit(".", 1)[0] + ".255")

        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if my_ip:
            try: udp_sock.bind((my_ip, 0))
            except OSError: pass
        udp_sock.settimeout(0.5)
        server_ip = None
        try:
            for _ in range(20):
                for t in targets:
                    try: udp_sock.sendto(b"DISCOVER_BATTLESHIP", (t, PORT_UDP))
                    except OSError: pass
                try:
                    data, addr = udp_sock.recvfrom(1024)
                    if data == b"HERE_IS_BATTLESHIP_SERVER":
                        server_ip = addr[0]
                        break
                except socket.timeout: continue
        finally: udp_sock.close()

        if not server_ip:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", "Игра не найдена! Проверьте сеть."))
            self.root.after(0, self.reset_to_welcome)
            return

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.conn.connect((server_ip, PORT_TCP))
            self.my_turn = False
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось подключиться: {e}"))
            self.root.after(0, self.reset_to_welcome)

    def reset_to_welcome(self):
        self.status_label.pack_forget()
        self.create_welcome_screen()
