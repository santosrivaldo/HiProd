import time
import psutil
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry
import ssl
import socket
import win32gui
from datetime import datetime, time as dt_time
import pytz
import os
import json
import subprocess
import re
import sys
import logging
from urllib.parse import urlparse

# Detectar se está rodando como executável (precisa estar antes de outras funções)
IS_EXECUTABLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def _get_base_directory():
    """Retorna o diretório base (do executável ou do script)"""
    if IS_EXECUTABLE:
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def _create_env_from_example():
    """Cria arquivo .env automaticamente a partir do config.example se não existir"""
    base_dir = _get_base_directory()
    env_path = os.path.join(base_dir, '.env')
    example_path = os.path.join(base_dir, 'config.example')
    
    # Se .env já existe, não fazer nada
    if os.path.exists(env_path):
        return env_path
    
    # Se config.example existe, copiar para .env
    if os.path.exists(example_path):
        try:
            import shutil
            shutil.copy2(example_path, env_path)
            if not IS_EXECUTABLE:
                print(f"[INFO] Arquivo .env criado automaticamente a partir de config.example")
                print(f"[INFO] Localização: {env_path}")
                print(f"[INFO] ⚠️  IMPORTANTE: Edite o arquivo .env e configure suas credenciais!")
                print(f"[INFO]    - API_URL=http://seu-servidor:8010 (opcional)")
                print(f"[INFO]    - API_URL=http://seu-servidor:8010")
            return env_path
        except Exception as e:
            if not IS_EXECUTABLE:
                print(f"[WARN] Não foi possível criar .env automaticamente: {e}")
    
    return env_path

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    
    # Criar .env automaticamente se não existir
    env_path = _create_env_from_example()
    
    # Carregar variáveis de ambiente
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Tentar carregar do diretório atual também
        load_dotenv()
except ImportError:
    # Se python-dotenv não estiver disponível, usar apenas variáveis de ambiente do sistema
    pass

def safe_print(*args, **kwargs):
    """Print seguro - em executável vai para log, em script vai para console"""
    if IS_EXECUTABLE:
        # Quando executável, usar logging em vez de print
        try:
            import logging
            message = ' '.join(str(arg) for arg in args)
            logging.info(message)
        except:
            # Fallback: tentar escrever em arquivo de log diretamente
            try:
                log_file = os.path.join(os.path.dirname(sys.executable), 'hiprod-agent.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(' '.join(str(arg) for arg in args) + '\n')
            except:
                pass  # Silencioso se falhar
    else:
        # Quando script Python, imprimir normalmente
        print(*args, **kwargs)

# ========================================
# MÓDULO DE DETECÇÃO FACIAL (INTEGRADO)
# ========================================
# Código de detecção facial integrado diretamente no agent.py
# Não há dependência de arquivo face_detection.py separado
# Tudo compila em um único executável

# Tentar importar OpenCV para detecção facial
try:
    import cv2
    # Verificar se cv2 foi importado corretamente
    if cv2 is None:
        raise ImportError("cv2 importado mas é None")
    # Testar se cv2.data está disponível
    try:
        _ = cv2.data.haarcascades
    except AttributeError:
        print("[WARN] OpenCV importado mas cv2.data não está disponível")
        raise ImportError("cv2.data não disponível")
    FACE_DETECTION_AVAILABLE = True
    print("[INFO] ✓ OpenCV (cv2) carregado com sucesso - Detecção facial disponível")
except ImportError as e:
    FACE_DETECTION_AVAILABLE = False
    cv2 = None
    print(f"[WARN] OpenCV não encontrado ou não disponível: {e}")
    print("[WARN] Verificação facial desabilitada.")
    print("[WARN] Para habilitar, instale: pip install opencv-python")
except Exception as e:
    FACE_DETECTION_AVAILABLE = False
    cv2 = None
    print(f"[WARN] Erro ao importar OpenCV: {e}")
    print("[WARN] Verificação facial desabilitada.")

# Classe para rastrear tempo de presença
class FacePresenceTracker:
    """
    Rastreia o tempo que uma pessoa passa em frente à câmera.
    Mantém um histórico de detecções e calcula o tempo total de presença.
    """
    def __init__(self):
        self.presence_start = None  # Timestamp quando a presença começou
        self.last_detection = None  # Timestamp da última detecção
        self.total_presence_time = 0  # Tempo total acumulado em segundos
        self.last_check_time = None  # Timestamp da última verificação
        self.check_interval = 60  # Intervalo entre verificações (60 segundos = 1 minuto)
        self.presence_threshold = 3  # Número de detecções consecutivas para confirmar presença
        
    def update_presence(self, face_detected, check_time=None):
        """
        Atualiza o estado de presença baseado na detecção facial.
        
        Args:
            face_detected: bool - Se uma face foi detectada
            check_time: float - Timestamp da verificação (opcional, usa time.time() se None)
        
        Returns:
            dict: Informações sobre o estado atual de presença
        """
        if check_time is None:
            check_time = time.time()
        
        current_time = check_time
        
        if face_detected:
            # Face detectada
            if self.last_detection is None:
                # Primeira detecção - iniciar rastreamento
                self.presence_start = current_time
                self.last_detection = current_time
            else:
                # Continuidade de presença - atualizar última detecção
                time_since_last = current_time - self.last_detection
                
                # Se passou muito tempo desde a última detecção, reiniciar
                if time_since_last > self.check_interval * 2:
                    # Presença interrompida e retomada
                    if self.presence_start is not None:
                        # Adicionar tempo acumulado antes de reiniciar
                        self.total_presence_time += self.last_detection - self.presence_start
                    self.presence_start = current_time
                
                self.last_detection = current_time
        else:
            # Nenhuma face detectada
            if self.last_detection is not None:
                # Havia presença antes - finalizar período
                time_since_last = current_time - self.last_detection
                
                if time_since_last > self.check_interval * 2:
                    # Presença definitivamente encerrada
                    if self.presence_start is not None:
                        self.total_presence_time += self.last_detection - self.presence_start
                    self.presence_start = None
                    self.last_detection = None
        
        self.last_check_time = current_time
        
        # Calcular tempo de presença atual
        current_presence_time = 0
        if self.presence_start is not None and self.last_detection is not None:
            current_presence_time = self.last_detection - self.presence_start
        
        return {
            'is_present': face_detected and self.last_detection is not None,
            'current_session_time': current_presence_time,
            'total_presence_time': self.total_presence_time + current_presence_time,
            'last_detection': self.last_detection,
            'presence_start': self.presence_start
        }
    
    def get_presence_time(self):
        """
        Retorna o tempo total de presença acumulado (em segundos).
        Inclui o tempo da sessão atual se houver presença ativa.
        
        Returns:
            float: Tempo total em segundos
        """
        current_presence = 0
        if self.presence_start is not None and self.last_detection is not None:
            current_presence = self.last_detection - self.presence_start
        
        return self.total_presence_time + current_presence
    
    def reset(self):
        """Reseta o rastreamento (útil ao trocar de usuário)"""
        # Salvar tempo atual antes de resetar
        final_time = self.get_presence_time()
        self.presence_start = None
        self.last_detection = None
        self.total_presence_time = 0
        self.last_check_time = None
        return final_time

# Instância global do tracker
_presence_tracker = FacePresenceTracker()

def get_haarcascade_path():
    """
    Retorna o caminho para o arquivo haarcascade_frontalface_default.xml
    Tenta encontrar em vários locais possíveis
    """
    if not FACE_DETECTION_AVAILABLE or cv2 is None:
        return None
    
    # Lista de possíveis locais
    possible_paths = []
    
    # Se for executável, procurar primeiro em sys._MEIPASS (onde PyInstaller coloca os dados)
    if IS_EXECUTABLE:
        try:
            meipass = sys._MEIPASS
            possible_paths.extend([
                os.path.join(meipass, 'haarcascade_frontalface_default.xml'),
                os.path.join(meipass, 'data', 'haarcascade_frontalface_default.xml'),
                # Procurar no caminho do OpenCV dentro do _MEIPASS
                os.path.join(meipass, 'cv2', 'data', 'haarcascades', 'haarcascade_frontalface_default.xml'),
            ])
            
            # Tentar usar cv2.data mesmo quando executável (pode funcionar se PyInstaller incluiu corretamente)
            try:
                possible_paths.append(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
            except:
                pass
        except:
            pass
        
        # Também procurar no diretório do executável
        base_dir = os.path.dirname(sys.executable)
        possible_paths.extend([
            os.path.join(base_dir, 'haarcascade_frontalface_default.xml'),
            os.path.join(base_dir, 'data', 'haarcascade_frontalface_default.xml'),
        ])
    
    # Procurar no diretório do script (quando rodando como script Python)
    if not IS_EXECUTABLE:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths.extend([
            os.path.join(script_dir, 'haarcascade_frontalface_default.xml'),
            os.path.join(script_dir, 'data', 'haarcascade_frontalface_default.xml'),
        ])
    
    # Procurar no diretório de dados do OpenCV (instalação padrão)
    try:
        possible_paths.append(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
    except:
        pass
    
    # Verificar cada caminho
    for path in possible_paths:
        if os.path.exists(path):
            if IS_EXECUTABLE:
                print(f"[FACE] Haarcascade encontrado em: {path}")
            return path
    
    # Se não encontrou, mostrar informações de debug quando executável
    if IS_EXECUTABLE:
        print(f"[FACE] AVISO: Haarcascade não encontrado em nenhum dos caminhos:")
        for i, path in enumerate(possible_paths, 1):
            print(f"  {i}. {path} (existe: {os.path.exists(path)})")
        try:
            print(f"[FACE] sys._MEIPASS: {sys._MEIPASS}")
            print(f"[FACE] sys.executable: {sys.executable}")
        except:
            pass
    
    # Se não encontrou, retornar None (será tratado no código)
    return None

def check_face_presence(timeout=5, camera_index=0):
    """
    Verifica se há uma pessoa em frente à câmera usando detecção facial.
    
    Args:
        timeout: Tempo máximo em segundos para tentar detectar uma face
        camera_index: Índice da câmera a ser usada (padrão: 0)
    
    Returns:
        bool: True se uma face foi detectada, False caso contrário
    """
    if not FACE_DETECTION_AVAILABLE or cv2 is None:
        return False
    
    try:
        # Obter caminho do classificador
        cascade_path = get_haarcascade_path()
        face_cascade = None
        
        if cascade_path is None:
            # Tentar usar o caminho padrão do OpenCV
            try:
                default_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
                if IS_EXECUTABLE:
                    print(f"[FACE] Procurando haarcascade em: {default_path}")
                face_cascade = cv2.CascadeClassifier(default_path)
                if face_cascade.empty():
                    if IS_EXECUTABLE:
                        print(f"[FACE] Erro: Classificador vazio em {default_path}")
                    return False
            except Exception as e:
                if IS_EXECUTABLE:
                    print(f"[FACE] Erro ao usar caminho padrão do OpenCV: {e}")
                return False
        else:
            if IS_EXECUTABLE:
                print(f"[FACE] Usando haarcascade encontrado em: {cascade_path}")
            face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Verificar se o classificador foi carregado corretamente
        if face_cascade is None or face_cascade.empty():
            if IS_EXECUTABLE:
                print(f"[FACE] Erro: Classificador de faces vazio ou inválido em: {cascade_path}")
            return False
        
        # Tentar abrir a câmera
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"[FACE] Erro: Não foi possível abrir a câmera (índice {camera_index})")
            return False
        
        # Configurar resolução (reduzir para melhor performance)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        start_time = time.time()
        face_detected = False
        
        # Tentar detectar face por até 'timeout' segundos
        while (time.time() - start_time) < timeout:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Converter para escala de cinza (mais rápido para detecção)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detectar faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Se detectou pelo menos uma face
            if len(faces) > 0:
                face_detected = True
                print(f"[FACE] ✓ Face detectada! ({len(faces)} face(s) encontrada(s))")
                break
            
            # Pequeno delay para não sobrecarregar a CPU
            time.sleep(0.1)
        
        # Liberar recursos
        cap.release()
        
        if not face_detected:
            print("[FACE] ✗ Nenhuma face detectada no tempo limite")
        
        return face_detected
        
    except Exception as e:
        print(f"[FACE] Erro durante detecção facial: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_face_presence_silent(timeout=5, camera_index=0):
    """
    Versão silenciosa da verificação de presença (sem prints).
    Útil quando executado como executável.
    
    Args:
        timeout: Tempo máximo em segundos para tentar detectar uma face
        camera_index: Índice da câmera a ser usada (padrão: 0)
    
    Returns:
        bool: True se uma face foi detectada, False caso contrário
    """
    if not FACE_DETECTION_AVAILABLE or cv2 is None:
        return False
    
    try:
        # Obter caminho do classificador
        cascade_path = get_haarcascade_path()
        
        if cascade_path is None:
            try:
                default_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
                face_cascade = cv2.CascadeClassifier(default_path)
                if face_cascade.empty():
                    return False
            except:
                return False
        else:
            face_cascade = cv2.CascadeClassifier(cascade_path)
            if face_cascade.empty():
                return False
        
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            return False
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        start_time = time.time()
        face_detected = False
        
        while (time.time() - start_time) < timeout:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) > 0:
                face_detected = True
                break
            
            time.sleep(0.1)
        
        cap.release()
        return face_detected
        
    except Exception as e:
        return False

def get_presence_tracker():
    """
    Retorna a instância global do rastreador de presença.
    
    Returns:
        FacePresenceTracker: Instância do tracker
    """
    return _presence_tracker

def reset_presence_tracker():
    """
    Reseta o rastreador de presença e retorna o tempo total acumulado.
    
    Returns:
        float: Tempo total de presença antes do reset (em segundos)
    """
    return _presence_tracker.reset()

# ========================================
# FIM DO MÓDULO DE DETECÇÃO FACIAL
# ========================================

# Variável global para controlar se o agente deve parar
AGENT_SHOULD_STOP = False

def check_stop_flag():
    """Verifica se existe flag de parada"""
    global AGENT_SHOULD_STOP
    try:
        flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.agent_stop_flag')
        if os.path.exists(flag_file):
            with open(flag_file, 'r') as f:
                content = f.read().strip()
                if content == 'STOP':
                    AGENT_SHOULD_STOP = True
                    # Remover flag
                    try:
                        os.remove(flag_file)
                    except:
                        pass
                    return True
    except:
        pass
    return AGENT_SHOULD_STOP

def check_pause_flag():
    """Verifica se existe flag de pausa (intervalo)"""
    try:
        flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.agent_pause_flag')
        if os.path.exists(flag_file):
            with open(flag_file, 'r') as f:
                content = f.read().strip()
                if content == 'PAUSED':
                    return True
    except:
        pass
    return False
try:
    import pygetwindow as gw
    import pyperclip
except ImportError:
    gw = None
    pyperclip = None

# ========================================
# CONFIGURAÇÕES - Carregadas de variáveis de ambiente
# ========================================
# IMPORTANTE: Configure as variáveis de ambiente ou crie um arquivo .env
# Veja config.example para exemplo de configuração

# URL da API do HiProd (opcional - tem valor padrão)
# ⚠️ IMPORTANTE: Configure para HTTPS para usar handshake TLS
API_BASE_URL = os.getenv('API_URL', 'https://hiprod.grupohi.com.br')
ATIVIDADE_URL = f"{API_BASE_URL}/api/atividade"
USUARIOS_MONITORADOS_URL = f"{API_BASE_URL}/api/usuarios-monitorados"

# Configuração SSL/TLS
SSL_VERIFY = os.getenv('SSL_VERIFY', 'true').lower() == 'true'
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', None)  # Caminho opcional para certificado customizado

# Configurações de monitoramento
SCREENSHOT_ENABLED = True      # Habilitar captura de screenshots (futuro)
SCREENSHOT_QUALITY = 55        # Qualidade do screenshot (1-100)
MONITOR_INTERVAL = 10          # Intervalo entre verificações (segundos)
IDLE_THRESHOLD = 600           # Tempo de inatividade para considerar ocioso (segundos)
REQUEST_TIMEOUT = 30           # Timeout para requisições HTTP (segundos)
MAX_RETRIES = 3                # Número máximo de tentativas em caso de falha

# ========================================
# BASE DE DADOS DE APLICATIVOS EXPANDIDA
# ========================================

# Mapeamento de aplicativos por processo/janela (SEM PRODUTIVIDADE)
APPLICATION_DATABASE = {
    # Navegadores
    'chrome.exe': {
        'name': 'Google Chrome',
        'category': 'navegador',
        'keywords': ['chrome', 'google chrome', 'chromium']
    },
    'firefox.exe': {
        'name': 'Mozilla Firefox',
        'category': 'navegador', 
        'keywords': ['firefox', 'mozilla']
    },
    'msedge.exe': {
        'name': 'Microsoft Edge',
        'category': 'navegador',
        'keywords': ['edge', 'microsoft edge']
    },
    'opera.exe': {
        'name': 'Opera',
        'category': 'navegador',
        'keywords': ['opera']
    },
    'brave.exe': {
        'name': 'Brave Browser',
        'category': 'navegador',
        'keywords': ['brave']
    },
    
    # Desenvolvimento
    'code.exe': {
        'name': 'Visual Studio Code',
        'category': 'desenvolvimento',
        'keywords': ['visual studio code', 'vs code', 'vscode']
    },
    'devenv.exe': {
        'name': 'Visual Studio',
        'category': 'desenvolvimento',
        'keywords': ['visual studio', 'vs2019', 'vs2022']
    },
    'pycharm64.exe': {
        'name': 'PyCharm',
        'category': 'desenvolvimento',
        'keywords': ['pycharm', 'jetbrains']
    },
    'idea64.exe': {
        'name': 'IntelliJ IDEA',
        'category': 'desenvolvimento',
        'keywords': ['intellij', 'idea']
    },
    'sublime_text.exe': {
        'name': 'Sublime Text',
        'category': 'desenvolvimento',
        'keywords': ['sublime text', 'sublime']
    },
    'notepad++.exe': {
        'name': 'Notepad++',
        'category': 'desenvolvimento',
        'keywords': ['notepad++', 'npp']
    },
    'atom.exe': {
        'name': 'Atom',
        'category': 'desenvolvimento',
        'keywords': ['atom']
    },
    
    # Office/Produtividade
    'winword.exe': {
        'name': 'Microsoft Word',
        'category': 'escritorio',
        'keywords': ['word', 'microsoft word', 'documento']
    },
    'excel.exe': {
        'name': 'Microsoft Excel',
        'category': 'escritorio',
        'keywords': ['excel', 'microsoft excel', 'planilha']
    },
    'powerpnt.exe': {
        'name': 'Microsoft PowerPoint',
        'category': 'escritorio',
        'keywords': ['powerpoint', 'microsoft powerpoint', 'apresentacao']
    },
    'outlook.exe': {
        'name': 'Microsoft Outlook',
        'category': 'comunicacao',
        'keywords': ['outlook', 'microsoft outlook', 'email']
    },
    'onenote.exe': {
        'name': 'Microsoft OneNote',
        'category': 'escritorio',
        'keywords': ['onenote', 'microsoft onenote']
    },
    
    # Comunicação/Colaboração
    'teams.exe': {
        'name': 'Microsoft Teams',
        'category': 'comunicacao',
        'keywords': ['teams', 'microsoft teams']
    },
    'slack.exe': {
        'name': 'Slack',
        'category': 'comunicacao',
        'keywords': ['slack']
    },
    'discord.exe': {
        'name': 'Discord',
        'category': 'comunicacao',
        'keywords': ['discord']
    },
    'whatsapp.exe': {
        'name': 'WhatsApp Desktop',
        'category': 'comunicacao',
        'keywords': ['whatsapp']
    },
    'telegram.exe': {
        'name': 'Telegram Desktop',
        'category': 'comunicacao',
        'keywords': ['telegram']
    },
    'zoom.exe': {
        'name': 'Zoom',
        'category': 'comunicacao',
        'keywords': ['zoom']
    },
    'skype.exe': {
        'name': 'Skype',
        'category': 'comunicacao',
        'keywords': ['skype']
    },
    
    # Design/Criação
    'photoshop.exe': {
        'name': 'Adobe Photoshop',
        'category': 'design',
        'keywords': ['photoshop', 'adobe photoshop']
    },
    'illustrator.exe': {
        'name': 'Adobe Illustrator',
        'category': 'design',
        'keywords': ['illustrator', 'adobe illustrator']
    },
    'indesign.exe': {
        'name': 'Adobe InDesign',
        'category': 'design',
        'keywords': ['indesign', 'adobe indesign']
    },
    'figma.exe': {
        'name': 'Figma',
        'category': 'design',
        'keywords': ['figma']
    },
    'canva.exe': {
        'name': 'Canva',
        'category': 'design',
        'keywords': ['canva']
    },
    
    # Sistema/Utilitários
    'explorer.exe': {
        'name': 'Windows Explorer',
        'category': 'sistema',
        'keywords': ['explorer', 'windows explorer', 'arquivos', 'file explorer']
    },
    'notepad.exe': {
        'name': 'Notepad',
        'category': 'sistema',
        'keywords': ['notepad', 'bloco de notas']
    },
    'calc.exe': {
        'name': 'Calculadora',
        'category': 'sistema',
        'keywords': ['calculadora', 'calculator']
    },
    'cmd.exe': {
        'name': 'Prompt de Comando',
        'category': 'sistema',
        'keywords': ['cmd', 'prompt', 'terminal', 'command prompt']
    },
    'powershell.exe': {
        'name': 'PowerShell',
        'category': 'sistema',
        'keywords': ['powershell', 'terminal']
    },
    'taskmgr.exe': {
        'name': 'Gerenciador de Tarefas',
        'category': 'sistema',
        'keywords': ['task manager', 'gerenciador de tarefas']
    },
    'control.exe': {
        'name': 'Painel de Controle',
        'category': 'sistema',
        'keywords': ['control panel', 'painel de controle']
    },
    'msconfig.exe': {
        'name': 'Configuração do Sistema',
        'category': 'sistema',
        'keywords': ['msconfig', 'configuracao do sistema']
    },
    'regedit.exe': {
        'name': 'Editor do Registro',
        'category': 'sistema',
        'keywords': ['regedit', 'registry editor']
    },
    'services.exe': {
        'name': 'Serviços do Windows',
        'category': 'sistema',
        'keywords': ['services', 'servicos']
    },
    'mmc.exe': {
        'name': 'Console de Gerenciamento',
        'category': 'sistema',
        'keywords': ['mmc', 'management console']
    },
    'winrar.exe': {
        'name': 'WinRAR',
        'category': 'sistema',
        'keywords': ['winrar', 'rar']
    },
    '7zfm.exe': {
        'name': '7-Zip',
        'category': 'sistema',
        'keywords': ['7-zip', '7zip']
    },
    'mspaint.exe': {
        'name': 'Paint',
        'category': 'sistema',
        'keywords': ['paint', 'mspaint']
    },
    'snippingtool.exe': {
        'name': 'Ferramenta de Captura',
        'category': 'sistema',
        'keywords': ['snipping tool', 'captura']
    },
    'osk.exe': {
        'name': 'Teclado Virtual',
        'category': 'sistema',
        'keywords': ['on-screen keyboard', 'teclado virtual']
    },
    'magnify.exe': {
        'name': 'Lupa',
        'category': 'sistema',
        'keywords': ['magnifier', 'lupa']
    },
    
    # Entretenimento
    'spotify.exe': {
        'name': 'Spotify',
        'category': 'entretenimento',
        'keywords': ['spotify', 'musica']
    },
    'vlc.exe': {
        'name': 'VLC Media Player',
        'category': 'entretenimento',
        'keywords': ['vlc', 'media player']
    },
    'steam.exe': {
        'name': 'Steam',
        'category': 'entretenimento',
        'keywords': ['steam', 'jogos', 'games']
    },
    
    # Banco de Dados/Análise
    'ssms.exe': {
        'name': 'SQL Server Management Studio',
        'category': 'desenvolvimento',
        'keywords': ['sql server', 'ssms', 'database']
    },
    'mysql-workbench.exe': {
        'name': 'MySQL Workbench',
        'category': 'desenvolvimento',
        'keywords': ['mysql', 'workbench', 'database']
    },
    'pgadmin4.exe': {
        'name': 'pgAdmin',
        'category': 'desenvolvimento',
        'keywords': ['pgadmin', 'postgresql', 'database']
    },
    
    # Virtualização/Containers
    'docker desktop.exe': {
        'name': 'Docker Desktop',
        'category': 'desenvolvimento',
        'keywords': ['docker', 'container']
    },
    'vmware.exe': {
        'name': 'VMware',
        'category': 'desenvolvimento',
        'keywords': ['vmware', 'virtual machine']
    },
    'virtualbox.exe': {
        'name': 'VirtualBox',
        'category': 'desenvolvimento',
        'keywords': ['virtualbox', 'virtual machine']
    }
}

# Mapeamento de domínios para categorização (SEM PRODUTIVIDADE)
DOMAIN_DATABASE = {
    # Trabalho/Desenvolvimento
    'github.com': {'category': 'desenvolvimento'},
    'gitlab.com': {'category': 'desenvolvimento'},
    'bitbucket.org': {'category': 'desenvolvimento'},
    'stackoverflow.com': {'category': 'desenvolvimento'},
    'docs.microsoft.com': {'category': 'documentacao'},
    'developer.mozilla.org': {'category': 'documentacao'},
    'w3schools.com': {'category': 'documentacao'},
    'medium.com': {'category': 'documentacao'},
    'dev.to': {'category': 'desenvolvimento'},
    
    # Google Workspace
    'docs.google.com': {'category': 'escritorio'},
    'sheets.google.com': {'category': 'escritorio'},
    'slides.google.com': {'category': 'escritorio'},
    'drive.google.com': {'category': 'escritorio'},
    'gmail.com': {'category': 'comunicacao'},
    'calendar.google.com': {'category': 'escritorio'},
    
    # Microsoft 365
    'office.com': {'category': 'escritorio'},
    'outlook.office.com': {'category': 'comunicacao'},
    'teams.microsoft.com': {'category': 'comunicacao'},
    'onedrive.com': {'category': 'escritorio'},
    'sharepoint.com': {'category': 'escritorio'},
    
    # Ferramentas de Desenvolvimento
    'aws.amazon.com': {'category': 'desenvolvimento'},
    'console.aws.amazon.com': {'category': 'desenvolvimento'},
    'azure.microsoft.com': {'category': 'desenvolvimento'},
    'cloud.google.com': {'category': 'desenvolvimento'},
    'heroku.com': {'category': 'desenvolvimento'},
    'vercel.com': {'category': 'desenvolvimento'},
    'netlify.com': {'category': 'desenvolvimento'},
    
    # Comunicação Profissional
    'slack.com': {'category': 'comunicacao'},
    'discord.com': {'category': 'comunicacao'},
    'web.whatsapp.com': {'category': 'comunicacao'},
    'telegram.org': {'category': 'comunicacao'},
    
    # Entretenimento/Não Produtivo
    'youtube.com': {'category': 'entretenimento'},
    'netflix.com': {'category': 'entretenimento'},
    'twitch.tv': {'category': 'entretenimento'},
    'instagram.com': {'category': 'social'},
    'facebook.com': {'category': 'social'},
    'twitter.com': {'category': 'social'},
    'x.com': {'category': 'social'},
    'tiktok.com': {'category': 'social'},
    'linkedin.com': {'category': 'social'},
    
    # E-commerce/Compras
    'amazon.com': {'category': 'compras'},
    'mercadolivre.com.br': {'category': 'compras'},
    'americanas.com.br': {'category': 'compras'},
    'magazineluiza.com.br': {'category': 'compras'},
    'shopee.com.br': {'category': 'compras'},
    
    # Notícias/Informação
    'g1.globo.com': {'category': 'noticias'},
    'uol.com.br': {'category': 'noticias'},
    'folha.uol.com.br': {'category': 'noticias'},
    'estadao.com.br': {'category': 'noticias'},
    'bbc.com': {'category': 'noticias'},
    'cnn.com': {'category': 'noticias'},
    
    # Ferramentas Online
    'canva.com': {'category': 'design'},
    'figma.com': {'category': 'design'},
    'trello.com': {'category': 'produtividade'},
    'notion.so': {'category': 'produtividade'},
    'asana.com': {'category': 'produtividade'},
    'monday.com': {'category': 'produtividade'},
    'jira.atlassian.com': {'category': 'desenvolvimento'},
    'confluence.atlassian.com': {'category': 'documentacao'},
    
    # Bancos/Financeiro
    'bb.com.br': {'category': 'financeiro'},
    'itau.com.br': {'category': 'financeiro'},
    'bradesco.com.br': {'category': 'financeiro'},
    'santander.com.br': {'category': 'financeiro'},
    'caixa.gov.br': {'category': 'financeiro'},
    'nubank.com.br': {'category': 'financeiro'},
    
    # Educação/Aprendizado
    'coursera.org': {'category': 'educacao'},
    'udemy.com': {'category': 'educacao'},
    'edx.org': {'category': 'educacao'},
    'khanacademy.org': {'category': 'educacao'},
    'duolingo.com': {'category': 'educacao'},
    
    # Sistema/Localhost
    'localhost': {'category': 'desenvolvimento'},
    '127.0.0.1': {'category': 'desenvolvimento'},
    '192.168.': {'category': 'desenvolvimento'},  # Rede local
    '10.0.': {'category': 'desenvolvimento'},     # Rede local
}

# Não há mais autenticação - a API identifica pelo nome do usuário do Windows

# Configurar logging baseado no modo de execução
if IS_EXECUTABLE:
    # Quando executável, logar apenas em arquivo (sem console)
    try:
        log_file = os.path.join(os.path.dirname(sys.executable), 'hiprod-agent.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8', errors='ignore'),
            ]
        )
        # Console está desabilitado no .spec (console=False)
        # Todos os logs vão apenas para o arquivo hiprod-agent.log
    except Exception as e:
        # Se logging falhar, tentar criar arquivo de log simples
        try:
            log_file = os.path.join(os.path.dirname(sys.executable), 'hiprod-agent.log')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[ERROR] Erro ao configurar logging: {e}\n")
        except:
            pass
else:
    # Quando script Python, usar console normal
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def create_secure_session():
    """
    Cria uma sessão HTTP com handshake TLS e verificação de certificado SSL.
    Implementa retry automático e configurações de segurança.
    """
    session = requests.Session()
    
    # Configurar retry automático
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Configurar verificação SSL/TLS
    if API_BASE_URL.startswith('https://'):
        if SSL_VERIFY:
            if SSL_CERT_PATH and os.path.exists(SSL_CERT_PATH):
                # Usar certificado customizado se fornecido
                session.verify = SSL_CERT_PATH
                safe_print(f"[TLS] Usando certificado customizado: {SSL_CERT_PATH}")
            else:
                # Verificação padrão com certificados do sistema
                session.verify = True
                safe_print("[TLS] Verificação SSL habilitada (certificados do sistema)")
        else:
            # AVISO: Desabilitar verificação SSL é inseguro (apenas para desenvolvimento)
            session.verify = False
            safe_print("[TLS] ⚠️ AVISO: Verificação SSL DESABILITADA (inseguro!)")
    
    # Configurar timeout padrão
    session.timeout = REQUEST_TIMEOUT
    
    return session

# Sessão global com TLS configurado
_secure_session = None

def get_secure_session():
    """Retorna a sessão HTTP segura (criada com handshake TLS)"""
    global _secure_session
    if _secure_session is None:
        _secure_session = create_secure_session()
    return _secure_session

def perform_tls_handshake(url):
    """
    Realiza handshake TLS explícito com o servidor antes de fazer requisições.
    Verifica se o servidor suporta TLS e valida o certificado.
    
    Args:
        url: URL do servidor (deve começar com https://)
    
    Returns:
        bool: True se handshake foi bem-sucedido, False caso contrário
    """
    if not url.startswith('https://'):
        safe_print(f"[TLS] URL não é HTTPS: {url}")
        return False
    
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or 443
        
        safe_print(f"[TLS] Iniciando handshake TLS com {hostname}:{port}...")
        
        # Criar contexto SSL com verificação de certificado
        context = ssl.create_default_context()
        
        # Se há certificado customizado, carregá-lo
        if SSL_CERT_PATH and os.path.exists(SSL_CERT_PATH):
            context.load_verify_locations(SSL_CERT_PATH)
            safe_print(f"[TLS] Certificado customizado carregado: {SSL_CERT_PATH}")
        
        # Criar socket e fazer handshake TLS
        sock = socket.create_connection((hostname, port), timeout=10)
        ssock = context.wrap_socket(sock, server_hostname=hostname)
        
        # Obter informações do certificado
        cert = ssock.getpeercert()
        cipher = ssock.cipher()
        
        safe_print(f"[TLS] ✅ Handshake TLS bem-sucedido!")
        safe_print(f"[TLS]    Servidor: {hostname}:{port}")
        safe_print(f"[TLS]    Protocolo: {ssock.version()}")
        safe_print(f"[TLS]    Cipher: {cipher[0]} ({cipher[1]})")
        safe_print(f"[TLS]    Certificado válido até: {cert.get('notAfter', 'N/A')}")
        
        ssock.close()
        sock.close()
        
        return True
        
    except ssl.SSLError as e:
        safe_print(f"[TLS] ❌ Erro SSL durante handshake: {e}")
        if "certificate verify failed" in str(e):
            safe_print("[TLS]    Certificado SSL inválido ou não confiável")
            safe_print("[TLS]    Verifique se o certificado está correto ou configure SSL_CERT_PATH")
        return False
    except socket.timeout:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or 443
        safe_print(f"[TLS] ❌ Timeout ao conectar com {hostname}:{port}")
        return False
    except Exception as e:
        safe_print(f"[TLS] ❌ Erro durante handshake TLS: {e}")
        return False

def get_headers(usuario_nome=None):
    """
    Retorna headers para requisições HTTP.
    Inclui o nome do usuário do Windows como identificação.
    """
    headers = {
        "Content-Type": "application/json"
    }
    
    # Adicionar nome do usuário como identificação (se fornecido)
    if usuario_nome:
        headers["X-User-Name"] = usuario_nome
    
    return headers

def load_learned_applications():
    """Carrega aplicações aprendidas do arquivo JSON"""
    global _LEARNED_APPLICATIONS
    try:
        if os.path.exists(_LEARNED_APPS_FILE):
            with open(_LEARNED_APPS_FILE, 'r', encoding='utf-8') as f:
                _LEARNED_APPLICATIONS = json.load(f)
            safe_print(f"[LEARN] Carregadas {len(_LEARNED_APPLICATIONS)} aplicações aprendidas")
        else:
            _LEARNED_APPLICATIONS = {}
            safe_print("[LEARN] Nenhuma aplicação aprendida encontrada")
    except Exception as e:
        safe_print(f"[WARN] Erro ao carregar aplicações aprendidas: {e}")
        _LEARNED_APPLICATIONS = {}

def save_learned_applications():
    """Salva aplicações aprendidas no arquivo JSON"""
    try:
        with open(_LEARNED_APPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_LEARNED_APPLICATIONS, f, ensure_ascii=False, indent=2)
        safe_print(f"[LEARN] Aplicações aprendidas salvas: {len(_LEARNED_APPLICATIONS)}")
    except Exception as e:
        safe_print(f"[ERROR] Erro ao salvar aplicações aprendidas: {e}")

def learn_application(process_name, window_title, application_name=None):
    """Aprende uma nova aplicação e adiciona ao catálogo aprendido"""
    if not process_name:
        return
    
    process_lower = process_name.lower()
    
    # Não aprender se já está na base de dados principal
    if process_lower in APPLICATION_DATABASE:
        return
    
    # Não aprender se já foi aprendida
    if process_lower in _LEARNED_APPLICATIONS:
        return
    
    # Criar entrada para a aplicação aprendida
    if not application_name:
        # Usar nome do processo sem extensão como nome da aplicação
        application_name = process_name.replace('.exe', '').replace('.EXE', '')
    
    # Extrair categoria básica do título da janela
    category = 'sistema'  # padrão
    title_lower = (window_title or '').lower()
    
    if any(word in title_lower for word in ['chrome', 'firefox', 'edge', 'opera', 'brave', 'navegador', 'browser']):
        category = 'navegador'
    elif any(word in title_lower for word in ['code', 'visual studio', 'pycharm', 'intellij', 'sublime', 'editor']):
        category = 'desenvolvimento'
    elif any(word in title_lower for word in ['word', 'excel', 'powerpoint', 'office', 'documento']):
        category = 'escritorio'
    elif any(word in title_lower for word in ['teams', 'slack', 'discord', 'whatsapp', 'telegram', 'email']):
        category = 'comunicacao'
    elif any(word in title_lower for word in ['photoshop', 'illustrator', 'figma', 'design', 'canva']):
        category = 'design'
    elif any(word in title_lower for word in ['youtube', 'netflix', 'spotify', 'jogo', 'game']):
        category = 'entretenimento'
    
    # Adicionar ao catálogo aprendido
    _LEARNED_APPLICATIONS[process_lower] = {
        'name': application_name,
        'category': category,
        'keywords': [application_name.lower(), process_lower],
        'first_seen': datetime.now(pytz.timezone('America/Sao_Paulo')).isoformat(),
        'window_title_sample': window_title[:100] if window_title else None,
        'usage_count': 1
    }
    
    safe_print(f"[LEARN] Nova aplicação aprendida: {application_name} ({process_name}) - Categoria: {category}")
    
    # Salvar imediatamente quando uma nova aplicação é aprendida
    # (salvamento periódico também ocorre, mas é bom salvar novas descobertas)
    try:
        save_learned_applications()
    except Exception as e:
        safe_print(f"[WARN] Erro ao salvar após aprender aplicação: {e}")

def detect_application_from_process(process_name, update_usage=True):
    """Detectar aplicação pelo nome do processo"""
    if not process_name:
        return None
    
    process_lower = process_name.lower()
    
    # 1. Busca direta na base de dados principal
    if process_lower in APPLICATION_DATABASE:
        return APPLICATION_DATABASE[process_lower]
    
    # 2. Busca no catálogo aprendido
    if process_lower in _LEARNED_APPLICATIONS:
        app_info = _LEARNED_APPLICATIONS[process_lower].copy()  # Copiar para não modificar o original diretamente
        # Atualizar contador de uso
        if update_usage:
            _LEARNED_APPLICATIONS[process_lower]['usage_count'] = \
                _LEARNED_APPLICATIONS[process_lower].get('usage_count', 0) + 1
            _LEARNED_APPLICATIONS[process_lower]['last_used'] = \
                datetime.now(pytz.timezone('America/Sao_Paulo')).isoformat()
        return app_info
    
    # 3. Busca por palavras-chave na base principal
    for app_key, app_info in APPLICATION_DATABASE.items():
        for keyword in app_info.get('keywords', []):
            if keyword.lower() in process_lower:
                return app_info
    
    # 4. Busca por palavras-chave no catálogo aprendido
    for app_key, app_info in _LEARNED_APPLICATIONS.items():
        for keyword in app_info.get('keywords', []):
            if keyword.lower() in process_lower:
                result = app_info.copy()
                # Atualizar contador de uso da aplicação encontrada por palavra-chave
                if update_usage and app_key in _LEARNED_APPLICATIONS:
                    _LEARNED_APPLICATIONS[app_key]['usage_count'] = \
                        _LEARNED_APPLICATIONS[app_key].get('usage_count', 0) + 1
                    _LEARNED_APPLICATIONS[app_key]['last_used'] = \
                        datetime.now(pytz.timezone('America/Sao_Paulo')).isoformat()
                return result
    
    return None

def detect_application_from_window(window_title):
    """Detectar aplicação pelo título da janela"""
    if not window_title:
        return None
    
    window_lower = window_title.lower()
    
    # Busca por palavras-chave no título
    for app_key, app_info in APPLICATION_DATABASE.items():
        for keyword in app_info['keywords']:
            if keyword.lower() in window_lower:
                return app_info
    
    return None

def categorize_domain(domain):
    """Categorizar domínio usando a base de dados"""
    if not domain:
        return {'category': 'desconhecido'}
    
    domain_lower = domain.lower()
    
    # Busca direta
    if domain_lower in DOMAIN_DATABASE:
        return DOMAIN_DATABASE[domain_lower]
    
    # Busca por subdomínios ou partes do domínio
    for known_domain, info in DOMAIN_DATABASE.items():
        if known_domain in domain_lower or domain_lower.endswith(known_domain):
            return info
    
    # Regras heurísticas para domínios desconhecidos
    if any(word in domain_lower for word in ['localhost', '127.0.0.1', '192.168.', '10.0.']):
        return {'category': 'desenvolvimento'}
    
    if any(word in domain_lower for word in ['github', 'gitlab', 'bitbucket']):
        return {'category': 'desenvolvimento'}
    
    if any(word in domain_lower for word in ['youtube', 'netflix', 'twitch', 'tiktok']):
        return {'category': 'entretenimento'}
    
    if any(word in domain_lower for word in ['facebook', 'instagram', 'twitter']):
        return {'category': 'social'}
    
    return {'category': 'web'}


# Função login() removida - não há mais autenticação necessária
# A API identifica o usuário pelo nome do Windows enviado no header X-User-Name


def get_logged_user():
    users = psutil.users()
    return users[0].name if users else None


def get_browser_tab_info():
    """Captura informações completas da aba ativa do navegador (URL, título, domínio)"""
    try:
        # Método 1: PowerShell com UI Automation para Chrome
        ps_script_chrome = '''
        try {
            Add-Type -AssemblyName UIAutomationClient
            $automation = [System.Windows.Automation.AutomationElement]::RootElement

            # Procurar janela ativa do Chrome
            $chromeProcesses = Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ""}
            if ($chromeProcesses) {
                $activeWindow = $automation.FindFirst([System.Windows.Automation.TreeScope]::Children, 
                    [System.Windows.Automation.AndCondition]::new(@(
                        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty, "Chrome_WidgetWin_1"),
                        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $chromeProcesses[0].Id)
                    )))

                if ($activeWindow) {
                    # Buscar barra de endereço
                    $addressBar = $activeWindow.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
                        [System.Windows.Automation.AndCondition]::new(@(
                            [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit),
                            [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::AutomationIdProperty, "L2")
                        )))

                    if ($addressBar) {
                        $url = $addressBar.GetCurrentPropertyValue([System.Windows.Automation.AutomationElement]::NameProperty)
                        if ($url -and ($url.StartsWith("http") -or $url.StartsWith("localhost"))) {
                            Write-Output $url
                        }
                    }
                }
            }
        } catch {
            # Silencioso se falhar
        }
        '''

        # Método 2: PowerShell para Edge
        ps_script_edge = '''
        try {
            Add-Type -AssemblyName UIAutomationClient
            $automation = [System.Windows.Automation.AutomationElement]::RootElement

            # Procurar janela ativa do Edge
            $edgeProcesses = Get-Process -Name "msedge" -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ""}
            if ($edgeProcesses) {
                $activeWindow = $automation.FindFirst([System.Windows.Automation.TreeScope]::Children, 
                    [System.Windows.Automation.AndCondition]::new(@(
                        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty, "Chrome_WidgetWin_1"),
                        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $edgeProcesses[0].Id)
                    )))

                if ($activeWindow) {
                    # Buscar barra de endereço do Edge
                    $addressBar = $activeWindow.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
                        [System.Windows.Automation.AndCondition]::new(@(
                            [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit),
                            [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::AutomationIdProperty, "L2")
                        )))

                    if ($addressBar) {
                        $url = $addressBar.GetCurrentPropertyValue([System.Windows.Automation.AutomationElement]::NameProperty)
                        if ($url -and ($url.StartsWith("http") -or $url.StartsWith("localhost"))) {
                            Write-Output $url
                        }
                    }
                }
            }
        } catch {
            # Silencioso se falhar
        }
        '''

        # Tentar Chrome primeiro
        if not IS_EXECUTABLE:  # Só executar quando não for executável
            try:
                result = subprocess.run(['powershell', '-Command', ps_script_chrome], 
                                     capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    url = result.stdout.strip()
                    if url.startswith('http') or url.startswith('localhost'):
                        parsed = urlparse(url)
                        return {
                            'url': url,
                            'domain': parsed.netloc if parsed.netloc else url,
                            'title': None  # Será extraído do título da janela
                        }
            except Exception:
                pass

            # Tentar Edge se Chrome falhar
            try:
                result = subprocess.run(['powershell', '-Command', ps_script_edge], 
                                     capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    url = result.stdout.strip()
                    if url.startswith('http') or url.startswith('localhost'):
                        parsed = urlparse(url)
                        return {
                            'url': url,
                            'domain': parsed.netloc if parsed.netloc else url,
                            'title': None  # Será extraído do título da janela
                        }
            except Exception:
                pass

        # Método 3: Tentar ler histórico recente do Chrome (fallback)
        try:
            import sqlite3
            import os
            from pathlib import Path
            
            # Localizar o arquivo de histórico do Chrome
            chrome_history_paths = [
                Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "History",
                Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Profile 1" / "History",
            ]
            
            for history_path in chrome_history_paths:
                if history_path.exists():
                    # Copiar o arquivo para evitar problemas de bloqueio
                    temp_history = history_path.parent / "temp_history"
                    import shutil
                    try:
                        shutil.copy2(history_path, temp_history)
                        
                        conn = sqlite3.connect(temp_history)
                        cursor = conn.cursor()
                        
                        # Buscar a URL mais recente (último minuto)
                        cursor.execute("""
                            SELECT url, title FROM urls 
                            WHERE last_visit_time > (strftime('%s', 'now') - 60) * 1000000 + 11644473600000000
                            ORDER BY last_visit_time DESC 
                            LIMIT 1
                        """)
                        
                        result = cursor.fetchone()
                        conn.close()
                        
                        # Limpar arquivo temporário
                        if temp_history.exists():
                            temp_history.unlink()
                        
                        if result:
                            url, title = result
                            if url and (url.startswith('http') or url.startswith('localhost')):
                                parsed = urlparse(url)
                                return {
                                    'url': url,
                                    'domain': parsed.netloc if parsed.netloc else url,
                                    'title': title
                                }
                        break
                    except Exception:
                        # Limpar arquivo temporário em caso de erro
                        if temp_history.exists():
                            temp_history.unlink()
                        continue
                        
        except Exception:
            pass

    except Exception as e:
        safe_print(f"[WARN] Erro ao capturar informações do navegador: {e}")

    return None


def extract_page_title_from_window(window_title):
    """Extrai o título da página (aba) do título da janela do navegador"""
    try:
        if not window_title:
            return None

        # Padrões para extrair título da página de diferentes navegadores
        browser_patterns = [
            # Chrome: "Título da Página - Google Chrome"
            r'^(.+?)\s*[-—]\s*Google\s*Chrome',
            # Edge: "Título da Página — Microsoft Edge"
            r'^(.+?)\s*[—-]\s*Microsoft\s*Edge',
            # Firefox: "Título da Página - Mozilla Firefox"
            r'^(.+?)\s*[-—]\s*Mozilla\s*Firefox',
            # Opera: "Título da Página - Opera"
            r'^(.+?)\s*[-—]\s*Opera',
            # Brave: "Título da Página - Brave"
            r'^(.+?)\s*[-—]\s*Brave',
            # Padrão genérico para navegadores
            r'^(.+?)\s*[-—]\s*(Chrome|Edge|Firefox|Opera|Brave)',
        ]

        for pattern in browser_patterns:
            match = re.search(pattern, window_title, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Validar se o título não está vazio e não é muito longo
                if title and len(title) > 0 and len(title) < 200:
                    safe_print(f"[PAGE_TITLE] Título extraído: {title}")
                    return title

        # Se não encontrou padrão de navegador, retornar o título completo se for curto
        if len(window_title) < 100 and not any(browser in window_title.lower() for browser in ['chrome', 'edge', 'firefox', 'opera', 'brave']):
            safe_print(f"[PAGE_TITLE] Usando título completo: {window_title}")
            return window_title

        safe_print(f"[PAGE_TITLE] Não foi possível extrair título de: {window_title}")
        return None

    except Exception as e:
        safe_print(f"[WARN] Erro ao extrair título da página: {e}")
        return None


def extract_domain_from_title(window_title):
    """Extrai domínio do título da janela com maior precisão e menos falsos positivos"""
    try:
        if not window_title:
            return None

        safe_print(f"[SEARCH] Tentando extrair domínio de: {window_title}")

        # Primeiro: procurar por URLs completas no título (mais específico)
        url_patterns = [
            r'https?://([a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})*(?::\d+)?)',  # URLs completas
            r'localhost:(\d+)',  # localhost com porta específica
            r'(\d+\.\d+\.\d+\.\d+):?(\d+)?',  # IPs específicos
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, window_title)
            if matches:
                if 'localhost' in pattern:
                    result = f"localhost:{matches[0]}" if matches[0] else "localhost"
                    safe_print(f"[OK] Domínio localhost encontrado: {result}")
                    return result
                elif r'\d+\.\d+\.\d+\.\d+' in pattern:
                    # Para IPs, retornar com porta se houver
                    ip, port = matches[0] if isinstance(matches[0], tuple) else (matches[0], None)
                    result = f"{ip}:{port}" if port else ip
                    safe_print(f"[OK] IP encontrado: {result}")
                    return result
                else:
                    domain = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    # Validação mais rigorosa para domínios
                    if ('.' in domain and 
                        len(domain.split('.')) >= 2 and 
                        len(domain) >= 4 and
                        not domain.startswith('.') and
                        not domain.endswith('.') and
                        ' ' not in domain):
                        safe_print(f"[OK] URL completa encontrada: {domain}")
                        return domain

        # Detecção especial para aplicações conhecidas (mais restritiva)
        app_domain_mapping = {
            'activity tracker': 'localhost:5000',
            'atividade tracker': 'localhost:5000',
            'hiprod': 'localhost:5000',
        }

        title_lower = window_title.lower()
        for app_name, domain in app_domain_mapping.items():
            if app_name in title_lower:
                safe_print(f"[OK] Aplicação conhecida detectada: {app_name} -> {domain}")
                return domain

        # Apenas domínios muito específicos e claros
        specific_patterns = [
            r'([a-zA-Z0-9-]+\.github\.io)',  # GitHub pages
            r'([a-zA-Z0-9-]+\.vercel\.app)',  # Vercel apps
            r'([a-zA-Z0-9-]+\.netlify\.app)',  # Netlify apps
            r'([a-zA-Z0-9-]+\.firebase\.app)',  # Firebase apps
        ]

        for pattern in specific_patterns:
            match = re.search(pattern, window_title.lower())
            if match:
                result = match.group(1)
                safe_print(f"[OK] Domínio específico encontrado: {result}")
                return result

        # Sites conhecidos apenas com padrões muito específicos
        known_sites = {
            'youtube.com': [r'\byoutube\.com\b'],
            'github.com': [r'\bgithub\.com\b'],
            'stackoverflow.com': [r'\bstackoverflow\.com\b'],
            'google.com': [r'\bgoogle\.com\b'],
            'gmail.com': [r'\bgmail\.com\b'],
        }

        for domain, patterns in known_sites.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    safe_print(f"[OK] Site conhecido detectado: {domain}")
                    return domain

        safe_print(f"[ERROR] Nenhum domínio válido extraído de: {window_title}")

    except Exception as e:
        safe_print(f"[WARN] Erro ao extrair domínio do título: {e}")

    return None


# Função removida - não filtrar atividades irrelevantes

def get_url_from_window_title():
    """Extrai URL/domínio do título da janela com foco em navegadores"""
    try:
        window = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(window)
        
        if not window_title:
            return None
        
        safe_print(f"[DEBUG] Analisando titulo: {window_title}")
        
        # Padrões específicos para diferentes navegadores
        browser_patterns = [
            # URLs completas no título
            r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            # Domínios no formato "Site - Navegador"
            r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[-—]\s*',
            # Localhost com porta
            r'localhost:(\d+)',
            # IPs com porta
            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)',
            # IPs sem porta
            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
            # Padrão específico do Edge: "Título — Microsoft Edge"
            r'^(.+?)\s*[—-]\s*Microsoft\s*Edge',
            # Padrão para títulos com separadores especiais
            r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            # Padrão do Chrome: "Título - Google Chrome"
            r'^(.+?)\s*[-—]\s*Google\s*Chrome',
            # Padrão do Firefox: "Título - Mozilla Firefox"
            r'^(.+?)\s*[-—]\s*Mozilla\s*Firefox'
        ]
        
        for i, pattern in enumerate(browser_patterns):
            matches = re.findall(pattern, window_title, re.IGNORECASE)
            if matches:
                if 'localhost' in pattern:
                    domain = f"localhost:{matches[0]}" if matches[0] else "localhost"
                elif r'\d{1,3}' in pattern:  # IP patterns
                    if isinstance(matches[0], tuple):
                        ip, port = matches[0]
                        domain = f"{ip}:{port}" if port else ip
                    else:
                        domain = matches[0]
                else:
                    # Para padrões de título de navegador
                    candidate = matches[0].strip()
                    
                    # Se o candidato parece ser um domínio
                    if ('.' in candidate and 
                        len(candidate.split('.')) >= 2 and 
                        not candidate.startswith('.') and
                        not candidate.endswith('.') and
                        len(candidate) < 100):  # Não muito longo
                        
                        # Verificar se não é apenas o nome da aplicação
                        if not any(app in candidate.lower() for app in ['activity tracker', 'pessoal', 'trabalho']):
                            domain = candidate
                        else:
                            continue
                    else:
                        continue
                
                if domain:
                    safe_print(f"[DOMAIN] Padrao {i+1} encontrou: {domain}")
                    return domain
        
        # Tratamento específico para aplicações locais conhecidas
        local_app_patterns = {
            'activity tracker': 'localhost:5005',
            'hiprod': 'localhost:5005',
            'atividade tracker': 'localhost:5005',
            'dashboard': 'localhost:5005'
        }
        
        title_lower = window_title.lower()
        for app_name, domain in local_app_patterns.items():
            if app_name in title_lower:
                safe_print(f"[DOMAIN] Aplicacao local detectada: {app_name} -> {domain}")
                return domain
        
        # Fallback: procurar domínios conhecidos no título
        known_domains = [
            'github.com', 'google.com', 'youtube.com', 'facebook.com', 'instagram.com',
            'linkedin.com', 'twitter.com', 'stackoverflow.com', 'medium.com',
            'gmail.com', 'outlook.com', 'teams.microsoft.com', 'office.com',
            'localhost', '127.0.0.1'
        ]
        
        for domain in known_domains:
            if domain in title_lower:
                safe_print(f"[DOMAIN] Dominio conhecido encontrado: {domain}")
                return domain
        
        safe_print(f"[DEBUG] Nenhum dominio encontrado em: {window_title}")
        return None
        
    except Exception as e:
        safe_print(f"[ERROR] Erro ao extrair URL: {e}")
        return None

def get_active_window_info():
    """Captura informações completas da janela ativa: URL, nome da página, domínio"""
    try:
        window = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(window)

        # Obter processo PRIMEIRO para identificação mais precisa
        try:
            import win32process
            _, process_id = win32process.GetWindowThreadProcessId(window)
            process = psutil.Process(process_id)
            process_name = process.name().lower()
            
            # PRIORIZAR DETECÇÃO POR PROCESSO
            app_info = detect_application_from_process(process_name)
            
            if app_info:
                # Usar nome da base de dados (mais preciso)
                application = app_info['name']
                
                # CAPTURA COMPLETA DE INFORMAÇÕES PARA NAVEGADORES
                if app_info['category'] == 'navegador':
                    # Tentar capturar informações completas do navegador
                    browser_info = get_browser_tab_info()
                    
                    if browser_info:
                        # Usar informações capturadas do navegador
                        url = browser_info.get('url')
                        domain = browser_info.get('domain')
                        page_title = browser_info.get('title')
                        
                        # Se não conseguiu o título do histórico, extrair do título da janela
                        if not page_title:
                            page_title = extract_page_title_from_window(window_title)
                        
                        safe_print(f"[BROWSER] {application}: URL={url}, Domain={domain}, Title={page_title}")
                        
                        return {
                            'window_title': window_title,
                            'url': url,
                            'page_title': page_title,
                            'domain': domain,
                            'application': application
                        }
                    else:
                        # Fallback: extrair do título da janela
                        domain = extract_domain_from_title(window_title)
                        page_title = extract_page_title_from_window(window_title)
                        
                        safe_print(f"[BROWSER_FALLBACK] {application}: Domain={domain}, Title={page_title}")
                        
                        return {
                            'window_title': window_title,
                            'url': None,
                            'page_title': page_title,
                            'domain': domain,
                            'application': application
                        }
                else:
                    # Aplicações não-navegador
                    safe_print(f"[APP] {app_info['category']}: {application}")
                    return {
                        'window_title': window_title,
                        'url': None,
                        'page_title': None,
                        'domain': None,
                        'application': application
                    }
            else:
                # Processo não encontrado na base de dados - APRENDER automaticamente
                try:
                    import win32process
                    window = win32gui.GetForegroundWindow()
                    _, process_id = win32process.GetWindowThreadProcessId(window)
                    process = psutil.Process(process_id)
                    process_name = process.name()
                    process_name_lower = process_name.lower()
                    
                    # Aprender a aplicação se ainda não foi aprendida
                    if process_name_lower not in _LEARNED_APPLICATIONS:
                        learn_application(process_name, window_title)
                    
                    # Buscar novamente (agora deve encontrar no catálogo aprendido)
                    # A função detect_application_from_process já atualiza o contador de uso automaticamente
                    app_info = detect_application_from_process(process_name)
                    if app_info:
                        application = app_info['name']
                    else:
                        # Usar nome do processo como aplicação (sem .exe)
                        application = process_name.replace('.exe', '').replace('.EXE', '')
                    
                    safe_print(f"[APP] Processo aprendido/em uso: {application} ({process_name})")
                except Exception as e:
                    # Fallback: usar detecção por título
                    application = get_application_name(window_title)
                    safe_print(f"[APP] Fallback: {application} - Erro: {e}")
                
                return {
                    'window_title': window_title,
                    'url': None,
                    'page_title': None,
                    'domain': None,
                    'application': application
                }
                
        except Exception as e:
            # Fallback se não conseguir obter processo
            safe_print(f"[WARN] Erro ao obter processo: {e}")
            application = get_application_name(window_title)
            
            # Se ainda for "Sistema Local", tentar extrair do título da janela
            if application == 'Sistema Local' and window_title:
                # Tentar identificar pelo título
                title_lower = window_title.lower()
                if 'explorer' in title_lower or 'arquivo' in title_lower:
                    application = 'Windows Explorer'
                elif 'calculadora' in title_lower or 'calculator' in title_lower:
                    application = 'Calculadora'
                elif 'notepad' in title_lower or 'bloco de notas' in title_lower:
                    application = 'Notepad'
                elif 'paint' in title_lower:
                    application = 'Paint'
                elif 'cmd' in title_lower or 'prompt' in title_lower:
                    application = 'Prompt de Comando'
                elif 'powershell' in title_lower:
                    application = 'PowerShell'
                else:
                    # Usar parte do título como nome da aplicação
                    application = window_title[:50] if len(window_title) > 50 else window_title
                    safe_print(f"[APP] Usando título como aplicação: {application}")
            
            return {
                'window_title': window_title,
                'url': None,
                'page_title': None,
                'domain': None,
                'application': application
            }

    except Exception as e:
        safe_print(f"[ERROR] Erro ao capturar informacoes da janela: {e}")
        return {
            'window_title': 'Erro ao capturar janela',
            'url': None,
            'page_title': None,
            'domain': None,
            'application': 'Sistema Local'
        }


def get_application_name(window_title):
    """Identifica a aplicação baseada no título da janela e processo"""
    try:
        # Obter o processo da janela ativa
        import win32process
        window = win32gui.GetForegroundWindow()
        _, process_id = win32process.GetWindowThreadProcessId(window)

        try:
            process = psutil.Process(process_id)
            process_name = process.name().lower()

            # Mapear nomes de processo para aplicações
            process_mapping = {
                'chrome.exe': 'Google Chrome',
                'firefox.exe': 'Firefox',
                'msedge.exe': 'Microsoft Edge',
                'code.exe': 'VS Code',
                'notepad.exe': 'Notepad',
                'excel.exe': 'Microsoft Excel',
                'winword.exe': 'Microsoft Word',
                'powerpnt.exe': 'PowerPoint',
                'outlook.exe': 'Outlook',
                'teams.exe': 'Microsoft Teams',
                'slack.exe': 'Slack',
                'discord.exe': 'Discord',
                'whatsapp.exe': 'WhatsApp',
                'telegram.exe': 'Telegram',
                'explorer.exe': 'Windows Explorer',
                'notepad++.exe': 'Notepad++',
                'sublime_text.exe': 'Sublime Text',
                'atom.exe': 'Atom'
            }

            if process_name in process_mapping:
                return process_mapping[process_name]

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    except ImportError:
        pass  # win32process não disponível
    except Exception:
        pass

    # Fallback: usar título da janela
    title_lower = window_title.lower()

    app_patterns = {
        'Google Chrome': ['chrome', 'google chrome'],
        'Firefox': ['firefox', 'mozilla firefox'],
        'Microsoft Edge': ['edge', 'microsoft edge'],
        'VS Code': ['visual studio code', 'vscode'],
        'Notepad': ['notepad', 'bloco de notas'],
        'Microsoft Excel': ['excel', 'microsoft excel'],
        'Microsoft Word': ['word', 'microsoft word'],
        'PowerPoint': ['powerpoint', 'microsoft powerpoint'],
        'Outlook': ['outlook', 'microsoft outlook'],
        'Microsoft Teams': ['teams', 'microsoft teams'],
        'Slack': ['slack'],
        'Discord': ['discord'],
        'WhatsApp': ['whatsapp'],
        'Telegram': ['telegram'],
        # Sistemas locais
        'Windows Explorer': ['explorer', 'arquivo', 'file explorer', 'pasta'],
        'Calculadora': ['calculadora', 'calculator'],
        'Paint': ['paint'],
        'Prompt de Comando': ['cmd', 'command prompt', 'prompt de comando'],
        'PowerShell': ['powershell'],
        'Gerenciador de Tarefas': ['task manager', 'gerenciador de tarefas'],
        'Painel de Controle': ['control panel', 'painel de controle'],
        'Ferramenta de Captura': ['snipping tool', 'captura'],
    }

    for app, patterns in app_patterns.items():
        for pattern in patterns:
            if pattern in title_lower:
                return app

    # Se não encontrou padrão conhecido, usar o título da janela como nome da aplicação
    # Isso garante que sistemas locais sejam registrados mesmo sem estar na base
    if window_title and len(window_title.strip()) > 0:
        # Limitar tamanho e remover caracteres problemáticos
        app_name = window_title[:60].strip()
        safe_print(f"[APP] Aplicação não catalogada, usando título: {app_name}")
        return app_name
    
    return 'Sistema Local'


def get_usuario_monitorado_id(usuario_nome):
    """Busca ou cria usuário monitorado pelo nome"""
    try:
        # Validar nome do usuário
        if not usuario_nome or not usuario_nome.strip():
            safe_print("[ERROR] Nome do usuário não fornecido ou vazio")
            return None
        
        usuario_nome = usuario_nome.strip()
        safe_print(f"[INFO] Buscando/criando usuário monitorado: {usuario_nome}")
        
        # Realizar handshake TLS se for HTTPS
        if API_BASE_URL.startswith('https://'):
            if not perform_tls_handshake(API_BASE_URL):
                safe_print("[ERROR] Falha no handshake TLS - não foi possível estabelecer conexão segura")
                return None
        
        session = get_secure_session()
        headers = get_headers(usuario_nome)
        safe_print(f"[INFO] URL: {USUARIOS_MONITORADOS_URL}")
        safe_print(f"[INFO] Params: nome={usuario_nome}")
        safe_print(f"[INFO] Headers: X-User-Name={headers.get('X-User-Name', 'N/A')}")
        
        resp = session.get(USUARIOS_MONITORADOS_URL,
                            params={'nome': usuario_nome},
                            headers=headers)
        
        # Sempre mostrar informações da resposta em caso de erro
        safe_print(f"[INFO] Status code: {resp.status_code}")
        safe_print(f"[INFO] Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        safe_print(f"[INFO] Response length: {len(resp.text)} bytes")
        
        if resp.status_code == 200:
            # Verificar se a resposta não está vazia
            if not resp.text or not resp.text.strip():
                safe_print("[ERROR] Resposta da API está vazia")
                return None
            
            # Verificar content-type
            content_type = resp.headers.get('Content-Type', '').lower()
            if 'application/json' not in content_type and 'text/json' not in content_type:
                safe_print(f"[WARN] Content-Type inesperado: {content_type}")
                safe_print(f"[DEBUG] Primeiros 200 caracteres da resposta: {resp.text[:200]}")
            
            # Tentar fazer parse do JSON
            try:
                # Tentar fazer parse direto
                data = resp.json()
            except ValueError as json_error:
                # Se falhar, tentar limpar a resposta e fazer parse novamente
                try:
                    # Remover espaços em branco no início e fim
                    cleaned_text = resp.text.strip()
                    # Tentar fazer parse manualmente
                    import json
                    data = json.loads(cleaned_text)
                except (ValueError, json.JSONDecodeError) as json_error2:
                    safe_print(f"[ERROR] Erro ao fazer parse do JSON: {json_error}")
                    safe_print(f"[ERROR] Erro ao fazer parse após limpeza: {json_error2}")
                    safe_print(f"[ERROR] Status: {resp.status_code}")
                    safe_print(f"[ERROR] Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
                    safe_print(f"[ERROR] Resposta completa ({len(resp.text)} chars):")
                    safe_print(f"[ERROR] {resp.text}")
                    return None
            
            user_id = data.get('id')
            was_created = data.get('created', False)
            if was_created:
                safe_print(f"[OK] Novo usuário monitorado criado: {usuario_nome} (ID: {user_id})")
            else:
                safe_print(f"[OK] Usuário monitorado encontrado: {usuario_nome} (ID: {user_id})")
            return user_id
        elif resp.status_code == 401:
            safe_print("[ERROR] Erro de autenticação na API. Verifique a configuração.")
            safe_print(f"[ERROR] Resposta: {resp.text}")
            safe_print(f"[ERROR] Headers enviados: X-User-Name={usuario_nome}")
            return None
        elif resp.status_code == 500:
            safe_print("[ERROR] Erro interno do servidor (500). Verifique os logs do backend.")
            safe_print(f"[ERROR] Resposta completa: {resp.text}")
            return None
        else:
            safe_print(f"[ERROR] Erro ao buscar usuário monitorado: Status {resp.status_code}")
            safe_print(f"[ERROR] Resposta completa: {resp.text}")
            return None
    except requests.exceptions.RequestException as e:
        safe_print(f"[ERROR] Erro de conexão ao consultar usuário monitorado: {e}")
        if not IS_EXECUTABLE:
            import traceback
            traceback.print_exc()
        return None
    except Exception as e:
        safe_print(f"[ERROR] Erro ao consultar usuário monitorado: {e}")
        import traceback
        if not IS_EXECUTABLE:
            traceback.print_exc()
        return None


def verificar_usuario_ativo(usuario_id, usuario_nome=None):
    """Verifica se o usuário monitorado ainda existe e está ativo"""
    try:
        # Se não tiver nome, tentar obter do sistema
        if not usuario_nome:
            usuario_nome = get_logged_user()
        session = get_secure_session()
        resp = session.get(USUARIOS_MONITORADOS_URL,
                            headers=get_headers(usuario_nome))
        if resp.status_code == 200:
            usuarios = resp.json()
            for usuario in usuarios:
                if usuario.get('id') == usuario_id and usuario.get('ativo', True):
                    return True
            return False
        return False
    except Exception as e:
        safe_print(f"[ERROR] Erro ao verificar usuário ativo: {e}")
        return False


def obter_configuracoes_horario_usuario(usuario_nome):
    """Obtém as configurações de horário de trabalho do usuário"""
    try:
        session = get_secure_session()
        resp = session.get(USUARIOS_MONITORADOS_URL,
                            params={'nome': usuario_nome},
                            headers=get_headers(usuario_nome))
        if resp.status_code == 200:
            data = resp.json()
            return {
                'horario_inicio_trabalho': data.get('horario_inicio_trabalho', '08:00:00'),
                'horario_fim_trabalho': data.get('horario_fim_trabalho', '18:00:00'),
                'dias_trabalho': data.get('dias_trabalho', '1,2,3,4,5'),
                'monitoramento_ativo': data.get('monitoramento_ativo', True)
            }
        else:
            safe_print(f"[ERROR] Erro ao buscar configurações do usuário: {resp.status_code}")
            return None
    except Exception as e:
        safe_print(f"[ERROR] Erro ao consultar configurações do usuário: {e}")
        return None


def esta_em_horario_trabalho(usuario_nome, tz):
    """Verifica se o horário atual está dentro do horário de trabalho do usuário"""
    try:
        config = obter_configuracoes_horario_usuario(usuario_nome)
        if not config:
            safe_print("[WARN] Configurações não encontradas, usando horário padrão (8-18h, seg-sex)")
            config = {
                'horario_inicio_trabalho': '08:00:00',
                'horario_fim_trabalho': '18:00:00',
                'dias_trabalho': '1,2,3,4,5',
                'monitoramento_ativo': True
            }

        # Se o monitoramento não está ativo, não enviar atividades
        if not config.get('monitoramento_ativo', True):
            safe_print(f"⏸️ Monitoramento desativado para o usuário {usuario_nome}")
            return False

        agora = datetime.now(tz)

        # Verificar se é um dia de trabalho (1=Segunda, 7=Domingo)
        dia_semana = agora.isoweekday()
        dias_trabalho = [int(d) for d in config['dias_trabalho'].split(',')]

        if dia_semana not in dias_trabalho:
            safe_print(f"⏰ Fora dos dias de trabalho: hoje é {dia_semana}, dias de trabalho: {dias_trabalho}")
            return False

        # Verificar se está no horário de trabalho
        horario_inicio = dt_time.fromisoformat(config['horario_inicio_trabalho'])
        horario_fim = dt_time.fromisoformat(config['horario_fim_trabalho'])
        hora_atual = agora.time()

        if horario_inicio <= hora_atual <= horario_fim:
            safe_print(f"[OK] Dentro do horário de trabalho: {hora_atual} ({horario_inicio}-{horario_fim})")
            return True
        else:
            safe_print(f"⏰ Fora do horário de trabalho: {hora_atual} ({horario_inicio}-{horario_fim})")
            return False

    except Exception as e:
        safe_print(f"[ERROR] Erro ao verificar horário de trabalho: {e}")
        # Em caso de erro, permitir o envio para não quebrar o funcionamento
        return True


def enviar_atividade(registro):
    # Verificar se agente deve parar antes de enviar
    if check_stop_flag():
        safe_print("[AGENT] Agente deve parar - não enviando atividade")
        return False
    
    # Verificar se agente está em pausa (intervalo)
    if check_pause_flag():
        safe_print("[AGENT] Agente em pausa (intervalo) - não enviando atividade")
        return False
    
    try:
        # Obter nome do usuário do registro ou do sistema
        usuario_nome = registro.get('usuario_nome') or get_logged_user()
        
        # Realizar handshake TLS se for HTTPS (apenas na primeira requisição)
        if API_BASE_URL.startswith('https://') and not hasattr(enviar_atividade, '_tls_handshake_done'):
            if perform_tls_handshake(API_BASE_URL):
                enviar_atividade._tls_handshake_done = True
            else:
                safe_print("[ERROR] Falha no handshake TLS - não foi possível estabelecer conexão segura")
                _save_offline(registro)
                return False
        
        session = get_secure_session()
        resp = session.post(ATIVIDADE_URL,
                             json=registro,
                             headers=get_headers(usuario_nome))
        if resp.status_code == 201:
            domain_info = f" | Domínio: {registro.get('domain', 'N/A')}" if registro.get('domain') else ""
            page_info = f" | Página: {registro.get('page_title', 'N/A')}" if registro.get('page_title') else ""
            url_info = f" | URL: {registro.get('url', 'N/A')}" if registro.get('url') else ""
            safe_print(f"[OK] Atividade enviada: {registro['active_window']}{domain_info}{page_info}{url_info}")
        elif resp.status_code == 401:
            safe_print("[ERROR] Erro de autenticação na API. Verifique a configuração.")
            _save_offline(registro)
            return False
        elif resp.status_code == 404 and "Usuário monitorado não encontrado" in resp.text:
            safe_print(f"[ERROR] Usuário monitorado ID {registro['usuario_monitorado_id']} não encontrado!")
            safe_print("[INFO] Tentando recriar usuário monitorado...")
            # Tentar obter o nome do usuário atual e recriar
            try:
                current_usuario_nome = get_logged_user()
                if current_usuario_nome:
                    new_user_id = get_usuario_monitorado_id(current_usuario_nome)
                    if new_user_id and new_user_id != 0:
                        safe_print(f"[OK] Usuário monitorado recriado com ID: {new_user_id}")
                        # Atualizar o registro com o novo ID e tentar enviar novamente
                        registro['usuario_monitorado_id'] = new_user_id
                        return enviar_atividade(registro)
                    else:
                        safe_print("[ERROR] Não foi possível recriar usuário monitorado")
                        _save_offline(registro)
                        return False
                else:
                    safe_print("[ERROR] Não foi possível obter nome do usuário atual")
                    _save_offline(registro)
                    return False
            except Exception as e:
                safe_print(f"[ERROR] Erro ao tentar recriar usuário: {e}")
                _save_offline(registro)
                return False
        else:
            safe_print(f"[ERROR] Erro ao enviar atividade: {resp.status_code} {resp.text}")
            _save_offline(registro)
            return False
    except Exception as e:
        safe_print(f"[ERROR] Erro ao enviar atividade: {e}")
        _save_offline(registro)
        return False
    return True

def enviar_face_presence_check(usuario_monitorado_id, face_detected, presence_time):
    """
    Envia um ponto de verificação facial para a API.
    Chamado a cada 1 minuto quando há verificação facial.
    
    Args:
        usuario_monitorado_id: ID do usuário monitorado
        face_detected: bool - Se uma face foi detectada
        presence_time: int - Tempo total de presença acumulado em segundos
    
    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    if check_stop_flag():
        return False
    
    # Validar ID antes de enviar
    if not usuario_monitorado_id or usuario_monitorado_id == 0:
        if not IS_EXECUTABLE:
            safe_print(f"[FACE-CHECK] ⚠ ID de usuário inválido ({usuario_monitorado_id}), não enviando verificação")
        return False
    
    try:
        check_data = {
            'usuario_monitorado_id': usuario_monitorado_id,
            'face_detected': face_detected,
            'presence_time': int(presence_time)
        }
        
        # Obter nome do usuário do sistema
        usuario_nome = get_logged_user()
        
        face_check_url = f"{API_BASE_URL}/api/face-presence-check"
        session = get_secure_session()
        resp = session.post(face_check_url,
                             json=check_data,
                             headers=get_headers(usuario_nome),
                             timeout=10)
        
        if resp.status_code == 201:
            if not IS_EXECUTABLE:
                status = "✓ Detectado" if face_detected else "✗ Ausente"
                safe_print(f"[FACE-CHECK] {status} | Usuário ID: {usuario_monitorado_id} | Tempo: {presence_time/60:.1f}min | ✅ Enviado")
            return True
        elif resp.status_code == 401:
            safe_print("[ERROR] Erro de autenticação na API ao enviar verificação facial.")
            return False
        elif resp.status_code == 404:
            if not IS_EXECUTABLE:
                error_msg = resp.text if hasattr(resp, 'text') else 'N/A'
                safe_print(f"[FACE-CHECK] ⚠ Usuário monitorado ID {usuario_monitorado_id} não encontrado: {error_msg}")
            return False
        else:
            if not IS_EXECUTABLE:
                error_msg = resp.text if hasattr(resp, 'text') else 'N/A'
                safe_print(f"[FACE-CHECK] ❌ Erro {resp.status_code} ao enviar verificação facial: {error_msg}")
            return False
    except Exception as e:
        if not IS_EXECUTABLE:
            safe_print(f"[FACE-CHECK] ❌ Exceção ao enviar verificação facial: {e}")
        return False


# =========================
#  Fila Offline Persistente
# =========================
_OFFLINE_QUEUE_FILE = os.path.join(os.path.dirname(__file__), 'offline_queue.jsonl')

# =========================
#  Banco de Dados de Aplicações Aprendidas (por usuário)
# =========================
def get_learned_apps_file():
    """Retorna o caminho do arquivo de aplicações aprendidas"""
    if IS_EXECUTABLE:
        # Quando executável, salvar no mesmo diretório do executável
        base_dir = os.path.dirname(sys.executable)
    else:
        # Quando script Python, salvar no diretório do script
        base_dir = os.path.dirname(__file__)
    return os.path.join(base_dir, 'learned_applications.json')

_LEARNED_APPS_FILE = get_learned_apps_file()
_LEARNED_APPLICATIONS = {}  # Cache em memória: {process_name: {info}}

def _save_offline(registro: dict) -> None:
    try:
        # Garante campo de criação
        if 'created_at' not in registro:
            registro['created_at'] = datetime.now(pytz.timezone('America/Sao_Paulo')).isoformat()
        with open(_OFFLINE_QUEUE_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        safe_print("🗂️ Atividade salva offline (fila)")
    except Exception as e:
        safe_print(f"[ERROR] Falha ao salvar offline: {e}")

def _flush_offline_queue(max_items: int = 200) -> None:
    try:
        if not os.path.exists(_OFFLINE_QUEUE_FILE):
            return
        # Ler todos
        with open(_OFFLINE_QUEUE_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if not lines:
            return
        safe_print(f"🔁 Tentando reenviar {len(lines)} atividades offline...")
        remaining = []
        sent = 0
        for idx, line in enumerate(lines):
            if idx >= max_items:
                remaining.extend(lines[idx:])
                break
            try:
                data = json.loads(line)
            except Exception:
                # linha corrompida, descartar
                continue
            ok = enviar_atividade(data)
            if ok:
                sent += 1
            else:
                remaining.append(line)
        # Reescrever arquivo com os não enviados
        if remaining:
            with open(_OFFLINE_QUEUE_FILE, 'w', encoding='utf-8') as f:
                f.writelines(remaining)
        else:
            # Remove arquivo se vazio
            try:
                os.remove(_OFFLINE_QUEUE_FILE)
            except OSError:
                pass
        safe_print(f"[OK] Reenvio offline concluído: enviados {sent}, pendentes {len(remaining)}")
    except Exception as e:
        safe_print(f"[ERROR] Erro no flush da fila offline: {e}")


def main():
    # Carregar aplicações aprendidas na inicialização
    load_learned_applications()
    
    # Mostrar configurações carregadas
    usuario_windows = get_logged_user()
    safe_print(f"[CONFIG] API_URL: {API_BASE_URL}")
    safe_print(f"[CONFIG] Usuário Windows: {usuario_windows if usuario_windows else 'NÃO IDENTIFICADO'}")
    safe_print(f"[CONFIG] MONITOR_INTERVAL: {MONITOR_INTERVAL}s")
    safe_print(f"[CONFIG] IDLE_THRESHOLD: {IDLE_THRESHOLD}s")
    safe_print(f"[CONFIG] Aplicações aprendidas: {len(_LEARNED_APPLICATIONS)}")
    
    # Mostrar configurações TLS/SSL
    if API_BASE_URL.startswith('https://'):
        safe_print(f"[CONFIG] TLS/SSL: Habilitado")
        safe_print(f"[CONFIG] SSL_VERIFY: {SSL_VERIFY}")
        if SSL_CERT_PATH:
            safe_print(f"[CONFIG] SSL_CERT_PATH: {SSL_CERT_PATH}")
        
        # Realizar handshake TLS inicial para verificar conectividade
        safe_print("[TLS] Verificando conectividade TLS com o servidor...")
        if perform_tls_handshake(API_BASE_URL):
            safe_print("[TLS] ✅ Servidor TLS acessível e certificado válido")
        else:
            safe_print("[TLS] ⚠️ Aviso: Não foi possível verificar TLS (requisições podem falhar)")
    else:
        safe_print(f"[CONFIG] TLS/SSL: Desabilitado (HTTP)")
        safe_print(f"[CONFIG] ⚠️ AVISO: Comunicação não criptografada")
    
    # Não há mais autenticação necessária - a API identifica pelo nome do usuário

    last_usuario_nome = get_logged_user()
    usuario_monitorado_id = get_usuario_monitorado_id(last_usuario_nome)

    # Contador para verificação periódica do usuário
    verificacao_contador = 0
    
    # Contador para verificação de presença facial (a cada 1 minuto = 6 ciclos de 10 segundos)
    face_check_contador = 0
    FACE_CHECK_INTERVAL = 6  # 6 ciclos * 10 segundos = 60 segundos = 1 minuto
    
    # Obter o tracker de presença facial
    presence_tracker = None
    if FACE_DETECTION_AVAILABLE:
        try:
            presence_tracker = get_presence_tracker()
        except:
            presence_tracker = None

    last_window_info = {"window_title": "", "url": None, "page_title": None, "domain": None, "application": ""}
    ociosidade = 0
    registros = []

    tz = pytz.timezone('America/Sao_Paulo')  # Brasília timezone

    safe_print("[START] Agente iniciado com captura completa de informações!")
    safe_print("[INFO] Funcionalidades disponíveis:")
    safe_print("   - Captura de URL completa da página")
    safe_print("   - Captura do nome da página (título da aba)")
    safe_print("   - Captura do domínio de uso")
    safe_print("   - Detecção por processo")
    safe_print("   - Base de dados expandida")
    safe_print("   - Categorização automática")
    if FACE_DETECTION_AVAILABLE:
        safe_print("   - Verificação de presença facial (face check em frente à tela)")
        safe_print("   - Rastreamento de tempo de presença em frente ao PC")
    else:
        safe_print("   - ⚠ Verificação facial desabilitada (módulo não disponível)")

    # Limpar flag de parada antiga ao iniciar (pode ter ficado de execução anterior)
    try:
        flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.agent_stop_flag')
        if os.path.exists(flag_file):
            os.remove(flag_file)
            safe_print("[AGENT] Flag de parada antiga removida - agente iniciando normalmente")
    except:
        pass
    
    # Resetar variável global de parada
    global AGENT_SHOULD_STOP
    AGENT_SHOULD_STOP = False

    while True:
        # Verificar flag de parada
        if check_stop_flag():
            safe_print("[AGENT] Flag de parada detectada! Parando agente...")
            safe_print("[AGENT] Agente encerrado com sucesso.")
            return  # Encerrar o agente
        
        # Verificar flag de pausa (intervalo)
        if check_pause_flag():
            # Agente está em pausa - aguardar sem capturar atividades
            if not IS_EXECUTABLE:
                safe_print("[AGENT] ⏸ Agente em pausa (intervalo) - aguardando retomada...")
            time.sleep(MONITOR_INTERVAL)
            continue  # Pular este ciclo e não capturar atividades
        
        current_window_info = get_active_window_info()
        current_usuario_nome = get_logged_user()

        # Detectar mudança de usuário
        if current_usuario_nome != last_usuario_nome:
            safe_print(f"[USER] Mudanca de usuario: {last_usuario_nome} -> {current_usuario_nome}")
            
            # Resetar tracker de presença ao trocar de usuário
            if presence_tracker is not None:
                try:
                    final_time = reset_presence_tracker()
                    safe_print(f"[FACE] Tempo de presença do usuário anterior: {final_time:.0f} segundos ({final_time/60:.1f} minutos)")
                except:
                    pass
            
            last_usuario_nome = current_usuario_nome
            usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            verificacao_contador = 0  # Reset contador
            face_check_contador = 0  # Reset contador de face também

            # Se não conseguiu obter o ID do usuário, pular este ciclo
            if not usuario_monitorado_id or usuario_monitorado_id == 0:
                safe_print(f"[WARN] Não foi possível obter ID válido para usuário {current_usuario_nome}, aguardando próximo ciclo...")
                time.sleep(10)
                continue

        # Verificar se temos um ID válido antes de continuar
        if not usuario_monitorado_id or usuario_monitorado_id == 0:
            safe_print(f"[WARN] ID de usuário inválido ({usuario_monitorado_id}), tentando reobter...")
            usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            if not usuario_monitorado_id or usuario_monitorado_id == 0:
                safe_print("[ERROR] Falha ao obter ID válido, aguardando 30 segundos...")
                time.sleep(30)
                continue

        # Verificar periodicamente se o usuário ainda existe (a cada 10 ciclos = ~100 segundos)
        verificacao_contador += 1
        if verificacao_contador >= 10:
            safe_print(f"[SEARCH] Verificando se usuário {usuario_monitorado_id} ainda existe...")
            if not verificar_usuario_ativo(usuario_monitorado_id):
                safe_print(f"[WARN] Usuário {usuario_monitorado_id} não encontrado, recriando...")
                usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            verificacao_contador = 0
        
        # Verificar presença facial a cada 1 minuto (apenas se não estiver em pausa)
        if FACE_DETECTION_AVAILABLE and presence_tracker is not None and not check_pause_flag():
            face_check_contador += 1
            if face_check_contador >= FACE_CHECK_INTERVAL:
                try:
                    # Usar versão silenciosa quando executável
                    if IS_EXECUTABLE:
                        face_detected = check_face_presence_silent(timeout=3)
                    else:
                        face_detected = check_face_presence(timeout=3)
                    
                    # Atualizar tracker de presença
                    check_time = time.time()
                    presence_info = presence_tracker.update_presence(face_detected, check_time)
                    
                    # Obter tempo total de presença
                    total_presence_time = presence_info['total_presence_time']
                    
                    if not IS_EXECUTABLE:
                        if face_detected:
                            total_min = total_presence_time / 60
                            safe_print(f"[FACE] ✓ Presença detectada | Tempo total: {total_min:.1f} min")
                        else:
                            total_min = total_presence_time / 60
                            safe_print(f"[FACE] ⚠ Ausente | Tempo acumulado: {total_min:.1f} min")
                    
                    # Enviar ponto de verificação para a API
                    # Verificar se temos um ID válido antes de enviar
                    if usuario_monitorado_id is None or usuario_monitorado_id == 0:
                        # Tentar obter o ID novamente
                        safe_print(f"[FACE-CHECK] Tentando obter ID do usuário {current_usuario_nome}...")
                        usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
                    
                    if usuario_monitorado_id is not None and usuario_monitorado_id != 0:
                        # Verificar se não está em pausa antes de enviar verificação facial
                        if not check_pause_flag():
                            enviar_face_presence_check(
                                usuario_monitorado_id=usuario_monitorado_id,
                                face_detected=face_detected,
                                presence_time=total_presence_time
                            )
                        else:
                            if not IS_EXECUTABLE:
                                safe_print("[FACE-CHECK] ⏸ Agente em pausa - não enviando verificação facial")
                    else:
                        if not IS_EXECUTABLE:
                            safe_print(f"[FACE-CHECK] ⚠ Não foi possível enviar verificação: usuário {current_usuario_nome} não encontrado ou ID inválido")
                    
                except Exception as e:
                    if not IS_EXECUTABLE:
                        safe_print(f"[FACE] Erro ao verificar presença facial: {e}")
                
                face_check_contador = 0

        # Verificar mudança significativa de janela/URL/página/domínio/aplicação
        window_changed = (
            current_window_info['window_title'] != last_window_info['window_title'] or 
            current_window_info['url'] != last_window_info['url'] or
            current_window_info['page_title'] != last_window_info['page_title'] or
            current_window_info['domain'] != last_window_info['domain'] or
            current_window_info['application'] != last_window_info['application']
        )

        if window_changed:
            # Log da mudança para debug
            if current_window_info['window_title'] != last_window_info['window_title']:
                safe_print(f"[INFO] Mudança de janela: {last_window_info['window_title'][:50]}... -> {current_window_info['window_title'][:50]}...")
            if current_window_info['url'] != last_window_info['url']:
                safe_print(f"[URL] Mudança de URL: {last_window_info['url']} -> {current_window_info['url']}")
            if current_window_info['page_title'] != last_window_info['page_title']:
                safe_print(f"[PAGE] Mudança de página: {last_window_info['page_title']} -> {current_window_info['page_title']}")
            if current_window_info['domain'] != last_window_info['domain']:
                safe_print(f"[DOMAIN] Mudança de domínio: {last_window_info['domain']} -> {current_window_info['domain']}")
            if current_window_info['application'] != last_window_info['application']:
                safe_print(f"[APP] Mudança de aplicação: {last_window_info['application']} -> {current_window_info['application']}")

            ociosidade = 0
            last_window_info = current_window_info
        else:
            ociosidade += 10

        if ociosidade % 10 == 0:
            # Enviar todas as atividades (sem filtro)
            # IMPORTANTE: Sistemas locais são sempre registrados, mesmo quando não identificados
            # na base de dados. O nome do processo ou título da janela será usado como aplicação.
            
            # Verificar se temos um ID válido antes de criar o registro
            if usuario_monitorado_id is None:
                safe_print("[WARN] ID do usuário monitorado é None, tentando recriar...")
                usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)

            if usuario_monitorado_id is not None:
                # Obter tempo de presença facial se disponível
                face_presence_time = None
                if presence_tracker is not None:
                    try:
                        face_presence_time = presence_tracker.get_presence_time()
                    except:
                        pass
                
                registro = {
                    'usuario_monitorado_id': usuario_monitorado_id,
                    'ociosidade': ociosidade,
                    'active_window': current_window_info['window_title'],
                    'url': current_window_info['url'],
                    'page_title': current_window_info['page_title'],
                    'domain': current_window_info['domain'],
                    'application': current_window_info['application'],
                    'horario': datetime.now(tz).isoformat()
                }
                
                # Adicionar tempo de presença facial se disponível
                if face_presence_time is not None:
                    registro['face_presence_time'] = int(face_presence_time)  # Tempo em segundos
                
                registros.append(registro)
                presence_info = f" | Presença: {face_presence_time/60:.1f}min" if face_presence_time is not None else ""
                safe_print(f"[LOG] Registro adicionado: {current_window_info['application']} - {current_window_info['page_title'] or 'N/A'}{presence_info}")
            else:
                safe_print("[ERROR] Não foi possível obter ID do usuário monitorado, pulando registro...")

        # Diminuir de 6 para 3 registros antes do envio (envio mais frequente)
        if len(registros) >= 3:
            # Sempre persistir tentativas e nunca descartar
            safe_print(f"[SEND] Preparando envio de {len(registros)} registros")
            for r in registros:
                ok = enviar_atividade(r)
                if not ok:
                    # Já salvo na fila offline dentro de enviar_atividade
                    pass
            registros.clear()

        # A cada ciclo, tentar reenviar fila offline
        _flush_offline_queue(max_items=100)
        
        # Salvar aplicações aprendidas periodicamente (a cada 60 ciclos = ~10 minutos)
        if not hasattr(main, '_save_counter'):
            main._save_counter = 0
        main._save_counter += 1
        
        if main._save_counter >= 60:  # A cada ~10 minutos
            save_learned_applications()
            main._save_counter = 0

        time.sleep(10)


if __name__ == '__main__':
    main()