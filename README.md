<<<<<<< HEAD
# APS_6_5_BIOFACE
=======
# APS BioFace — Python 3.13

## O que mudou

O código original utilizava `face_recognition` (e `dlib`), difíceis de instalar em algumas versões do Python. Agora utiliza **somente OpenCV e NumPy**, com detecção facial Haar e descritores de textura **LBP (Local Binary Patterns)** com distância qui-quadrado. Os comentários relevantes e a estrutura `src/`, `dataset/` e `database/` foram preservados. O programa agora cadastra as faces pela própria webcam, pois as fotos referenciadas no arquivo original não estavam incluídas.

> **Atenção**: implementação **acadêmica demonstrativa**, não é biometria segura. Não possui verificação de vivacidade (pode ser enganada por foto/vídeo), o limiar é heurístico, o cadastro e a exclusão não exigem administrador, e os dados locais não são criptografados. Não utilize para dados sensíveis ou controle de acesso real.

## Instalar (Windows / Linux / macOS, Python 3.13)

Abra o terminal **na pasta APS_6_5_BIOFACE** e execute:

```powershell
python -m venv .venv
```

No Windows (PowerShell):

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m src.main
```

No Linux / macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.main
```

Se `python` apontar para outra versão, use o lançador `py -3.13` no Windows para criar o ambiente. É necessário ter webcam, interface gráfica e conceder permissão para acesso à câmera.

## Interface gráfica (nova)

Execute `.venv\Scripts\python.exe -m src.main` para abrir uma janela com botões. Não é mais necessário escolher opções pelo terminal.

Na coluna **Gerenciar rostos**, informe um nome, escolha um nível e clique em **Cadastrar rosto pela webcam**. Na coluna **Autenticação**, clique em **Iniciar reconhecimento facial**. As janelas da câmera ainda são exibidas pelo OpenCV; pressione `Q` na janela da câmera para cancelar. Após login, os dados autorizados aparecem dentro do aplicativo. Use **Encerrar sessão** para ocultá-los.

Para continuar utilizando o menu antigo, execute `.venv\Scripts\python.exe -m src.main --cli`.

O Tkinter faz parte da distribuição padrão do Python para Windows e não precisa ser instalado pelo pip.

## Passo a passo

1. Clique em **Cadastrar rosto pela webcam**, selecione o **nível 1**, digite o nome e olhe para a webcam até capturar 12 amostras. Repita para os níveis **2** e **3** (máximo de um usuário por nível).
2. Clique em **Iniciar reconhecimento facial** para fazer login com o rosto. Mantenha só uma pessoa diante da câmera, com boa iluminação. Pressione `q` para cancelar.
3. O nível 1 vê informações básicas; o nível 2 também vê as de nível 2; o nível 3 vê todas.
4. Clique em **Remover cadastro do nível selecionado** para remover o rosto de um nível, se precisar refazer o cadastro. **Esta opção é aberta apenas por ser uma demonstração**.

O banco SQLite é criado automaticamente em `database/sistema.db`, e as amostras faciais são armazenadas em `dataset/nivelX_usuario/`. Os cadastros continuam disponíveis quando o programa é reaberto. **Não compartilhe sua pasta `dataset/` após cadastrar pessoas reais.**

## Técnicas utilizadas

- **Detecção**: classificador Haar Cascade do OpenCV localiza rostos na imagem recebida pela câmera.
- **Pré-processamento**: conversão BGR→tons de cinza, redimensionamento para 120×120 pixels e equalização do histograma para reduzir variações simples de iluminação.
- **Extração de características**: LBP compara cada pixel com seus oito vizinhos e agrega histogramas em grade 6×6 (9216 números). Essa técnica é diferente dos embeddings de 128 dimensões do `face_recognition` original.
- **Correspondência**: calcula a distância qui-quadrado entre cada amostra cadastrada e a imagem atual, selecionando a menor. Um limite experimental de 0,40 e cinco quadros consecutivos são empregados para reduzir aceitação acidental, **sem garantia de desempenho**.
- **Persistência / autorização**: SQLite armazena cadastros e níveis; consultas SQL com parâmetros liberam apenas registros cujo `nivel_requerido <= nivel_acesso`.

## Arquivos principais

- `src/main.py`: abre a interface por padrão; oferece `--cli` para o menu antigo.
- `src/gui.py`: interface gráfica em Tkinter, botões, cadastro e painel de permissões.
- `src/facial_auth.py`: cadastro, extração LBP, comparação e reconhecimento pela câmera.
- `src/database_setup.py`: criação e carga inicial do banco SQLite, sem apagar cadastros.
- `requirements.txt`: dependências compatíveis com Python 3.13.

## Limitações de teste

O código foi verificado em Python 3.13 com OpenCV e NumPy, mas não foi possível validar o uso de uma webcam física neste ambiente. O limiar de similaridade depende de testes com rostos diferentes sob várias condições; recomenda-se avaliar falso aceite e falsa rejeição antes da demonstração.

## Correção: falha ao carregar o Haar Cascade

O projeto inclui agora `src/models/haarcascade_frontalface_default.xml`, que deve permanecer junto do código. O `AutenticadorFacial` procura primeiro esse arquivo e depois o diretório interno do OpenCV. Isso evita o erro `Can't open file ... in read mode` causado pela ausência do XML no ambiente Python.

Após extrair o ZIP, execute `.venv\Scripts\python.exe -m src.main` na pasta do projeto. Caso o erro continue, confirme que o arquivo XML foi extraído em `src/models/`.
>>>>>>> 6808bd6 (APS_5_6BiometriaFacial)
