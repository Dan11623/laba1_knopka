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
        pass  # Будет реализовано позже

    def start_client_mode(self):
        pass  # Будет реализовано позже
