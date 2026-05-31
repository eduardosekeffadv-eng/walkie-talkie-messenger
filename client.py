import json
import threading
import tkinter as tk
from tkinter import messagebox
from urllib.parse import quote
import base64
import hashlib

import customtkinter as ctk
import websocket

from cryptography.fernet import Fernet, InvalidToken


# SERVIDOR ONLINE NO RENDER
SERVER_URL = "wss://walkie-talkie-go.onrender.com/ws"

# PARA TESTAR LOCALMENTE, SE QUISER USAR O SERVIDOR GO NO SEU PC:
# SERVER_URL = "ws://127.0.0.1:8080/ws"


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class WalkieTalkieApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Walkie Talkie Messenger")
        self.geometry("980x690")
        self.minsize(900, 620)

        self.ws = None
        self.conectado = False
        self.nome_atual = ""
        self.frequencia_atual = ""
        self.fernet = None

        self._montar_interface()

    # ============================================================
    # INTERFACE
    # ============================================================

    def _montar_interface(self):
        self.configure(fg_color="#080b14")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        topo = ctk.CTkFrame(self, fg_color="#101624", corner_radius=0)
        topo.grid(row=0, column=0, sticky="ew")
        topo.grid_columnconfigure(0, weight=1)

        titulo = ctk.CTkLabel(
            topo,
            text="WALKIE TALKIE",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#e8f1ff"
        )
        titulo.grid(row=0, column=0, padx=24, pady=(18, 2), sticky="w")

        subtitulo = ctk.CTkLabel(
            topo,
            text="Mensagens instantâneas por frequência com criptografia de ponta a ponta",
            font=ctk.CTkFont(size=14),
            text_color="#8fa3c7"
        )
        subtitulo.grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        self.status_label = ctk.CTkLabel(
            topo,
            text="Desconectado",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ff5d5d"
        )
        self.status_label.grid(row=0, column=1, padx=24, pady=(20, 2), sticky="e")

        corpo = ctk.CTkFrame(self, fg_color="#080b14", corner_radius=0)
        corpo.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)

        corpo.grid_columnconfigure(0, weight=0)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)

        painel_lateral = ctk.CTkFrame(
            corpo,
            fg_color="#101624",
            corner_radius=22,
            border_width=1,
            border_color="#1d2a44"
        )
        painel_lateral.grid(row=0, column=0, sticky="ns", padx=(0, 16), pady=0)
        painel_lateral.grid_columnconfigure(0, weight=1)

        label_config = ctk.CTkLabel(
            painel_lateral,
            text="Configuração",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#e8f1ff"
        )
        label_config.grid(row=0, column=0, padx=20, pady=(24, 12), sticky="w")

        label_nome = ctk.CTkLabel(
            painel_lateral,
            text="Seu nome",
            font=ctk.CTkFont(size=13),
            text_color="#8fa3c7"
        )
        label_nome.grid(row=1, column=0, padx=20, pady=(8, 4), sticky="w")

        self.campo_nome = ctk.CTkEntry(
            painel_lateral,
            width=280,
            height=42,
            placeholder_text="Ex: Eduardo",
            fg_color="#0b1020",
            border_color="#233458",
            text_color="#ffffff"
        )
        self.campo_nome.grid(row=2, column=0, padx=20, pady=(0, 14), sticky="ew")

        label_freq = ctk.CTkLabel(
            painel_lateral,
            text="Frequência",
            font=ctk.CTkFont(size=13),
            text_color="#8fa3c7"
        )
        label_freq.grid(row=3, column=0, padx=20, pady=(8, 4), sticky="w")

        self.campo_frequencia = ctk.CTkEntry(
            painel_lateral,
            width=280,
            height=42,
            placeholder_text="Ex: sala123, familia, grupo7",
            fg_color="#0b1020",
            border_color="#233458",
            text_color="#ffffff"
        )
        self.campo_frequencia.grid(row=4, column=0, padx=20, pady=(0, 14), sticky="ew")

        label_senha = ctk.CTkLabel(
            painel_lateral,
            text="Senha secreta da frequência",
            font=ctk.CTkFont(size=13),
            text_color="#8fa3c7"
        )
        label_senha.grid(row=5, column=0, padx=20, pady=(8, 4), sticky="w")

        self.campo_senha = ctk.CTkEntry(
            painel_lateral,
            width=280,
            height=42,
            placeholder_text="Senha combinada entre vocês",
            show="*",
            fg_color="#0b1020",
            border_color="#233458",
            text_color="#ffffff"
        )
        self.campo_senha.grid(row=6, column=0, padx=20, pady=(0, 18), sticky="ew")

        self.botao_entrar = ctk.CTkButton(
            painel_lateral,
            text="Entrar na frequência",
            height=44,
            corner_radius=14,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.entrar_frequencia
        )
        self.botao_entrar.grid(row=7, column=0, padx=20, pady=(4, 12), sticky="ew")

        self.botao_desconectar = ctk.CTkButton(
            painel_lateral,
            text="Desconectar",
            height=40,
            corner_radius=14,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.desconectar
        )
        self.botao_desconectar.grid(row=8, column=0, padx=20, pady=(0, 12), sticky="ew")

        self.botao_limpar = ctk.CTkButton(
            painel_lateral,
            text="Limpar tela",
            height=40,
            corner_radius=14,
            fg_color="#1d2a44",
            hover_color="#26395f",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.limpar_chat
        )
        self.botao_limpar.grid(row=9, column=0, padx=20, pady=(0, 18), sticky="ew")

        info = ctk.CTkLabel(
            painel_lateral,
            text=(
                "Criptografia ativa:\n"
                "a mensagem sai criptografada do seu PC.\n\n"
                "O servidor apenas repassa o conteúdo.\n"
                "Sem a senha secreta correta,\n"
                "a mensagem não pode ser lida."
            ),
            font=ctk.CTkFont(size=12),
            text_color="#687899",
            justify="left"
        )
        info.grid(row=10, column=0, padx=20, pady=(12, 22), sticky="w")

        painel_chat = ctk.CTkFrame(
            corpo,
            fg_color="#101624",
            corner_radius=22,
            border_width=1,
            border_color="#1d2a44"
        )
        painel_chat.grid(row=0, column=1, sticky="nsew")
        painel_chat.grid_columnconfigure(0, weight=1)
        painel_chat.grid_rowconfigure(0, weight=1)

        self.caixa_chat = ctk.CTkTextbox(
            painel_chat,
            fg_color="#0b1020",
            text_color="#e8f1ff",
            corner_radius=18,
            border_width=1,
            border_color="#1d2a44",
            font=ctk.CTkFont(size=14),
            wrap="word"
        )
        self.caixa_chat.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 10))
        self.caixa_chat.configure(state="disabled")

        area_envio = ctk.CTkFrame(painel_chat, fg_color="transparent")
        area_envio.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        area_envio.grid_columnconfigure(0, weight=1)

        self.campo_mensagem = ctk.CTkEntry(
            area_envio,
            height=46,
            placeholder_text="Digite sua mensagem...",
            fg_color="#0b1020",
            border_color="#233458",
            text_color="#ffffff"
        )
        self.campo_mensagem.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.campo_mensagem.bind("<Return>", lambda event: self.enviar_mensagem())
        self.campo_mensagem.configure(state="disabled")

        self.botao_enviar = ctk.CTkButton(
            area_envio,
            text="Enviar",
            width=130,
            height=46,
            corner_radius=14,
            fg_color="#22c55e",
            hover_color="#16a34a",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.enviar_mensagem
        )
        self.botao_enviar.grid(row=0, column=1)
        self.botao_enviar.configure(state="disabled")

        self._adicionar_sistema("Escolha um nome, uma frequência e uma senha secreta para começar.")
        self.protocol("WM_DELETE_WINDOW", self.fechar)

    # ============================================================
    # CRIPTOGRAFIA
    # ============================================================

    def gerar_chave_criptografia(self, senha, frequencia):
        senha = senha.strip()
        frequencia = frequencia.strip()

        if not senha:
            raise ValueError("A senha secreta é obrigatória.")

        if not frequencia:
            raise ValueError("A frequência é obrigatória.")

        # Todos que usarem a mesma frequência e a mesma senha
        # vão gerar a mesma chave localmente.
        salt = hashlib.sha256(frequencia.encode("utf-8")).digest()
        material = senha.encode("utf-8") + salt

        chave_hash = hashlib.sha256(material).digest()
        chave_fernet = base64.urlsafe_b64encode(chave_hash)

        return Fernet(chave_fernet)

    def criptografar_mensagem(self, nome, mensagem):
        pacote = {
            "name": nome,
            "message": mensagem
        }

        texto = json.dumps(pacote, ensure_ascii=False)
        token = self.fernet.encrypt(texto.encode("utf-8"))

        return token.decode("utf-8")

    def descriptografar_mensagem(self, token):
        dados = self.fernet.decrypt(token.encode("utf-8"))
        pacote = json.loads(dados.decode("utf-8"))

        nome = pacote.get("name", "Usuário")
        mensagem = pacote.get("message", "")

        return nome, mensagem

    # ============================================================
    # CONEXÃO
    # ============================================================

    def entrar_frequencia(self):
        nome = self.campo_nome.get().strip()
        frequencia = self.campo_frequencia.get().strip()
        senha = self.campo_senha.get().strip()

        if not nome:
            messagebox.showwarning("Atenção", "Digite seu nome.")
            return

        if not frequencia:
            messagebox.showwarning("Atenção", "Digite uma frequência.")
            return

        if not senha:
            messagebox.showwarning("Atenção", "Digite a senha secreta da frequência.")
            return

        try:
            self.fernet = self.gerar_chave_criptografia(senha, frequencia)
        except Exception as erro:
            messagebox.showerror(
                "Erro",
                f"Não foi possível gerar a chave de criptografia.\n\n{erro}"
            )
            return

        self.desconectar(silencioso=True)

        self.nome_atual = nome
        self.frequencia_atual = frequencia

        nome_url = quote(nome)
        freq_url = quote(frequencia)

        url = f"{SERVER_URL}?freq={freq_url}&name={nome_url}"

        self._set_status("Conectando...", "orange")

        self.ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        thread.start()

    def _on_open(self, ws):
        self.conectado = True

        self.after(
            0,
            lambda: self._set_status(
                f"Na frequência: {self.frequencia_atual} | Criptografia ativa",
                "green"
            )
        )

        self.after(0, lambda: self.botao_entrar.configure(text="Trocar frequência"))
        self.after(0, lambda: self.campo_mensagem.configure(state="normal"))
        self.after(0, lambda: self.botao_enviar.configure(state="normal"))
        self.after(0, lambda: self._adicionar_sistema("Conexão segura iniciada."))

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)

            tipo = data.get("type", "message")
            nome = data.get("name", "Usuário")
            texto = data.get("message", "")

            if tipo == "system":
                self.after(0, lambda: self._adicionar_sistema(texto))
                return

            if tipo == "encrypted":
                try:
                    nome_real, mensagem_real = self.descriptografar_mensagem(texto)
                    self.after(0, lambda: self._adicionar_mensagem(nome_real, mensagem_real))
                except InvalidToken:
                    self.after(
                        0,
                        lambda: self._adicionar_sistema(
                            "Mensagem recebida, mas não foi possível descriptografar. "
                            "A senha secreta provavelmente está diferente."
                        )
                    )
                except Exception:
                    self.after(
                        0,
                        lambda: self._adicionar_sistema(
                            "Mensagem criptografada recebida, mas houve erro ao tentar abrir."
                        )
                    )
                return

            # Compatibilidade com mensagens antigas não criptografadas,
            # caso algum cliente antigo ainda esteja conectado.
            self.after(0, lambda: self._adicionar_mensagem(nome, texto))

        except Exception:
            self.after(0, lambda: self._adicionar_sistema("Mensagem recebida em formato inválido."))

    def _on_error(self, ws, error):
        self.conectado = False

        self.after(0, lambda: self._set_status("Falha ao conectar", "red"))

        self.after(
            0,
            lambda: messagebox.showerror(
                "Erro de conexão",
                f"Não foi possível conectar.\n\nErro:\n{error}"
            )
        )

    def _on_close(self, ws, close_status_code, close_msg):
        self.conectado = False

        self.after(0, lambda: self._set_status("Desconectado", "red"))
        self.after(0, lambda: self.campo_mensagem.configure(state="disabled"))
        self.after(0, lambda: self.botao_enviar.configure(state="disabled"))

    def desconectar(self, silencioso=False):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

        self.ws = None
        self.conectado = False

        self._set_status("Desconectado", "red")
        self.campo_mensagem.configure(state="disabled")
        self.botao_enviar.configure(state="disabled")

        if not silencioso:
            self._adicionar_sistema("Você foi desconectado.")

    # ============================================================
    # MENSAGENS
    # ============================================================

    def enviar_mensagem(self):
        mensagem = self.campo_mensagem.get().strip()

        if not mensagem:
            return

        if not self.conectado or not self.ws:
            messagebox.showwarning("Atenção", "Entre em uma frequência antes de enviar mensagens.")
            return

        if not self.fernet:
            messagebox.showwarning("Atenção", "A chave de criptografia não foi criada.")
            return

        try:
            mensagem_criptografada = self.criptografar_mensagem(
                self.nome_atual,
                mensagem
            )

            data = {
                "name": "criptografado",
                "message": mensagem_criptografada,
                "type": "encrypted"
            }

            self.ws.send(json.dumps(data))
            self.campo_mensagem.delete(0, "end")

        except Exception as erro:
            messagebox.showerror(
                "Erro",
                f"Não foi possível criptografar/enviar a mensagem.\n\n{erro}"
            )

    def _adicionar_mensagem(self, nome, mensagem):
        self.caixa_chat.configure(state="normal")
        self.caixa_chat.insert("end", f"{nome}: {mensagem}\n\n")
        self.caixa_chat.see("end")
        self.caixa_chat.configure(state="disabled")

    def _adicionar_sistema(self, mensagem):
        self.caixa_chat.configure(state="normal")
        self.caixa_chat.insert("end", f"Sistema: {mensagem}\n\n")
        self.caixa_chat.see("end")
        self.caixa_chat.configure(state="disabled")

    def limpar_chat(self):
        self.caixa_chat.configure(state="normal")
        self.caixa_chat.delete("1.0", "end")
        self.caixa_chat.configure(state="disabled")
        self._adicionar_sistema("Tela limpa.")

    # ============================================================
    # UTILITÁRIOS
    # ============================================================

    def _set_status(self, texto, cor):
        cores = {
            "green": "#22c55e",
            "red": "#ff5d5d",
            "orange": "#f59e0b"
        }

        self.status_label.configure(
            text=texto,
            text_color=cores.get(cor, "#e8f1ff")
        )

    def fechar(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

        self.destroy()


if __name__ == "__main__":
    app = WalkieTalkieApp()
    app.mainloop()