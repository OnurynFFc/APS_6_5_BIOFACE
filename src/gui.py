"""Interface gráfica do projeto APS BioFace (Python 3.13).

Tkinter controla a navegação; OpenCV continua responsável pela câmera.
Este é um protótipo acadêmico, não um sistema de autenticação de produção.
"""
import sqlite3
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .database_setup import DB_PATH, init_db
from .facial_auth import AutenticadorFacial

FUNDO = '#0b1220'
PAINEL = '#152238'
PAINEL_CLARO = '#1d304a'
TEXTO = '#edf5ff'
SUAVE = '#afc2d8'
VERDE = '#43dbac'
AZUL = '#5a9cff'
VERMELHO = '#ff8190'


class BioFaceGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('BioFace | Controle de Acesso Facial')
        self.geometry('970x680')
        self.minsize(780, 600)
        self.configure(bg=FUNDO)
        self.autenticador = AutenticadorFacial()
        self.ocupado = False
        self.usuario = None
        self.botoes_acao = []
        self._construir()
        self._atualizar_cadastros()
        self.protocol('WM_DELETE_WINDOW', self._fechar)

    def _texto(self, pai, conteudo, tamanho=11, cor=TEXTO, negrito=False, **kwargs):
        return tk.Label(pai, text=conteudo, bg=pai.cget('bg'), fg=cor,
                        font=('Segoe UI', tamanho, 'bold' if negrito else 'normal'),
                        **kwargs)

    def _botao(self, pai, titulo, comando, cor=AZUL):
        botao = tk.Button(pai, text=titulo, command=comando, bg=cor, fg=FUNDO,
                          activebackground=VERDE, activeforeground=FUNDO,
                          relief='flat', cursor='hand2', font=('Segoe UI', 11, 'bold'),
                          padx=17, pady=10)
        self.botoes_acao.append(botao)
        return botao

    def _construir(self):
        # Cabeçalho com identidade visual do projeto.
        topo = tk.Frame(self, bg=FUNDO, padx=28, pady=22)
        topo.pack(fill='x')
        self._texto(topo, '◉  BIOFACE', 23, VERDE, True).pack(anchor='w')
        self._texto(topo, 'Sistema demonstrativo de autenticação facial  •  Python 3.13',
                    11, SUAVE).pack(anchor='w', pady=(3, 0))

        principal = tk.Frame(self, bg=FUNDO, padx=28)
        principal.pack(fill='both', expand=True)
        esquerda = tk.Frame(principal, bg=PAINEL, padx=22, pady=20)
        esquerda.pack(side='left', fill='both', expand=True, padx=(0, 10))
        direita = tk.Frame(principal, bg=PAINEL, padx=22, pady=20)
        direita.pack(side='left', fill='both', expand=True, padx=(10, 0))

        self._texto(esquerda, 'Autenticação', 17, TEXTO, True).pack(anchor='w')
        self._texto(esquerda, 'Entre usando seu rosto cadastrado.', 10, SUAVE).pack(anchor='w', pady=(4, 18))
        self._botao(esquerda, '◉  Iniciar reconhecimento facial', self._login, VERDE).pack(fill='x')
        self._texto(esquerda, 'A câmera será aberta em outra janela. Pressione Q para cancelar.',
                    9, SUAVE, wraplength=360, justify='left').pack(anchor='w', pady=(9, 18))
        self._texto(esquerda, 'Sessão atual', 12, TEXTO, True).pack(anchor='w')
        self.sessao = self._texto(esquerda, 'Nenhum usuário autenticado', 11, SUAVE,
                                  wraplength=370, justify='left')
        self.sessao.pack(anchor='w', pady=(8, 9))
        self.dados = tk.Text(esquerda, height=9, bg=PAINEL_CLARO, fg=TEXTO,
                              insertbackground=TEXTO, relief='flat', font=('Segoe UI', 10),
                              wrap='word', padx=13, pady=13, state='disabled')
        self.dados.pack(fill='both', expand=True, pady=(0, 12))
        self._botao(esquerda, 'Encerrar sessão', self._logout, PAINEL_CLARO).pack(fill='x')

        self._texto(direita, 'Gerenciar rostos', 17, TEXTO, True).pack(anchor='w')
        self._texto(direita, 'Até um usuário por nível de acesso.', 10, SUAVE).pack(anchor='w', pady=(4, 15))
        self._texto(direita, 'Nome da pessoa', 10, TEXTO, True).pack(anchor='w')
        self.nome = ttk.Entry(direita, font=('Segoe UI', 11))
        self.nome.pack(fill='x', pady=(5, 12), ipady=5)
        self._texto(direita, 'Nível de acesso', 10, TEXTO, True).pack(anchor='w')
        self.nivel = tk.StringVar(value='1')
        niveis = ttk.Combobox(direita, textvariable=self.nivel, values=['1', '2', '3'],
                               state='readonly', font=('Segoe UI', 11))
        niveis.pack(fill='x', pady=(5, 15), ipady=5)
        self._botao(direita, '+  Cadastrar rosto pela webcam', self._cadastrar).pack(fill='x')
        self._texto(direita, 'Cadastros existentes', 12, TEXTO, True).pack(anchor='w', pady=(21, 7))
        self.cadastros = tk.Frame(direita, bg=PAINEL)
        self.cadastros.pack(fill='x')
        self._botao(direita, 'Remover cadastro do nível selecionado',
                    self._remover, VERMELHO).pack(fill='x', pady=(16, 0))
        self._texto(direita, 'Modo demonstração: cadastro e remoção não exigem login de administrador.',
                    9, SUAVE, wraplength=350, justify='left').pack(anchor='w', pady=(11, 0))

        rodape = tk.Frame(self, bg=FUNDO, padx=28, pady=16)
        rodape.pack(fill='x')
        self.status = self._texto(rodape, 'Pronto para uso', 10, VERDE)
        self.status.pack(side='left')
        self._texto(rodape, 'APS • Visão computacional e níveis de acesso', 9, SUAVE).pack(side='right')

    def _status(self, mensagem, cor=VERDE):
        self.status.config(text=mensagem, fg=cor)

    def _atualizar_cadastros(self):
        for widget in self.cadastros.winfo_children():
            widget.destroy()
        # A leitura reflete o banco SQLite, sem apagar os cadastros anteriores.
        with sqlite3.connect(DB_PATH) as conexao:
            linhas = conexao.execute('SELECT nome, nivel_acesso FROM usuarios').fetchall()
        por_nivel = {nivel: nome for nome, nivel in linhas}
        for nivel in (1, 2, 3):
            cadastrado = por_nivel.get(nivel)
            linha = tk.Frame(self.cadastros, bg=PAINEL_CLARO, padx=10, pady=10)
            linha.pack(fill='x', pady=3)
            self._texto(linha, f'NÍVEL {nivel}', 10, VERDE, True).pack(side='left')
            self._texto(linha, cadastrado or 'Disponível', 10,
                        TEXTO if cadastrado else SUAVE).pack(side='right')

    def _executar_camera(self, tarefa, ao_final):
        """A webcam roda em outra thread para não travar a janela do Tkinter.

        Atualizações de widgets são realizadas exclusivamente na thread principal.
        """
        if self.ocupado:
            return
        self.ocupado = True
        for botao in self.botoes_acao:
            botao.configure(state='disabled')
        self._status('Câmera em uso… pressione Q na janela da câmera para cancelar.', AZUL)

        def processo():
            try:
                resultado = tarefa()
                erro = None
            except Exception as exc:
                resultado, erro = None, str(exc)
            self.after(0, lambda: self._finalizar_camera(resultado, erro, ao_final))

        threading.Thread(target=processo, daemon=True).start()

    def _finalizar_camera(self, resultado, erro, ao_final):
        self.ocupado = False
        for botao in self.botoes_acao:
            botao.configure(state='normal')
        if erro:
            self._status('Falha na operação', VERMELHO)
            messagebox.showerror('BioFace', erro)
        else:
            ao_final(resultado)

    def _cadastrar(self):
        nome = self.nome.get().strip()
        nivel = int(self.nivel.get())
        if not nome:
            messagebox.showwarning('Cadastro', 'Informe o nome da pessoa.')
            return
        if any(u['nivel_acesso'] == nivel for u in self.autenticador.known_users):
            messagebox.showwarning('Cadastro', 'Este nível já possui um usuário cadastrado.')
            return
        self._executar_camera(lambda: self.autenticador.cadastrar_rosto(nivel, nome),
                             self._cadastro_concluido)

    def _cadastro_concluido(self, sucesso):
        self._atualizar_cadastros()
        if sucesso:
            self.nome.delete(0, tk.END)
            self._status('Rosto cadastrado com sucesso!')
            messagebox.showinfo('Cadastro concluído', 'As amostras faciais foram salvas no banco local.')
        else:
            self._status('Cadastro cancelado ou webcam indisponível.', VERMELHO)

    def _remover(self):
        nivel = int(self.nivel.get())
        if not messagebox.askyesno('Confirmar exclusão',
                                   f'Remover o usuário e as fotos do nível {nivel}?'):
            return
        # ATENÇÃO: exclusão aberta apenas no protótipo acadêmico.
        removido = self.autenticador.remover_cadastro(nivel)
        self._atualizar_cadastros()
        self._logout()
        self._status('Cadastro removido.' if removido else 'Nenhum cadastro nesse nível.',
                     VERDE if removido else VERMELHO)

    def _login(self):
        if not self.autenticador.known_users:
            messagebox.showwarning('Reconhecimento facial', 'Cadastre um rosto antes de entrar.')
            return
        self._executar_camera(self.autenticador.reconhecer_rosto_webcam,
                             self._login_concluido)

    def _login_concluido(self, usuario):
        if not usuario:
            self._status('Autenticação cancelada ou não reconhecida.', VERMELHO)
            messagebox.showwarning('Acesso negado', 'Rosto não reconhecido ou operação cancelada.')
            return
        self.usuario = usuario
        nivel = usuario['nivel_acesso']
        self.sessao.config(text=f"{usuario['nome']}  •  Nível {nivel}", fg=VERDE)
        with sqlite3.connect(DB_PATH) as conexao:
            # Exibe somente os dados que o nível de acesso permite visualizar.
            registros = conexao.execute(
                'SELECT informacao FROM dados_sistema WHERE nivel_requerido <= ? ORDER BY nivel_requerido',
                (nivel,)).fetchall()
        self._mostrar_dados('\n\n'.join('• ' + dado[0] for dado in registros)
                           or 'Nenhuma informação disponível para este nível.')
        self._status(f"Autenticação aprovada — acesso nível {nivel}.")

    def _mostrar_dados(self, conteudo):
        self.dados.configure(state='normal')
        self.dados.delete('1.0', tk.END)
        self.dados.insert('1.0', conteudo)
        self.dados.configure(state='disabled')

    def _logout(self):
        self.usuario = None
        self.sessao.config(text='Nenhum usuário autenticado', fg=SUAVE)
        self._mostrar_dados('')
        self._status('Sessão encerrada.')

    def _fechar(self):
        if self.ocupado:
            messagebox.showwarning('Câmera ativa',
                                   'Cancele primeiro a operação na janela da webcam (tecla Q).')
            return
        self.destroy()


def iniciar_gui():
    init_db()
    BioFaceGUI().mainloop()


if __name__ == '__main__':
    iniciar_gui()
