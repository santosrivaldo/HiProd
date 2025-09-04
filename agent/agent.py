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
    """Tenta capturar a URL da aba ativa do Chrome de forma mais precisa"""
    try:
        # Método mais simples e confiável: usar PowerShell para obter URL da aba ativa
        ps_script = '''
        try {
            Add-Type -AssemblyName UIAutomationClient
            $automation = [System.Windows.Automation.AutomationElement]::RootElement

            # Procurar janela ativa do Chrome
            $activeWindow = $automation.FindFirst([System.Windows.Automation.TreeScope]::Children, 
                [System.Windows.Automation.AndCondition]::new(@(
                    [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty, "Chrome_WidgetWin_1"),
                    [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty, (Get-Process -Name "chrome" | Where-Object {$_.MainWindowTitle -ne ""} | Select-Object -First 1).Id)
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
                    if ($url -and $url.StartsWith("http")) {
                        Write-Output $url
                    }
                }
            }
        } catch {
            # Silencioso se falhar
        }
        '''

        result = subprocess.run(['powershell', '-Command', ps_script], 
                             capture_output=True, text=True, timeout=2)

        if result.returncode == 0 and result.stdout.strip():
            url = result.stdout.strip()
            if url.startswith('http'):
                parsed = urlparse(url)
                return parsed.netloc

    except Exception as e:
        print(f"⚠️ Erro ao capturar URL do Chrome: {e}")

    return None


def extract_domain_from_title(window_title):
    """Extrai domínio do título da janela quando possível com maior precisão"""
    try:
        if not window_title:
            return None

        # Primeiro: procurar por URLs completas no título
        url_patterns = [
            r'https?://([a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+)',
            r'(?:^|\s)([a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:\s|$)',  # domínios com subdomínio
            r'localhost:(\d+)',  # localhost com porta
            r'(\d+\.\d+\.\d+\.\d+):?(\d+)?',  # IPs
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, window_title)
            if matches:
                if 'localhost' in pattern:
                    return f"localhost:{matches[0]}" if matches[0] else "localhost"
                elif r'\d+\.\d+\.\d+\.\d+' in pattern:
                    # Para IPs, retornar com porta se houver
                    ip, port = matches[0] if isinstance(matches[0], tuple) else (matches[0], None)
                    return f"{ip}:{port}" if port else ip
                else:
                    domain = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    # Validar se é um domínio válido
                    if '.' in domain and len(domain.split('.')) >= 2:
                        return domain

        # Segundo: procurar por domínios específicos em contexto
        specific_patterns = [
            r'([a-zA-Z0-9-]+\.bitrix24\.com\.br)',  # Bitrix24 Brasil
            r'([a-zA-Z0-9-]+\.replit\.dev)',  # Replit apps
            r'([a-zA-Z0-9-]+\.vercel\.app)',  # Vercel apps
            r'([a-zA-Z0-9-]+\.herokuapp\.com)',  # Heroku apps
            r'([a-zA-Z0-9-]+\.github\.io)',  # GitHub pages
        ]

        for pattern in specific_patterns:
            match = re.search(pattern, window_title.lower())
            if match:
                return match.group(1)

        # Terceiro: padrões mais gerais (mais restritivos para evitar falsos positivos)
        general_patterns = [
            r'(?:^|\s|\(|-)([a-zA-Z0-9-]+\.(?:com\.br|co\.uk|gov\.br))(?:\s|\)|$|/)',  # domínios BR/UK específicos
            r'(?:^|\s|\(|-)([a-zA-Z0-9-]+\.(?:com|org|net|edu|gov|br))(?:\s|\)|$|/)',  # TLDs principais
        ]

        for pattern in general_patterns:
            match = re.search(pattern, window_title.lower())
            if match:
                domain = match.group(1)
                # Validações adicionais para evitar falsos positivos
                if (len(domain) >= 4 and 
                    '.' in domain and 
                    len(domain.split('.')) >= 2 and
                    not domain.startswith('.')):
                    return domain

        # Quarto: apenas se nada foi encontrado, usar padrões conhecidos (mais restritivo)
        known_sites = {
            'youtube.com': r'\byoutube\b.*\bcom\b',
            'facebook.com': r'\bfacebook\b',
            'twitter.com': r'\btwitter\b',
            'linkedin.com': r'\blinkedin\b',
            'github.com': r'\bgithub\b',
            'stackoverflow.com': r'\bstackoverflow\b',
            'reddit.com': r'\breddit\b',
            'wikipedia.org': r'\bwikipedia\b',
        }

        title_lower = window_title.lower()
        for domain, pattern in known_sites.items():
            if re.search(pattern, title_lower):
                return domain

    except Exception as e:
        print(f"⚠️ Erro ao extrair domínio do título: {e}")

    return None


def get_active_window_info():
    """Captura informações da janela ativa incluindo domínio quando possível"""
    try:
        window = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(window)

        # Identificar aplicação primeiro
        application = get_application_name(window_title)
        domain = None

        # Se for navegador, tentar capturar URL real
        if 'Chrome' in application or 'Firefox' in application or 'Edge' in application:
            domain = get_chrome_active_tab_url()
            if domain:
                print(f"🌐 URL capturada do navegador: {domain}")
            else:
                # Se não conseguiu capturar URL, extrair do título com mais cuidado
                domain = extract_domain_from_title(window_title)
                if domain:
                    print(f"🔍 Domínio extraído do título: {domain}")
                else:
                    print(f"⚠️ Não foi possível extrair domínio do título: {window_title[:50]}...")

        # Para aplicações desktop conhecidas, não extrair domínio
        elif application in ['VS Code', 'Visual Studio', 'Notepad', 'Notepad++', 'Sublime Text', 
                           'Atom', 'Microsoft Word', 'Microsoft Excel', 'PowerPoint', 'Windows Explorer']:
            domain = None
            print(f"📱 Aplicação desktop detectada: {application}")
        
        # Para outras aplicações, tentar extrair domínio apenas se parecer ser web-based
        else:
            # Verificar se o título contém indicações de conteúdo web
            web_indicators = ['http', 'www.', '.com', '.org', '.net', '.br', 'localhost']
            has_web_content = any(indicator in window_title.lower() for indicator in web_indicators)
            
            if has_web_content:
                domain = extract_domain_from_title(window_title)
                if domain:
                    print(f"🔍 Domínio extraído do título: {domain}")
            else:
                domain = None
                print(f"📱 Aplicação local detectada: {application}")

        return {
            'window_title': window_title,
            'domain': domain,
            'application': application
        }

    except Exception as e:
        print(f"❌ Erro ao capturar informações da janela: {e}")
        return {
            'window_title': 'Erro ao capturar janela',
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

        # Detectar mudança de usuário
        if current_usuario_nome != last_usuario_nome:
            print(f"👤 Mudança de usuário: {last_usuario_nome} -> {current_usuario_nome}")
            last_usuario_nome = current_usuario_nome
            usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            verificacao_contador = 0  # Reset contador

            # Se não conseguiu obter o ID do usuário, pular este ciclo
            if not usuario_monitorado_id or usuario_monitorado_id == 0:
                print(f"⚠️ Não foi possível obter ID válido para usuário {current_usuario_nome}, aguardando próximo ciclo...")
                time.sleep(10)
                continue

        # Verificar se temos um ID válido antes de continuar
        if not usuario_monitorado_id or usuario_monitorado_id == 0:
            print(f"⚠️ ID de usuário inválido ({usuario_monitorado_id}), tentando reobter...")
            usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            if not usuario_monitorado_id or usuario_monitorado_id == 0:
                print("❌ Falha ao obter ID válido, aguardando 30 segundos...")
                time.sleep(30)
                continue

        # Verificar periodicamente se o usuário ainda existe (a cada 10 ciclos = ~100 segundos)
        verificacao_contador += 1
        if verificacao_contador >= 10:
            print(f"🔍 Verificando se usuário {usuario_monitorado_id} ainda existe...")
            if not verificar_usuario_ativo(usuario_monitorado_id):
                print(f"⚠️ Usuário {usuario_monitorado_id} não encontrado, recriando...")
                usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)
            verificacao_contador = 0

        # Verificar mudança significativa de janela/domínio/aplicação
        window_changed = (
            current_window_info['window_title'] != last_window_info['window_title'] or 
            current_window_info['domain'] != last_window_info['domain'] or
            current_window_info['application'] != last_window_info['application']
        )

        if window_changed:
            # Log da mudança para debug
            if current_window_info['window_title'] != last_window_info['window_title']:
                print(f"🔄 Mudança de janela: {last_window_info['window_title'][:50]}... -> {current_window_info['window_title'][:50]}...")
            if current_window_info['domain'] != last_window_info['domain']:
                print(f"🌐 Mudança de domínio: {last_window_info['domain']} -> {current_window_info['domain']}")
            if current_window_info['application'] != last_window_info['application']:
                print(f"📱 Mudança de aplicação: {last_window_info['application']} -> {current_window_info['application']}")

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