"""Inicialização não destrutiva do banco de dados do BioFace."""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'database' / 'sistema.db'
DATASET_DIR = BASE_DIR / 'dataset'


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    conect = sqlite3.connect(DB_PATH)  # Conexão com o banco de dados sqlite
    cursor = conect.cursor()  # Executar/usar comandos/queries SQL

    # Tabela de Usuários e Níveis
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        nivel_acesso INTEGER NOT NULL UNIQUE CHECK(nivel_acesso BETWEEN 1 AND 3),
        foto_path TEXT NOT NULL
    )''')

    # Tabela de Dados Restritos
    cursor.execute('''CREATE TABLE IF NOT EXISTS dados_sistema (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nivel_requerido INTEGER NOT NULL,
        informacao TEXT NOT NULL
    )''')

    # IMPORTANTE: Não limpa registros antigos! Isso apagaria os rostos cadastrados
    # em toda execução e possibilitaria perder os dados do aplicativo.
    # Dados de exemplo são criados somente na primeira inicialização.
    if cursor.execute('SELECT COUNT(*) FROM dados_sistema').fetchone()[0] == 0:
        print('[LOG]: Adicionando restrições iniciais...')
        cursor.executemany('INSERT INTO dados_sistema (nivel_requerido, informacao) VALUES (?, ?)', [
            (1, '[Nível 1] Horário de funcionamento do sistema: 08:00 às 18:00.'),
            (2, '[Nível 2] Relatório Mensal de Vendas e Desempenho.'),
            (3, '[Nível 3] CHAVES SECRETAS E DADOS FINANCEIROS CRÍTICOS (SIMULAÇÃO).'),
        ])

    conect.commit()  # Commit antes das mudanças serem salvas no banco
    conect.close()  # Fechando a conexão com o banco
    print('[LOG]: Banco de dados inicializado com sucesso!')


if __name__ == '__main__':
    # Iniciando o banco de dados
    init_db()
