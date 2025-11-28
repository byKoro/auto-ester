"""
Auto Ester - Macro Triple Box v3.0
Funcionalidades completas:
- Três caixas de texto independentes
- Captura de teclas sem travamento
- Salvar/Carregar configurações
- Tema Dark/Light
- Controle de velocidade
- Loop multi-etapas

Dependências: 
pip install pynput pyperclip
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
import pyperclip
import platform
import json
import os
from pynput import keyboard as pynput_kb
from pynput.keyboard import Key, Controller

# ======================================================================
# Funções utilitárias
# ======================================================================

def press_combination(controller, combo_str):
    """Envia a combinação de teclas ao SO usando pynput."""
    if not combo_str:
        return

    parts = combo_str.split("+")
    modifiers = []
    keys = []

    modifier_map = {
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "shift": Key.shift, "alt": Key.alt,
        "cmd": Key.cmd, "command": Key.cmd, "win": Key.cmd
    }

    special_map = {
        "enter": Key.enter, "return": Key.enter, "space": Key.space,
        "tab": Key.tab, "esc": Key.esc, "escape": Key.esc,
        "delete": Key.delete, "del": Key.delete,
        "backspace": Key.backspace, "up": Key.up,
        "down": Key.down, "left": Key.left, "right": Key.right,
        "home": Key.home, "end": Key.end,
        "pageup": Key.page_up, "pagedown": Key.page_down,
        "insert": Key.insert
    }

    for p in parts:
        p = p.strip().lower()
        
        if p in modifier_map:
            modifiers.append(modifier_map[p])
        elif p in special_map:
            keys.append(special_map[p])
        elif p.startswith("f") and len(p) <= 3 and p[1:].isdigit():
            try:
                keys.append(getattr(Key, p))
            except AttributeError:
                pass
        elif len(p) == 1:
            keys.append(p)

    for m in modifiers:
        controller.press(m)
    time.sleep(0.02)

    for k in keys:
        try:
            controller.press(k)
            time.sleep(0.02)
            controller.release(k)
        except Exception as e:
            print(f"Erro ao pressionar tecla {k}: {e}")

    time.sleep(0.02)
    for m in reversed(modifiers):
        controller.release(m)
    time.sleep(0.05)


def paste_clipboard(controller):
    """Simula Ctrl+V ou Cmd+V conforme o sistema."""
    if platform.system() == "Darwin":
        controller.press(Key.cmd)
        controller.press('v')
        controller.release('v')
        controller.release(Key.cmd)
    else:
        controller.press(Key.ctrl)
        controller.press('v')
        controller.release('v')
        controller.release(Key.ctrl)
    time.sleep(0.05)


# ======================================================================
# Classe principal da aplicação Auto Ester
# ======================================================================

class AutoEsterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Ester v3.0 - Macro Automatizada")
        self.root.geometry("1050x750")
        self.controller = Controller()

        # Estados
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.running = False
        self.dark_mode = False

        # Velocidade (delay em segundos)
        self.speed = tk.DoubleVar(value=0.1)

        # Captura de teclas
        self.capturing = False
        self.captured_keys = set()
        self.capture_target_entry = None
        self.capture_listener = None

        # Teclas
        self.key_after_b1 = ""
        self.key_after_b2 = ""
        self.key_after_b3 = ""
        self.global_start_key = ""
        self.global_stop_key = ""

        # Linhas
        self.lines_b1 = []
        self.lines_b2 = []
        self.lines_b3 = []

        # Arquivo de configuração
        self.config_file = "auto_ester_config.json"

        # Construir interface
        self.build_ui()

        # Valores padrão
        self.entry_start.insert(0, "f11")
        self.entry_stop.insert(0, "f12")
        self.entry_after1.insert(0, "enter")
        self.entry_after2.insert(0, "enter")
        self.entry_after3.insert(0, "enter")

        # Carregar configuração salva (se existir)
        self.load_config()

        # Listener global
        self.global_listener = pynput_kb.Listener(on_press=self.on_global_press)
        self.global_listener.start()

        # Protocolo de fechamento
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ==================================================================
    # Interface
    # ==================================================================

    def build_ui(self):
        pad = 8
        main = ttk.Frame(self.root, padding=pad)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Header com botões de controle
        header_frame = ttk.Frame(main)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(header_frame, text="🚀 Auto Ester v3.0", 
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        # Botões à direita
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="💾 Salvar Config", 
                  command=self.save_config, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📂 Carregar Config", 
                  command=self.load_config, width=15).pack(side=tk.LEFT, padx=2)

        # Controle de velocidade
        speed_frame = ttk.LabelFrame(main, text="⚡ Velocidade de Execução", padding=8)
        speed_frame.grid(row=1, column=0, sticky="ew", pady=5, padx=4)

        ttk.Label(speed_frame, text="Rápido").pack(side=tk.LEFT, padx=5)
        
        self.speed_scale = ttk.Scale(speed_frame, from_=0.01, to=0.5, 
                                     variable=self.speed, orient=tk.HORIZONTAL, length=300)
        self.speed_scale.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(speed_frame, text="Lento").pack(side=tk.LEFT, padx=5)
        
        self.speed_label = ttk.Label(speed_frame, text="Delay: 0.10s")
        self.speed_label.pack(side=tk.LEFT, padx=10)
        
        self.speed.trace('w', self.update_speed_label)

        # Boxes
        frame_boxes = ttk.Frame(main)
        frame_boxes.grid(row=2, column=0, pady=4)

        self.use_b1 = tk.BooleanVar(value=True)
        self.use_b2 = tk.BooleanVar(value=True)
        self.use_b3 = tk.BooleanVar(value=True)

        self.box1 = self.make_box(frame_boxes, 0, "📦 Box 1", self.use_b1)
        self.box2 = self.make_box(frame_boxes, 1, "📦 Box 2", self.use_b2)
        self.box3 = self.make_box(frame_boxes, 2, "📦 Box 3", self.use_b3)

        # Teclas após cada Box
        config = ttk.LabelFrame(main, text="⌨️ Teclas após cada Box", padding=10)
        config.grid(row=3, column=0, sticky="ew", pady=8, padx=4)

        self.entry_after1 = self.make_key_capture(config, 0, "Após Box 1:")
        self.entry_after2 = self.make_key_capture(config, 1, "Após Box 2:")
        self.entry_after3 = self.make_key_capture(config, 2, "Após Box 3:")

        # Teclas globais
        global_frame = ttk.LabelFrame(main, text="🎮 Teclas globais (Start/Stop)", padding=10)
        global_frame.grid(row=4, column=0, sticky="ew", pady=8, padx=4)

        self.entry_start = self.make_key_capture(global_frame, 0, "🟢 Iniciar global:")
        self.entry_stop = self.make_key_capture(global_frame, 1, "🔴 Parar global:")

        # Controles
        ctrl = ttk.Frame(main)
        ctrl.grid(row=5, pady=12)

        ttk.Button(ctrl, text="▶️ Iniciar", 
                  command=self.start_macro, width=18).grid(row=0, column=0, padx=6)
        ttk.Button(ctrl, text="⏹️ Parar", 
                  command=self.stop_macro, width=18).grid(row=0, column=1, padx=6)

        # Status
        status_frame = ttk.Frame(main)
        status_frame.grid(row=6, pady=5)
        
        self.status = tk.StringVar(value="⚪ Aguardando... (F11 para iniciar)")
        self.status_label = ttk.Label(status_frame, textvariable=self.status, 
                                      font=("Arial", 10, "bold"))
        self.status_label.pack()

        # Instruções
        info = ttk.LabelFrame(main, text="ℹ️ Instruções", padding=8)
        info.grid(row=7, column=0, sticky="ew", pady=8, padx=4)
        
        instructions = """1. Cole o conteúdo nas caixas (uma linha por entrada) | 2. Configure teclas após cada box
3. Ajuste a velocidade | 4. Salve suas configurações | 5. Use F11/F12 ou botões manuais"""
        
        self.info_label = ttk.Label(info, text=instructions, justify=tk.LEFT)
        self.info_label.pack()

    def make_box(self, master, col, label, var):
        frame = ttk.LabelFrame(master, text=label, padding=5)
        frame.grid(row=0, column=col, padx=4)

        box = scrolledtext.ScrolledText(frame, width=32, height=10, wrap=tk.WORD)
        box.pack(pady=3)

        ttk.Checkbutton(frame, text="✓ Usar", variable=var).pack()
        return box

    def make_key_capture(self, master, row, text):
        ttk.Label(master, text=text).grid(row=row, column=0, sticky="w", padx=5, pady=4)

        entry = tk.Entry(master, width=25, font=("Courier", 10))
        entry.grid(row=row, column=1, padx=5)

        btn = ttk.Button(master, text="🎯 Capturar", 
                        command=lambda e=entry: self.capture_key(e), width=12)
        btn.grid(row=row, column=2, padx=5)

        return entry

    def update_speed_label(self, *args):
        """Atualiza o label de velocidade"""
        self.speed_label.config(text=f"Delay: {self.speed.get():.2f}s")

    # ==================================================================
    # Tema Dark/Light
    # ==================================================================

    # ==================================================================
    # Salvar/Carregar Configurações
    # ==================================================================

    def save_config(self):
        """Salva todas as configurações em arquivo JSON"""
        try:
            config = {
                "version": "3.0",
                "speed": self.speed.get(),
                "dark_mode": self.dark_mode,
                "keys": {
                    "start": self.entry_start.get(),
                    "stop": self.entry_stop.get(),
                    "after1": self.entry_after1.get(),
                    "after2": self.entry_after2.get(),
                    "after3": self.entry_after3.get()
                },
                "boxes": {
                    "box1_enabled": self.use_b1.get(),
                    "box2_enabled": self.use_b2.get(),
                    "box3_enabled": self.use_b3.get(),
                    "box1_content": self.box1.get("1.0", tk.END),
                    "box2_content": self.box2.get("1.0", tk.END),
                    "box3_content": self.box3.get("1.0", tk.END)
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Sucesso", f"Configuração salva em:\n{self.config_file}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configuração:\n{e}")

    def load_config(self):
        """Carrega configurações do arquivo JSON"""
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Carregar velocidade
            self.speed.set(config.get("speed", 0.1))
            
            # Carregar teclas
            keys = config.get("keys", {})
            self.entry_start.delete(0, tk.END)
            self.entry_start.insert(0, keys.get("start", "f11"))
            
            self.entry_stop.delete(0, tk.END)
            self.entry_stop.insert(0, keys.get("stop", "f12"))
            
            self.entry_after1.delete(0, tk.END)
            self.entry_after1.insert(0, keys.get("after1", "enter"))
            
            self.entry_after2.delete(0, tk.END)
            self.entry_after2.insert(0, keys.get("after2", "enter"))
            
            self.entry_after3.delete(0, tk.END)
            self.entry_after3.insert(0, keys.get("after3", "enter"))
            
            # Carregar boxes
            boxes = config.get("boxes", {})
            self.use_b1.set(boxes.get("box1_enabled", True))
            self.use_b2.set(boxes.get("box2_enabled", True))
            self.use_b3.set(boxes.get("box3_enabled", True))
            
            self.box1.delete("1.0", tk.END)
            self.box1.insert("1.0", boxes.get("box1_content", ""))
            
            self.box2.delete("1.0", tk.END)
            self.box2.insert("1.0", boxes.get("box2_content", ""))
            
            self.box3.delete("1.0", tk.END)
            self.box3.insert("1.0", boxes.get("box3_content", ""))
            
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")

    # ==================================================================
    # Captura de tecla
    # ==================================================================

    def capture_key(self, entry):
        """Inicia captura de teclas sem travar a interface"""
        if self.capturing:
            messagebox.showwarning("Aviso", "Já existe uma captura em andamento!")
            return

        self.capturing = True
        self.captured_keys = set()
        self.capture_target_entry = entry

        self.capture_window = tk.Toplevel(self.root)
        self.capture_window.title("Capturando...")
        self.capture_window.geometry("400x140")
        self.capture_window.resizable(False, False)
        self.capture_window.transient(self.root)
        self.capture_window.grab_set()

        frame = ttk.Frame(self.capture_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="⌨️ Pressione a combinação desejada", 
                 font=("Arial", 12, "bold")).pack(pady=5)
        ttk.Label(frame, text="Depois pressione ENTER para confirmar", 
                 font=("Arial", 10)).pack(pady=5)

        self.capture_label = ttk.Label(frame, text="Aguardando...", 
                                      font=("Courier", 11, "bold"),
                                      foreground="blue")
        self.capture_label.pack(pady=10)

        self.capture_listener = pynput_kb.Listener(
            on_press=self.on_capture_press,
            on_release=self.on_capture_release
        )
        self.capture_listener.start()
        self.capture_window.protocol("WM_DELETE_WINDOW", self.cancel_capture)

    def on_capture_press(self, key):
        """Callback quando tecla é pressionada durante captura"""
        if not self.capturing:
            return

        try:
            if hasattr(key, 'char') and key.char:
                key_str = key.char.lower()
            else:
                key_str = str(key).split('.')[-1].lower()

            key_map = {
                "ctrl_l": "ctrl", "ctrl_r": "ctrl",
                "shift_l": "shift", "shift_r": "shift",
                "alt_l": "alt", "alt_r": "alt",
                "cmd_l": "cmd", "cmd_r": "cmd"
            }
            key_str = key_map.get(key_str, key_str)

            if key_str in ("enter", "return"):
                self.finish_capture()
                return

            if key_str not in self.captured_keys:
                self.captured_keys.add(key_str)

            display = " + ".join(sorted(self.captured_keys))
            self.capture_label.config(text=display if display else "Aguardando...")

        except Exception as e:
            print(f"Erro na captura: {e}")

    def on_capture_release(self, key):
        pass

    def finish_capture(self):
        """Finaliza a captura e aplica as teclas"""
        if not self.capturing:
            return

        self.captured_keys.discard("enter")
        self.captured_keys.discard("return")

        combo_str = "+".join(sorted(self.captured_keys)) if self.captured_keys else "enter"

        if self.capture_target_entry:
            self.capture_target_entry.delete(0, tk.END)
            self.capture_target_entry.insert(0, combo_str)

        self.cancel_capture()

    def cancel_capture(self):
        """Cancela a captura"""
        self.capturing = False
        
        if self.capture_listener:
            self.capture_listener.stop()
            self.capture_listener = None

        if hasattr(self, 'capture_window') and self.capture_window:
            self.capture_window.destroy()

        self.captured_keys = set()
        self.capture_target_entry = None

    # ==================================================================
    # Listener global
    # ==================================================================

    def on_global_press(self, key):
        """Detecta teclas globais F11/F12"""
        if self.capturing:
            return

        try:
            if hasattr(key, 'char') and key.char:
                k = key.char.lower()
            else:
                k = str(key).split('.')[-1].lower()

            start_key = self.entry_start.get().strip().lower()
            stop_key = self.entry_stop.get().strip().lower()

            if k == start_key and start_key != "" and not self.running:
                self.root.after(10, self.start_macro)

            if k == stop_key and stop_key != "" and self.running:
                self.root.after(10, self.stop_macro)

        except:
            pass

    # ==================================================================
    # Macro
    # ==================================================================

    def start_macro(self):
        if self.running:
            messagebox.showwarning("Aviso", "O macro já está em execução!")
            return

        self.lines_b1 = [line for line in self.box1.get("1.0", tk.END).splitlines() if line.strip()]
        self.lines_b2 = [line for line in self.box2.get("1.0", tk.END).splitlines() if line.strip()]
        self.lines_b3 = [line for line in self.box3.get("1.0", tk.END).splitlines() if line.strip()]

        if not any([
            self.use_b1.get() and self.lines_b1,
            self.use_b2.get() and self.lines_b2,
            self.use_b3.get() and self.lines_b3
        ]):
            messagebox.showwarning("Aviso", "Nenhuma box ativa contém linhas!")
            return

        self.key_after_b1 = self.entry_after1.get().strip()
        self.key_after_b2 = self.entry_after2.get().strip()
        self.key_after_b3 = self.entry_after3.get().strip()

        self.stop_event.clear()
        self.running = True
        self.status.set("🟢 INICIANDO... (2s para focar)")

        self.root.after(2000, self._start_worker_thread)

    def _start_worker_thread(self):
        if self.running:
            self.status.set("🟢 EXECUTANDO... (F12 para parar)")
            self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
            self.worker_thread.start()

    def stop_macro(self):
        if not self.running:
            return
            
        self.stop_event.set()
        self.running = False
        self.status.set("🔴 PARADO (F11 para iniciar)")

    def worker_loop(self):
        """Loop principal com velocidade configurável"""
        i = 0
        max_lines = max(
            len(self.lines_b1) if self.use_b1.get() else 0,
            len(self.lines_b2) if self.use_b2.get() else 0,
            len(self.lines_b3) if self.use_b3.get() else 0
        )

        delay = self.speed.get()

        while i < max_lines:
            if self.stop_event.is_set():
                break

            self.root.after(0, lambda: self.status.set(f"🔄 Linha {i+1}/{max_lines}"))

            if self.use_b1.get() and i < len(self.lines_b1):
                pyperclip.copy(self.lines_b1[i])
                time.sleep(delay * 0.5)
                paste_clipboard(self.controller)
                time.sleep(delay * 0.8)
                
                if self.key_after_b1:
                    press_combination(self.controller, self.key_after_b1)
                    time.sleep(delay)

            if self.use_b2.get() and i < len(self.lines_b2):
                pyperclip.copy(self.lines_b2[i])
                time.sleep(delay * 0.5)
                paste_clipboard(self.controller)
                time.sleep(delay * 0.8)
                
                if self.key_after_b2:
                    press_combination(self.controller, self.key_after_b2)
                    time.sleep(delay)

            if self.use_b3.get() and i < len(self.lines_b3):
                pyperclip.copy(self.lines_b3[i])
                time.sleep(delay * 0.5)
                paste_clipboard(self.controller)
                time.sleep(delay * 0.8)
                
                if self.key_after_b3:
                    press_combination(self.controller, self.key_after_b3)
                    time.sleep(delay)

            i += 1
            time.sleep(delay * 1.5)

        self.running = False
        
        if not self.stop_event.is_set():
            self.root.after(0, lambda: self.status.set(f"✅ CONCLUÍDO - {max_lines} linhas"))
        else:
            self.root.after(0, lambda: self.status.set("🔴 PARADO"))

    def on_closing(self):
        """Limpeza ao fechar"""
        self.cancel_capture()
        self.stop_macro()
        if self.global_listener:
            self.global_listener.stop()
        self.root.destroy()


# ======================================================================
# Inicialização
# ======================================================================

def main():
    root = tk.Tk()
    app = AutoEsterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()