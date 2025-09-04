
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
from urllib.parse import urlparse
try:
    import pygetwindow as gw
    import pyperclip
except ImportError:
    gw = None
    pyperclip = None

API_BASE_URL = 'https://30639375-c8ee-4839-b62a-4cdd5cf7f23e-00-29im557edjni.worf.replit.dev:8000'
LOGIN_URL = f"{API_BASE_URL}/login"
ATIVIDADE_URL = f"{API_BASE_URL}/atividade"
USUARIOS_MONITORADOS_URL = f"{API_BASE_URL}/usuarios-monitorados"

# Credenciais do agente (colocar no .env ou hardcode para teste)
AGENT_USER = os.getenv("AGENT_USER", "admin")
AGENT_PASS = os.getenv("AGENT_PASS", "Brasil@1402")

JWT_TOKEN = None


def get_headers():
    global JWT_TOKEN
    return {
        "Authorization": f"Bearer {JWT_TOKEN}" if JWT_TOKEN else "",
        "Content-Type": "application/json"
    }


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
            print(f"✅ Login bem-sucedido. Token obtido.")
        else:
            print(f"❌ Erro no login: {resp.status_code} {resp.text}")
            JWT_TOKEN = None
    except Exception as e:
        print(f"❌ Falha ao conectar no login: {e}")
        JWT_TOKEN = None


def get_logged_user():
    users = psutil.users()
    return users[0].name if users else None


def get_chrome_active_tab_url():
    """Tenta capturar a URL da aba ativa do Chrome usando diferentes métodos"""
    try:
        # Método 1: Tentar usar chrome-remote-interface (se disponível)
        try:
            result = subprocess.run([
                'node', '-e', '''
                const CDP = require('chrome-remote-interface');
                CDP(async (client) => {
                    const {Page, Runtime} = client;
                    await Page.enable();
                    const {frameTree} = await Page.getFrameTree();
                    console.log(frameTree.frame.url);
                    await client.close();
                }).catch(err => console.error('Chrome not accessible'));
                '''
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip()
                if url.startswith('http'):
                    return urlparse(url).netloc
        except:
            pass

        # Método 2: Tentar extrair URL do histórico do Chrome (último acesso)
        try:
            import sqlite3
            chrome_history_paths = [
                os.path.expanduser('~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History'),
                os.path.expanduser('~\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1\\History'),
            ]
            
            for history_path in chrome_history_paths:
                if os.path.exists(history_path):
                    # Copiar para temp para evitar lock
                    temp_history = history_path + '.temp'
                    try:
                        import shutil
                        shutil.copy2(history_path, temp_history)
                        
                        conn = sqlite3.connect(temp_history)
                        cursor = conn.cursor()
                        
                        # Pegar a URL mais recente (últimos 5 minutos)
                        cursor.execute('''
                            SELECT url FROM urls 
                            WHERE last_visit_time > (strftime('%s','now') - 300) * 1000000 + 11644473600000000
                            ORDER BY last_visit_time DESC 
                            LIMIT 1
                        ''')
                        
                        result = cursor.fetchone()
                        conn.close()
                        os.remove(temp_history)
                        
                        if result and result[0]:
                            return urlparse(result[0]).netloc
                    except:
                        if os.path.exists(temp_history):
                            os.remove(temp_history)
        except:
            pass

        # Método 3: Usar PowerShell para extrair URL via UI Automation (Windows 10+)
        try:
            ps_script = '''
            Add-Type -AssemblyName UIAutomationClient
            $automation = [System.Windows.Automation.AutomationElement]::RootElement
            $chromeWindows = $automation.FindAll([System.Windows.Automation.TreeScope]::Children, 
                [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty, "*Chrome*"))
            
            foreach ($window in $chromeWindows) {
                $addressBar = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, 
                    [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, 
                    [System.Windows.Automation.ControlType]::Edit))
                if ($addressBar -and $addressBar.Current.Name) {
                    Write-Output $addressBar.Current.Name
                    break
                }
            }
            '''
            
            result = subprocess.run(['powershell', '-Command', ps_script], 
                                 capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0 and result.stdout.strip():
                url_text = result.stdout.strip()
                if 'http' in url_text:
                    # Extrair URL da string
                    url_match = re.search(r'https?://[^\s]+', url_text)
                    if url_match:
                        return urlparse(url_match.group()).netloc
        except:
            pass

    except Exception as e:
        print(f"⚠️ Erro ao capturar URL do Chrome: {e}")
    
    return None


def extract_domain_from_title(window_title):
    """Extrai domínio do título da janela quando possível"""
    try:
        # Padrões comuns de domínios em títulos
        domain_patterns = [
            r'([a-zA-Z0-9-]+\.(?:com|org|net|edu|gov|br|co\.uk|de|fr|es|it|ru|cn|jp))',
            r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
            r'(?:https?://)?([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+)',
        ]
        
        for pattern in domain_patterns:
            match = re.search(pattern, window_title.lower())
            if match:
                domain = match.group(1)
                # Validar se parece um domínio real
                if '.' in domain and len(domain.split('.')) >= 2:
                    return domain
        
        # Padrões específicos para sites conhecidos
        known_patterns = {
            'youtube': 'youtube.com',
            'google': 'google.com',
            'facebook': 'facebook.com',
            'twitter': 'twitter.com',
            'linkedin': 'linkedin.com',
            'github': 'github.com',
            'stackoverflow': 'stackoverflow.com',
            'reddit': 'reddit.com',
            'wikipedia': 'wikipedia.org',
            'amazon': 'amazon.com',
        }
        
        title_lower = window_title.lower()
        for key, domain in known_patterns.items():
            if key in title_lower:
                return domain
                
    except Exception as e:
        print(f"⚠️ Erro ao extrair domínio do título: {e}")
    
    return None


def get_active_window_info():
    """Captura informações da janela ativa incluindo domínio quando possível"""
    try:
        window = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(window)
        
        # Tentar capturar URL/domínio do Chrome
        domain = None
        
        # Se for uma janela do Chrome, tentar capturar URL
        if 'chrome' in window_title.lower():
            domain = get_chrome_active_tab_url()
            print(f"🌐 Domínio capturado do Chrome: {domain}")
        
        # Se não conseguiu capturar domínio, tentar extrair do título
        if not domain:
            domain = extract_domain_from_title(window_title)
            if domain:
                print(f"🔍 Domínio extraído do título: {domain}")
        
        return {
            'window_title': window_title,
            'domain': domain,
            'application': get_application_name(window_title)
        }
        
    except Exception as e:
        print(f"❌ Erro ao capturar informações da janela: {e}")
        return {
            'window_title': 'Erro ao capturar janela',
            'domain': None,
            'application': 'unknown'
        }


def get_application_name(window_title):
    """Identifica a aplicação baseada no título da janela"""
    title_lower = window_title.lower()
    
    app_patterns = {
        'chrome': ['chrome', 'google chrome'],
        'firefox': ['firefox', 'mozilla firefox'],
        'edge': ['edge', 'microsoft edge'],
        'vscode': ['visual studio code', 'vscode'],
        'notepad': ['notepad', 'bloco de notas'],
        'excel': ['excel', 'microsoft excel'],
        'word': ['word', 'microsoft word'],
        'powerpoint': ['powerpoint', 'microsoft powerpoint'],
        'outlook': ['outlook', 'microsoft outlook'],
        'teams': ['teams', 'microsoft teams'],
        'slack': ['slack'],
        'discord': ['discord'],
        'whatsapp': ['whatsapp'],
        'telegram': ['telegram'],
    }
    
    for app, patterns in app_patterns.items():
        for pattern in patterns:
            if pattern in title_lower:
                return app
    
    return 'other'


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
                print(f"✅ Novo usuário monitorado criado: {usuario_nome} (ID: {user_id})")
            else:
                print(f"✅ Usuário monitorado encontrado: {usuario_nome} (ID: {user_id})")
            return user_id
        elif resp.status_code == 401:
            print("⚠️ Token expirado, renovando...")
            login()
            return get_usuario_monitorado_id(usuario_nome)
        else:
            print(
                f"❌ Erro ao buscar usuário monitorado: {resp.status_code} {resp.text}"
            )
            return None
    except Exception as e:
        print(f"❌ Erro ao consultar usuário monitorado: {e}")
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
        print(f"❌ Erro ao verificar usuário ativo: {e}")
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
            print(f"❌ Erro ao buscar configurações do usuário: {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ Erro ao consultar configurações do usuário: {e}")
        return None


def esta_em_horario_trabalho(usuario_nome, tz):
    """Verifica se o horário atual está dentro do horário de trabalho do usuário"""
    try:
        config = obter_configuracoes_horario_usuario(usuario_nome)
        if not config:
            print("⚠️ Configurações não encontradas, usando horário padrão (8-18h, seg-sex)")
            config = {
                'horario_inicio_trabalho': '08:00:00',
                'horario_fim_trabalho': '18:00:00',
                'dias_trabalho': '1,2,3,4,5',
                'monitoramento_ativo': True
            }
        
        # Se o monitoramento não está ativo, não enviar atividades
        if not config.get('monitoramento_ativo', True):
            print(f"⏸️ Monitoramento desativado para o usuário {usuario_nome}")
            return False
        
        agora = datetime.now(tz)
        
        # Verificar se é um dia de trabalho (1=Segunda, 7=Domingo)
        dia_semana = agora.isoweekday()
        dias_trabalho = [int(d) for d in config['dias_trabalho'].split(',')]
        
        if dia_semana not in dias_trabalho:
            print(f"⏰ Fora dos dias de trabalho: hoje é {dia_semana}, dias de trabalho: {dias_trabalho}")
            return False
        
        # Verificar se está no horário de trabalho
        horario_inicio = dt_time.fromisoformat(config['horario_inicio_trabalho'])
        horario_fim = dt_time.fromisoformat(config['horario_fim_trabalho'])
        hora_atual = agora.time()
        
        if horario_inicio <= hora_atual <= horario_fim:
            print(f"✅ Dentro do horário de trabalho: {hora_atual} ({horario_inicio}-{horario_fim})")
            return True
        else:
            print(f"⏰ Fora do horário de trabalho: {hora_atual} ({horario_inicio}-{horario_fim})")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar horário de trabalho: {e}")
        # Em caso de erro, permitir o envio para não quebrar o funcionamento
        return True


def enviar_atividade(registro):
    try:
        resp = requests.post(ATIVIDADE_URL,
                             json=registro,
                             headers=get_headers())
        if resp.status_code == 201:
            domain_info = f" | Domínio: {registro.get('domain', 'N/A')}" if registro.get('domain') else ""
            print(f"✅ Atividade enviada: {registro['active_window']}{domain_info}")
        elif resp.status_code == 401:
            print("⚠️ Token expirado, renovando...")
            login()
            enviar_atividade(registro)
        elif resp.status_code == 404 and "Usuário monitorado não encontrado" in resp.text:
            print(f"❌ Usuário monitorado ID {registro['usuario_monitorado_id']} não encontrado!")
            print("🔄 Tentando recriar usuário monitorado...")
            return False
        else:
            print(f"❌ Erro ao enviar atividade: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao enviar atividade: {e}")
        return False
    return True


def main():
    # Primeiro login
    login()

    last_usuario_nome = get_logged_user()
    usuario_monitorado_id = get_usuario_monitorado_id(last_usuario_nome)
    
    # Contador para verificação periódica do usuário
    verificacao_contador = 0

    last_window_info = {"window_title": "", "domain": None, "application": ""}
    ociosidade = 0
    registros = []

    tz = pytz.timezone('America/Sao_Paulo')

    print("🚀 Agente iniciado com captura de domínio!")
    print("📋 Métodos disponíveis:")
    print("   - Chrome DevTools Protocol")
    print("   - Histórico do Chrome")
    print("   - UI Automation (PowerShell)")
    print("   - Extração de domínio do título")
    print()

    while True:
        current_window_info = get_active_window_info()
        current_usuario_nome = get_logged_user()

        # Verificar se o nome do usuário mudou
        if current_usuario_nome != last_usuario_nome:
            print(f"🔄 Usuário do sistema mudou de '{last_usuario_nome}' para '{current_usuario_nome}'")
            last_usuario_nome = current_usuario_nome
            usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            verificacao_contador = 0  # Reset contador

        # Verificar periodicamente se o usuário ainda existe (a cada 10 ciclos = ~100 segundos)
        verificacao_contador += 1
        if verificacao_contador >= 10:
            print(f"🔍 Verificando se usuário {usuario_monitorado_id} ainda existe...")
            if not verificar_usuario_ativo(usuario_monitorado_id):
                print(f"⚠️ Usuário {usuario_monitorado_id} não encontrado, recriando...")
                usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            verificacao_contador = 0

        # Verificar mudança de janela/domínio
        if (current_window_info['window_title'] != last_window_info['window_title'] or 
            current_window_info['domain'] != last_window_info['domain']):
            ociosidade = 0
            last_window_info = current_window_info
        else:
            ociosidade += 10

        if ociosidade % 10 == 0:
            # Verificar se temos um ID válido antes de criar o registro
            if usuario_monitorado_id is None:
                print("⚠️ ID do usuário monitorado é None, tentando recriar...")
                usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
                
            if usuario_monitorado_id is not None:
                registro = {
                    'usuario_monitorado_id': usuario_monitorado_id,
                    'ociosidade': ociosidade,
                    'active_window': current_window_info['window_title'],
                    'domain': current_window_info['domain'],
                    'application': current_window_info['application'],
                    'horario': datetime.now(tz).isoformat()
                }
                registros.append(registro)
            else:
                print("❌ Não foi possível obter ID do usuário monitorado, pulando registro...")

        if len(registros) >= 6:
            # Verificar se estamos em horário de trabalho antes de enviar
            if esta_em_horario_trabalho(current_usuario_nome, tz):
                for r in registros:
                    enviar_atividade(r)
                registros.clear()
            else:
                # Fora do horário de trabalho, limpar registros sem enviar
                print(f"⏰ Fora do horário de trabalho, descartando {len(registros)} registros")
                registros.clear()

        time.sleep(10)


if __name__ == '__main__':
    main()
