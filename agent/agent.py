import time
import psutil
import requests
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
import base64
from PIL import ImageGrab, Image
import io

# Detectar se está rodando como executável
IS_EXECUTABLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def safe_print(*args, **kwargs):
    """Print seguro - completamente silencioso quando executável"""
    if not IS_EXECUTABLE:
        # Apenas quando rodando como script Python
        print(*args, **kwargs)
    # Quando executável: completamente silencioso (modo fantasma)
try:
    import pygetwindow as gw
    import pyperclip
except ImportError:
    gw = None
    pyperclip = None

API_BASE_URL = 'http://192.241.155.236:8010'
LOGIN_URL = f"{API_BASE_URL}/login"
ATIVIDADE_URL = f"{API_BASE_URL}/atividade"
USUARIOS_MONITORADOS_URL = f"{API_BASE_URL}/usuarios-monitorados"

# Credenciais do agente (HARDCODED - SEM .ENV)
AGENT_USER = "connect"
AGENT_PASS = "L@undry60"

# Configurações de monitoramento (HARDCODED)
SCREENSHOT_ENABLED = True
SCREENSHOT_QUALITY = 55
MONITOR_INTERVAL = 10  # segundos
IDLE_THRESHOLD = 600   # segundos (10 minutos)
REQUEST_TIMEOUT = 30   # segundos
MAX_RETRIES = 3

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
        'keywords': ['explorer', 'windows explorer', 'arquivos']
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
        'category': 'desenvolvimento',
        'keywords': ['cmd', 'prompt', 'terminal']
    },
    'powershell.exe': {
        'name': 'PowerShell',
        'category': 'desenvolvimento',
        'keywords': ['powershell', 'terminal']
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

JWT_TOKEN = None

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
        # Redirecionar stdout/stderr para evitar janelas
        sys.stdout = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
        sys.stderr = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
    except Exception as e:
        # Fallback silencioso se logging falhar
        pass
else:
    # Quando script Python, usar console normal
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def get_headers():
    global JWT_TOKEN
    return {
        "Authorization": f"Bearer {JWT_TOKEN}" if JWT_TOKEN else "",
        "Content-Type": "application/json"
    }

def detect_application_from_process(process_name):
    """Detectar aplicação pelo nome do processo"""
    if not process_name:
        return None
    
    process_lower = process_name.lower()
    
    # Busca direta na base de dados
    if process_lower in APPLICATION_DATABASE:
        return APPLICATION_DATABASE[process_lower]
    
    # Busca por palavras-chave
    for app_key, app_info in APPLICATION_DATABASE.items():
        for keyword in app_info['keywords']:
            if keyword.lower() in process_lower:
                return app_info
    
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


def login():
    """Faz login e obtém o token JWT"""
    global JWT_TOKEN
    try:
        resp = requests.post(LOGIN_URL,
                             json={
                                 "nome": AGENT_USER,
                                 "senha": AGENT_PASS
                             })
        if resp.status_code == 200:
            JWT_TOKEN = resp.json().get("token")
            safe_print(f"[OK] Login bem-sucedido. Token obtido.")
        else:
            safe_print(f"[ERROR] Erro no login: {resp.status_code} {resp.text}")
            JWT_TOKEN = None
    except Exception as e:
        safe_print(f"[ERROR] Falha ao conectar no login: {e}")
        JWT_TOKEN = None


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

def capture_screenshot():
    """Captura screenshot da tela atual"""
    try:
        from PIL import Image, ImageGrab
        
        # Capturar screenshot
        screenshot = ImageGrab.grab()
        
        # Redimensionar para economizar espaço (max 800x600)
        screenshot.thumbnail((800, 600), Image.Resampling.LANCZOS)
        
        # Converter para base64
        buffer = io.BytesIO()
        # Compressão agressiva para reduzir tamanho (qualidade ~ 55)
        screenshot.save(buffer, format='JPEG', quality=55, optimize=True)
        buffer.seek(0)
        
        # Codificar em base64
        screenshot_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        safe_print(f"[SCREENSHOT] Screenshot capturado: {len(screenshot_b64)} bytes")
        return screenshot_b64
        
    except Exception as e:
        safe_print(f"[ERROR] Erro ao capturar screenshot: {e}")
        return None

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
                # Fallback: usar detecção por título
                application = get_application_name(window_title)
                safe_print(f"[APP] Fallback: {application}")
                
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
    }

    for app, patterns in app_patterns.items():
        for pattern in patterns:
            if pattern in title_lower:
                return app

    return 'Sistema Local'


def get_usuario_monitorado_id(usuario_nome):
    """Busca ou cria usuário monitorado pelo nome"""
    try:
        resp = requests.get(USUARIOS_MONITORADOS_URL,
                            params={'nome': usuario_nome},
                            headers=get_headers())
        if resp.status_code == 200:
            data = resp.json()
            user_id = data.get('id')
            was_created = data.get('created', False)
            if was_created:
                safe_print(f"[OK] Novo usuário monitorado criado: {usuario_nome} (ID: {user_id})")
            else:
                safe_print(f"[OK] Usuário monitorado encontrado: {usuario_nome} (ID: {user_id})")
            return user_id
        elif resp.status_code == 401:
            safe_print("[WARN] Token expirado, renovando...")
            login()
            return get_usuario_monitorado_id(usuario_nome)
        else:
            safe_print(
                f"[ERROR] Erro ao buscar usuário monitorado: {resp.status_code} {resp.text}"
            )
            return None
    except Exception as e:
        safe_print(f"[ERROR] Erro ao consultar usuário monitorado: {e}")
        return None


def verificar_usuario_ativo(usuario_id):
    """Verifica se o usuário monitorado ainda existe e está ativo"""
    try:
        resp = requests.get(USUARIOS_MONITORADOS_URL,
                            headers=get_headers())
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
        resp = requests.get(USUARIOS_MONITORADOS_URL,
                            params={'nome': usuario_nome},
                            headers=get_headers())
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
    try:
        resp = requests.post(ATIVIDADE_URL,
                             json=registro,
                             headers=get_headers())
        if resp.status_code == 201:
            domain_info = f" | Domínio: {registro.get('domain', 'N/A')}" if registro.get('domain') else ""
            page_info = f" | Página: {registro.get('page_title', 'N/A')}" if registro.get('page_title') else ""
            url_info = f" | URL: {registro.get('url', 'N/A')}" if registro.get('url') else ""
            safe_print(f"[OK] Atividade enviada: {registro['active_window']}{domain_info}{page_info}{url_info}")
        elif resp.status_code == 401:
            safe_print("[WARN] Token expirado, renovando...")
            login()
            enviar_atividade(registro)
        elif resp.status_code == 404 and "Usuário monitorado não encontrado" in resp.text:
            safe_print(f"[ERROR] Usuário monitorado ID {registro['usuario_monitorado_id']} não encontrado!")
            safe_print("[INFO] Tentando recriar usuário monitorado...")
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


# =========================
#  Fila Offline Persistente
# =========================
_OFFLINE_QUEUE_FILE = os.path.join(os.path.dirname(__file__), 'offline_queue.jsonl')

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
    # Primeiro login
    login()

    last_usuario_nome = get_logged_user()
    usuario_monitorado_id = get_usuario_monitorado_id(last_usuario_nome)

    # Contador para verificação periódica do usuário
    verificacao_contador = 0

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

    while True:
        current_window_info = get_active_window_info()
        current_usuario_nome = get_logged_user()

        # Detectar mudança de usuário
        if current_usuario_nome != last_usuario_nome:
            safe_print(f"[USER] Mudanca de usuario: {last_usuario_nome} -> {current_usuario_nome}")
            last_usuario_nome = current_usuario_nome
            usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            verificacao_contador = 0  # Reset contador

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
            
            # Verificar se temos um ID válido antes de criar o registro
            if usuario_monitorado_id is None:
                safe_print("[WARN] ID do usuário monitorado é None, tentando recriar...")
                usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)

            # Capturar screenshot a cada 10 segundos
            screenshot_b64 = capture_screenshot()

            if usuario_monitorado_id is not None:
                registro = {
                    'usuario_monitorado_id': usuario_monitorado_id,
                    'ociosidade': ociosidade,
                    'active_window': current_window_info['window_title'],
                    'url': current_window_info['url'],
                    'page_title': current_window_info['page_title'],
                    'domain': current_window_info['domain'],
                    'application': current_window_info['application'],
                    'screenshot': screenshot_b64,
                    'horario': datetime.now(tz).isoformat()
                }
                registros.append(registro)
                safe_print(f"[LOG] Registro adicionado: {current_window_info['application']} - {current_window_info['page_title'] or 'N/A'} - {current_window_info['domain'] or 'N/A'}")
            else:
                safe_print("[ERROR] Não foi possível obter ID do usuário monitorado, pulando registro...")

        if len(registros) >= 6:
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

        time.sleep(10)


if __name__ == '__main__':
    main()