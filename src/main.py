"""Menu principal do projeto de biometria facial APS."""
import sqlite3

try:
    from .database_setup import init_db, DB_PATH
    from .facial_auth import AutenticadorFacial
except ImportError:
    from database_setup import init_db, DB_PATH
    from facial_auth import AutenticadorFacial


def consultar_sistema(nivel_usuario):
    """Retorna apenas os registros permitidos para o nível do usuário."""
    if nivel_usuario not in (1, 2, 3):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Busca informações cujo nível_requerido seja menor ou igual ao nível do usuário
        cursor.execute('SELECT informacao FROM dados_sistema WHERE nivel_requerido <= ?',
                       (nivel_usuario,))
        return cursor.fetchall()


def main():
    # Inicializa/atualiza o banco de dados SQLite sem apagar dados salvos.
    init_db()
    autenticador = AutenticadorFacial()
    while True:
        print('\n==== BIOFACE - PYTHON 3.13 ====')
        print('1. Entrar com reconhecimento facial')
        print('2. Cadastrar rosto em um nível (1, 2 ou 3)')
        print('3. Remover cadastro de um nível (modo demonstração)')
        print('0. Sair')
        escolha = input('Escolha: ').strip()
        if escolha == '0':
            break
        if escolha == '2':
            try:
                nivel = int(input('Nível de acesso (1, 2 ou 3): '))
                nome = input('Nome do usuário: ')
                autenticador.cadastrar_rosto(nivel, nome)
            except ValueError as exc:
                print(f'[LOG] Entrada inválida: {exc}')
            continue
        if escolha == '3':
            # ATENÇÃO: administração aberta somente para demonstração em sala de aula.
            # Em produção, proteger cadastro/exclusão com administrador autenticado.
            try:
                nivel = int(input('Nível a remover (1, 2 ou 3): '))
                print('Removido.' if autenticador.remover_cadastro(nivel)
                      else 'Nenhum cadastro encontrado.')
            except ValueError:
                print('[LOG] Digite um nível numérico.')
            continue
        if escolha != '1':
            print('[LOG] Opção desconhecida.')
            continue

        usuario = autenticador.reconhecer_rosto_webcam()
        if not usuario:
            print('\n❌ Autenticação falhou ou foi cancelada. Acesso negado.')
            continue
        print('\n==========================================')
        print(f" BEM-VINDO(A), {usuario['nome'].upper()}!")
        print(f" Nível de Acesso Confirmado: Nível {usuario['nivel_acesso']}")
        print('==========================================')

        # Exibição controlada de dados
        dados = consultar_sistema(usuario['nivel_acesso'])
        print('\n[ INFORMAÇÕES LIBERADAS PARA SEU PERFIL ]\n')
        for item in dados:
            print(f' • {item[0]}')
        print('\n------------------------------------------')


if __name__ == '__main__':
    # Interface gráfica padrão. Para acessar o menu antigo: python -m src.main --cli
    import sys
    if '--cli' in sys.argv:
        main()
    else:
        try:
            from .gui import iniciar_gui
        except ImportError:
            from gui import iniciar_gui
        iniciar_gui()
