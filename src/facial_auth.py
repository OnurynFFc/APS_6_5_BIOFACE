"""Reconhecimento facial demonstrativo compatível com Python 3.13.

Substitui face_recognition/dlib por OpenCV + NumPy, usando detecção Haar,
LBP (Local Binary Patterns) e comparação dos histogramas em grade.
Aviso: não incorpora detecção de vivacidade; NÃO use como autenticação real.
"""
import sqlite3
from pathlib import Path

import cv2
import numpy as np

try:
    from .database_setup import DB_PATH, DATASET_DIR, init_db
except ImportError:  # Permite executar `python src/main.py`.
    from database_setup import DB_PATH, DATASET_DIR, init_db

# Limiar de distância heurístico: necessita calibração com imagens reais.
# Menor distância = maior semelhança. Não constitui garantia de segurança.
LIMIAR_DISTANCIA = 0.40
QUADROS_CONSECUTIVOS = 5
CAPTURAS_CADASTRO = 12
FACE_SIZE = (120, 120)


def _extrair_lbp(face):
    """Calcula padrões binários locais e histogramas LBP normalizados em grade."""
    face = cv2.resize(face, FACE_SIZE, interpolation=cv2.INTER_AREA)
    face = cv2.equalizeHist(face)
    centro = face[1:-1, 1:-1]
    vizinhos = [face[:-2, :-2], face[:-2, 1:-1], face[:-2, 2:],
                face[1:-1, 2:], face[2:, 2:], face[2:, 1:-1],
                face[2:, :-2], face[1:-1, :-2]]
    lbp = np.zeros_like(centro, dtype=np.uint8)
    for bit, vizinho in enumerate(vizinhos):
        lbp |= ((vizinho >= centro).astype(np.uint8) << bit)

    # Histograma em 6x6 células mantém alguma informação espacial do rosto.
    partes = []
    for linha in np.array_split(lbp, 6, axis=0):
        for celula in np.array_split(linha, 6, axis=1):
            hist = np.bincount(celula.ravel(), minlength=256).astype(np.float32)
            hist /= max(hist.sum(), 1)
            partes.append(hist)
    return np.concatenate(partes)


def _distancia(a, b):
    """Distância qui-quadrado média entre histogramas de cada célula."""
    return float(0.5 * np.sum((a - b) ** 2 / (a + b + 1e-8)) / 36)


class AutenticadorFacial:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        # Carrega o detector Haar Cascade de forma portátil.
        # 1. Prioriza o XML incluído no projeto para não depender da instalação do OpenCV.
        # 2. Se ele faltar, tenta o diretório de dados instalado com o OpenCV.
        #    Usar pathlib evita erros de concatenação de caminhos no Windows.
        nome_xml = 'haarcascade_frontalface_default.xml'
        pasta_local = Path(__file__).resolve().parent / 'models'
        candidatos = [pasta_local / nome_xml]
        diretorio_opencv = getattr(getattr(cv2, 'data', None), 'haarcascades', None)
        if diretorio_opencv:
            candidatos.append(Path(diretorio_opencv) / nome_xml)

        self.detector = None
        for caminho_xml in candidatos:
            if not caminho_xml.is_file():
                continue
            detector = cv2.CascadeClassifier(str(caminho_xml))
            if not detector.empty():
                self.detector = detector
                print(f'[LOG] Detector de rostos carregado: {caminho_xml}')
                break

        if self.detector is None:
            locais = '\n  - '.join(str(p) for p in candidatos)
            raise RuntimeError(
                'Não foi possível carregar o detector de faces OpenCV.\n'
                f'Locais verificados:\n  - {locais}\n'
                'Confira se src/models/haarcascade_frontalface_default.xml existe '
                'e, se necessário, reinstale opencv-python.'
            )
        self.known_encodings = []  # Agora: descritores LBP em vez de embeddings dlib.
        self.known_users = []
        self._carregar_usuarios_cadastrados()

    def _detectar(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        boxes = self.detector.detectMultiScale(gray, scaleFactor=1.1,
                                               minNeighbors=5, minSize=(65, 65))
        return gray, sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)

    def _carregar_usuarios_cadastrados(self):
        """Carrega fotos do banco de dados e computa as características LBP."""
        self.known_encodings.clear()
        self.known_users.clear()
        with sqlite3.connect(self.db_path) as conect:  # Conexão com o banco de dados
            cursor = conect.cursor()
            cursor.execute('SELECT id, nome, nivel_acesso, foto_path FROM usuarios')
            rows = cursor.fetchall()  # Recuperar todas as linhas

        for user_id, nome, nivel, path in rows:
            try:
                # 1. Carregamento de amostras faciais do disco.
                arquivo = Path(path)
                if not arquivo.is_absolute():
                    arquivo = self.db_path.parent.parent / arquivo
                imagens = sorted(arquivo.glob('*.png')) if arquivo.is_dir() else [arquivo]
                amostras = []
                for imagem in imagens:
                    face = cv2.imread(str(imagem), cv2.IMREAD_GRAYSCALE)
                    if face is not None:
                        # 2. Extração de características com textura LBP.
                        amostras.append(_extrair_lbp(face))
                if amostras:
                    self.known_encodings.append(amostras)
                    self.known_users.append({'id': user_id, 'nome': nome,
                                             'nivel_acesso': nivel})
                else:
                    print(f'[LOG] AVISO: Nenhuma amostra facial encontrada em {arquivo}')
            except Exception as exc:
                print(f'[LOG] Erro ao carregar {path}: {exc}')

    def cadastrar_rosto(self, nivel, nome):
        """Registra uma pessoa por nível usando amostras coletadas na webcam."""
        if nivel not in (1, 2, 3):
            raise ValueError('Nível inválido: utilize 1, 2 ou 3.')
        if not nome.strip():
            raise ValueError('O nome não pode ficar em branco.')
        with sqlite3.connect(self.db_path) as conn:
            ja_existe = conn.execute('SELECT id FROM usuarios WHERE nivel_acesso = ?',
                                    (nivel,)).fetchone()
        if ja_existe:
            print(f'[LOG] Nível {nivel} já possui um rosto. Remova o cadastro primeiro.')
            return False

        pasta = DATASET_DIR / f'nivel{nivel}_usuario'
        webcam = cv2.VideoCapture(0)
        if not webcam.isOpened():
            print('[LOG] Erro ao acessar a webcam.')
            return False
        amostras = []
        try:
            print('Olhe para a webcam e mova levemente o rosto. Q cancela.')
            while len(amostras) < CAPTURAS_CADASTRO:
                ret, frame = webcam.read()
                if not ret:
                    break
                gray, boxes = self._detectar(frame)
                # Exatamente um rosto: evita registrar outra pessoa na mesma foto.
                if len(boxes) == 1:
                    x, y, w, h = boxes[0]
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    amostras.append(cv2.resize(gray[y:y+h, x:x+w], FACE_SIZE))
                cv2.putText(frame, f'Amostras: {len(amostras)}/{CAPTURAS_CADASTRO}',
                            (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 0), 2)
                cv2.imshow('Cadastro facial - Q cancela', frame)
                if cv2.waitKey(140) & 0xFF == ord('q'):
                    break
        finally:
            webcam.release()
            cv2.destroyAllWindows()
        if len(amostras) != CAPTURAS_CADASTRO:
            print('[LOG] Cadastro cancelado ou amostras insuficientes.')
            return False

        pasta.mkdir(parents=True, exist_ok=True)
        for indice, face in enumerate(amostras):
            cv2.imwrite(str(pasta / f'amostra_{indice:02d}.png'), face)
        # Salva caminho relativo; o cadastro persiste entre execuções.
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('INSERT INTO usuarios (nome, nivel_acesso, foto_path) VALUES (?, ?, ?)',
                         (nome.strip(), nivel, f'dataset/{pasta.name}'))
        self._carregar_usuarios_cadastrados()
        print(f'[LOG] Rosto cadastrado no nível {nivel}.')
        return True

    def remover_cadastro(self, nivel):
        """Remove o cadastro de um nível, incluindo as amostras faciais armazenadas."""
        import shutil
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT foto_path FROM usuarios WHERE nivel_acesso = ?',
                               (nivel,)).fetchone()
            if not row:
                return False
            conn.execute('DELETE FROM usuarios WHERE nivel_acesso = ?', (nivel,))
        pasta = (self.db_path.parent.parent / row[0]).resolve()
        if pasta.is_dir() and pasta.parent == DATASET_DIR.resolve():
            shutil.rmtree(pasta)
        self._carregar_usuarios_cadastrados()
        return True

    def reconhecer_rosto_webcam(self):
        """Abre a webcam e tenta reconhecer um único rosto cadastrado."""
        if not self.known_users:
            print('[LOG] Cadastre um rosto antes de iniciar o login.')
            return None
        video_capture = cv2.VideoCapture(0)
        if not video_capture.isOpened():  # Verifica se tem uma câmera
            print('[LOG] Erro ao acessar a webcam.')
            return None
        print('\n--- TELA DE LOGIN BIOMÉTRICO ---')
        print("Posicione seu rosto em frente à câmera. Pressione 'q' para cancelar.")
        usuario_autenticado = None
        ultimo_id, consecutivos = None, 0
        try:
            while True:
                ret, frame = video_capture.read()
                if not ret:
                    break
                gray, boxes = self._detectar(frame)
                nome_display = 'Desconhecido'
                cor_box = (0, 0, 255)  # Vermelho para desconhecido
                # Mais de um rosto na câmera impede autenticação.
                if len(boxes) == 1:
                    x, y, w, h = boxes[0]
                    # 1. Extração do descritor da região facial detectada.
                    descritor = _extrair_lbp(gray[y:y+h, x:x+w])
                    # 2. Comparação vetorial usando distância qui-quadrado.
                    distancias = [min(_distancia(descritor, exemplar) for exemplar in amostras)
                                  for amostras in self.known_encodings]
                    melhor = int(np.argmin(distancias))
                    if distancias[melhor] <= LIMIAR_DISTANCIA:
                        candidato = self.known_users[melhor]
                        if candidato['id'] == ultimo_id:
                            consecutivos += 1
                        else:
                            ultimo_id, consecutivos = candidato['id'], 1
                        nome_display = f"{candidato['nome']} (Nivel {candidato['nivel_acesso']})"
                        cor_box = (0, 255, 0)  # Verde para rosto reconhecido
                        if consecutivos >= QUADROS_CONSECUTIVOS:
                            usuario_autenticado = candidato
                    else:
                        ultimo_id, consecutivos = None, 0
                    # Desenha o retângulo ao redor do rosto detectado.
                    cv2.rectangle(frame, (x, y), (x+w, y+h), cor_box, 2)
                    cv2.putText(frame, nome_display, (x, max(y-10, 20)),
                                cv2.FONT_HERSHEY_DUPLEX, .55, cor_box, 1)
                else:
                    ultimo_id, consecutivos = None, 0
                    if len(boxes) > 1:
                        cv2.putText(frame, 'Somente um rosto por vez!', (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), 2)
                cv2.imshow("Autenticacao Facial - Pressione 'q' para sair", frame)
                if usuario_autenticado:
                    cv2.waitKey(500)  # Pausa breve para confirmação visual
                    break
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            video_capture.release()
            cv2.destroyAllWindows()
        return usuario_autenticado
