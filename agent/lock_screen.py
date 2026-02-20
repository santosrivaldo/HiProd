#!/usr/bin/env python3
"""
Tela de Bloqueio do HiProd Agent - Fase 1
Interface gráfica com tela de bloqueio e botão de iniciar
Suporta múltiplos monitores
Integração com Bitrix24 Timeman API
"""

import tkinter as tk
import sys
import os
import threading
import psutil
import json
from datetime import datetime

from floating_button import Popup, create_floating_button, FloatingButton

# Variável global para controlar o agente
AGENT_RUNNING = True
AGENT_PAUSED = False  # Nova variável para pausar o agente durante intervalos
AGENT_THREAD = None

# Detectar se está rodando como executável
IS_EXECUTABLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def import_agent_module():
    """
    Importa o módulo agent de forma compatível com executável e script Python.
    Retorna o módulo agent ou None se não encontrado.
    """
    try:
        if IS_EXECUTABLE:
            # Quando executável, importar diretamente
            import agent as agent_module
            return agent_module
        else:
            # Quando script Python, usar importlib.util (caminho absoluto para não depender do cwd)
            import importlib.util
            _agent_dir = os.path.dirname(os.path.abspath(__file__))
            agent_path = os.path.join(_agent_dir, 'agent.py')
            
            if not os.path.exists(agent_path):
                print(f"[ERROR] agent.py não encontrado em: {agent_path}")
                raise FileNotFoundError("agent.py não encontrado")
            
            # Garantir que o diretório do agent está no path para imports internos
            if _agent_dir not in sys.path:
                sys.path.insert(0, _agent_dir)
            
            spec = importlib.util.spec_from_file_location("agent", agent_path)
            agent_module = importlib.util.module_from_spec(spec)
            sys.modules["agent"] = agent_module
            spec.loader.exec_module(agent_module)
            return agent_module
    except Exception as e:
        print(f"[ERROR] Erro ao importar agent: {e}")
        import traceback
        traceback.print_exc()
        return None

# Função para enviar notificações do Windows
def show_windows_notification(title, message, duration=5):
    """Exibe uma notificação toast no Windows"""
    try:
        # Tentar usar win10toast primeiro
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=duration, threaded=True)
            return True
        except ImportError:
            pass
        
        # Tentar usar plyer
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                timeout=duration,
                app_name="HiProd Agent"
            )
            return True
        except ImportError:
            pass
        
        # Fallback: usar PowerShell para notificação
        try:
            import subprocess
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title}</text>
                        <text id="2">{message}</text>
                    </binding>
                </visual>
            </toast>
"@
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("HiProd").Show($toast)
            '''
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=5)
            return True
        except:
            pass
        
        # Último fallback: MessageBox do Windows
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)  # MB_ICONINFORMATION
            return True
        except:
            pass
        
        print(f"[NOTIFY] {title}: {message}")
        return False
    except Exception as e:
        print(f"[WARN] Erro ao exibir notificação: {e}")
        return False

try:
    import requests
except ImportError:
    requests = None
    print("[WARN] Módulo requests não encontrado. Instale com: pip install requests")

try:
    import win32gui
    import win32con
    import win32api
    import win32security
    import win32net
    import win32netcon
except ImportError:
    # Se não tiver pywin32, continuar sem essas funcionalidades
    pass

# Detectar se está rodando como executável
IS_EXECUTABLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Configuração da API Bitrix24
BITRIX24_WEBHOOK_URL = "https://grupohi.bitrix24.com.br/rest/39949/1x1rdu5fmqncb5fp"

# Cache do USER_ID do Bitrix24
_bitrix_user_cache = {
    'user_id': None,
    'email': None
}


def get_user_email_for_bitrix():
    """
    Obtém o email do usuário para identificação no Bitrix24.
    Tenta obter de várias fontes.
    """
    # Primeiro, tentar usar a função existente get_user_info
    try:
        user_info = get_user_info()
        if user_info and user_info.get('email'):
            return user_info['email']
    except:
        pass
    
    # Fallback: construir email baseado no nome de usuário
    try:
        username = get_logged_user()
        if username:
            # Formato padrão: usuario@grupohi.com.br
            email = f"{username.lower()}@grupohi.com.br"
            print(f"[API] Email construído a partir do usuário: {email}")
            return email
    except:
        pass
    
    return None


def get_bitrix_user_id_by_email(email):
    """
    Busca o USER_ID do Bitrix24 pelo email do usuário.
    
    Args:
        email: Email do usuário para buscar
        
    Retorna:
        - USER_ID (int): ID do usuário no Bitrix24
        - None: Usuário não encontrado ou erro
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return None
    
    # Verificar cache
    if _bitrix_user_cache['email'] == email and _bitrix_user_cache['user_id']:
        print(f"[API] Usando USER_ID em cache: {_bitrix_user_cache['user_id']}")
        return _bitrix_user_cache['user_id']
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/user.get.json"
        
        # Buscar usuário pelo email
        params = {
            "filter[EMAIL]": email
        }
        
        print(f"[API] Buscando usuário pelo email: {email}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Resposta user.get: {json.dumps(data, indent=2)}")
        
        if 'result' in data and len(data['result']) > 0:
            user_id = data['result'][0].get('ID')
            if user_id:
                # Atualizar cache
                _bitrix_user_cache['user_id'] = int(user_id)
                _bitrix_user_cache['email'] = email
                print(f"[API] ✓ USER_ID encontrado: {user_id}")
                return int(user_id)
        
        print(f"[API] Usuário não encontrado pelo email: {email}")
        return None
        
    except Exception as e:
        print(f"[API] Erro ao buscar USER_ID: {e}")
        return None


def get_current_bitrix_user_id():
    """
    Obtém o USER_ID do Bitrix24 para o usuário atual.
    """
    email = get_user_email_for_bitrix()
    if email:
        return get_bitrix_user_id_by_email(email)
    return None


def get_timeman_settings(user_id=None):
    """
    Obtém as configurações de horário de trabalho do usuário no Bitrix24.
    
    Retorna:
        dict com as configurações ou None em caso de erro
        Exemplo: {
            'UF_TIMEMAN': True,  # Controle de ponto habilitado
            'UF_TM_MAX_START': '09:00',  # Horário máximo de início
            'UF_TM_MIN_FINISH': '18:00',  # Horário mínimo de término
            'UF_TM_MIN_DURATION': '08:00',  # Duração mínima do expediente
            ...
        }
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return None
    
    # Obter USER_ID se não fornecido
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/timeman.settings.get.json"
        
        params = {}
        if user_id:
            params['USER_ID'] = user_id
            print(f"[API] Buscando configurações de horário para USER_ID: {user_id}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Configurações de horário: {json.dumps(data, indent=2)}")
        
        if 'result' in data:
            return data['result']
        
        return None
        
    except Exception as e:
        print(f"[API] Erro ao buscar configurações de horário: {e}")
        return None


def is_work_hours(user_id=None):
    """
    Verifica se está em horário de expediente baseado nas configurações do Bitrix24.
    
    Retorna:
        bool: True se está em horário de expediente, False caso contrário
    """
    try:
        settings = get_timeman_settings(user_id)
        if not settings:
            print("[INFO] Não foi possível obter configurações de horário, permitindo acesso")
            return True  # Se não conseguir verificar, permite por padrão
        
        current_time = datetime.now().time()
        
        # Verificar se o expediente está aberto primeiro
        timeman_info = check_timeman_status(user_id)
        if timeman_info and timeman_info.get('status') == 'OPENED':
            print(f"[INFO] Expediente está aberto. Permitindo agente de atividades.")
            return True
        
        # Se o expediente não está aberto, verificar horário
        # Verificar horário mínimo de término (UF_TM_MIN_FINISH)
        # Se já passou do horário mínimo de término, não está mais em horário
        min_finish = settings.get('UF_TM_MIN_FINISH')
        if min_finish:
            try:
                min_finish_time = datetime.strptime(min_finish, '%H:%M').time()
                if current_time >= min_finish_time:
                    print(f"[INFO] Horário atual ({current_time.strftime('%H:%M')}) está após o horário mínimo de término ({min_finish})")
                    print("[INFO] Não está mais em horário de expediente. Agente não será iniciado.")
                    return False
            except:
                pass
        
        # Verificar horário máximo de início (UF_TM_MAX_START)
        # Se ainda não passou do horário máximo de início, pode estar em horário
        max_start = settings.get('UF_TM_MAX_START')
        if max_start:
            try:
                max_start_time = datetime.strptime(max_start, '%H:%M').time()
                if current_time <= max_start_time:
                    print(f"[INFO] Horário atual ({current_time.strftime('%H:%M')}) está antes ou no horário máximo de início ({max_start})")
                    print("[INFO] Ainda pode estar em horário de expediente. Permitindo agente.")
                    return True
            except:
                pass
        
        # Se não há restrições claras e expediente não está aberto, não permitir
        print("[INFO] Expediente não está aberto e não está em horário de expediente")
        return False
        
    except Exception as e:
        print(f"[ERROR] Erro ao verificar horário de expediente: {e}")
        return True  # Em caso de erro, permite por padrão


def get_user_work_schedule(user_id=None):
    """
    Obtém informações detalhadas do usuário incluindo horário de trabalho.
    
    Retorna:
        dict com informações do usuário ou None
    """
    if requests is None:
        return None
    
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    if not user_id:
        return None
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/user.get.json"
        
        params = {'ID': user_id}
        
        print(f"[API] Buscando dados do usuário ID: {user_id}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'result' in data and len(data['result']) > 0:
            user_data = data['result'][0]
            
            # Extrair informações relevantes
            schedule_info = {
                'user_id': user_id,
                'name': f"{user_data.get('NAME', '')} {user_data.get('LAST_NAME', '')}".strip(),
                'email': user_data.get('EMAIL', ''),
                'work_position': user_data.get('WORK_POSITION', ''),
                'personal_birthday': user_data.get('PERSONAL_BIRTHDAY', ''),
                'time_zone': user_data.get('TIME_ZONE', ''),
                'timeman_enabled': user_data.get('UF_TIMEMAN', False),
            }
            
            print(f"[API] Dados do usuário: {json.dumps(schedule_info, indent=2, ensure_ascii=False)}")
            return schedule_info
        
        return None
        
    except Exception as e:
        print(f"[API] Erro ao buscar dados do usuário: {e}")
        return None


def get_user_manager(user_id=None):
    """
    Obtém informações do coordenador/gerente do usuário no Bitrix24.
    
    Retorna:
        dict com informações do coordenador ou None
    """
    if requests is None:
        return None
    
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    if not user_id:
        return None
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/user.get.json"
        
        # Buscar todos os campos do usuário para encontrar o supervisor
        params = {
            'ID': user_id,
            # Não especificar select para pegar todos os campos
        }
        
        print(f"[API] Buscando supervisor do usuário ID: {user_id}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'result' in data and len(data['result']) > 0:
            user_data = data['result'][0]
            
            # Debug: mostrar todos os campos disponíveis e seus valores
            print(f"[API] Total de campos disponíveis: {len(user_data.keys())}")
            print(f"[API] Campos disponíveis: {list(user_data.keys())}")
            
            # Mostrar campos que podem conter supervisor
            print("[API] Campos relacionados a supervisor/manager/head:")
            for key, value in user_data.items():
                key_upper = key.upper()
                if any(term in key_upper for term in ['SUPERVISOR', 'MANAGER', 'HEAD', 'BOSS', 'LEADER', 'COORD']):
                    print(f"  - {key}: {value}")
            
            # Buscar ID do supervisor/coordenador (priorizar campos de supervisor)
            manager_id = None
            
            # Priorizar campos de supervisor primeiro
            supervisor_fields = [
                'SUPERVISOR_ID',
                'UF_SUPERVISOR',
                'UF_SUPERVISOR_ID',
                'SUPERVISOR',
                'MANAGER_ID',
                'UF_MANAGER',
                'UF_MANAGER_ID',
                'UF_HEAD',
                'UF_HEAD_ID', 
                'UF_DEPARTMENT_HEAD',
                'HEAD_ID'
            ]
            
            for field in supervisor_fields:
                if field in user_data and user_data[field]:
                    manager_id = user_data[field]
                    print(f"[API] ✓ Supervisor encontrado no campo '{field}': {manager_id}")
                    break
            
            # Se não encontrou, mostrar todos os campos que contêm ID para debug
            if not manager_id:
                print("[API] Supervisor não encontrado nos campos padrão. Verificando todos os campos...")
                relevant_fields = []
                for key, value in user_data.items():
                    key_upper = key.upper()
                    if ('ID' in key_upper or 'SUPERVISOR' in key_upper or 'MANAGER' in key_upper or 
                        'HEAD' in key_upper or 'BOSS' in key_upper or 'LEADER' in key_upper):
                        relevant_fields.append((key, value))
                        print(f"[API] Campo relevante '{key}': {value}")
                        # Se o valor parece ser um ID numérico, tentar usar
                        if value and str(value).isdigit() and int(value) > 0:
                            print(f"[API] Tentando usar campo '{key}' como supervisor ID: {value}")
                            manager_id = int(value)
                            break
                
                # Se ainda não encontrou, tentar qualquer campo que tenha um valor numérico válido
                if not manager_id:
                    for key, value in user_data.items():
                        if value and str(value).isdigit() and int(value) > 0 and int(value) != user_id:
                            # Verificar se esse ID corresponde a um usuário válido
                            try:
                                test_url = f"{BITRIX24_WEBHOOK_URL}/user.get.json"
                                test_response = requests.get(test_url, params={'ID': int(value)}, timeout=5)
                                if test_response.status_code == 200:
                                    test_data = test_response.json()
                                    if 'result' in test_data and len(test_data['result']) > 0:
                                        print(f"[API] Campo '{key}' contém um ID de usuário válido: {value}")
                                        manager_id = int(value)
                                        break
                            except:
                                pass
            
            if not manager_id:
                print("[API] Coordenador não encontrado nos campos diretos do usuário")
                # Tentar buscar pelo departamento
                departments = user_data.get('UF_DEPARTMENT', [])
                print(f"[API] Departamentos do usuário: {departments}")
                
                if departments:
                    # Buscar chefe do departamento
                    dept_id = departments[0] if isinstance(departments, list) else departments
                    try:
                        print(f"[API] Buscando chefe do departamento ID: {dept_id}")
                        dept_url = f"{BITRIX24_WEBHOOK_URL}/department.get.json"
                        dept_response = requests.get(dept_url, params={'ID': dept_id}, timeout=10)
                        dept_response.raise_for_status()
                        dept_data = dept_response.json()
                        print(f"[API] Dados do departamento: {json.dumps(dept_data, indent=2, ensure_ascii=False)}")
                        
                        if 'result' in dept_data and len(dept_data['result']) > 0:
                            dept_info = dept_data['result'][0]
                            # Tentar diferentes campos no departamento
                            dept_manager_fields = ['UF_HEAD', 'HEAD_ID', 'MANAGER_ID']
                            for field in dept_manager_fields:
                                if field in dept_info and dept_info[field]:
                                    manager_id = dept_info[field]
                                    print(f"[API] Coordenador encontrado no departamento (campo '{field}'): {manager_id}")
                                    break
                    except Exception as e:
                        print(f"[API] Erro ao buscar chefe do departamento: {e}")
                        import traceback
                        traceback.print_exc()
            
            if manager_id:
                # Buscar dados do coordenador
                try:
                    print(f"[API] Buscando dados do coordenador ID: {manager_id}")
                    manager_url = f"{BITRIX24_WEBHOOK_URL}/user.get.json"
                    manager_response = requests.get(manager_url, params={'ID': manager_id}, timeout=10)
                    manager_response.raise_for_status()
                    manager_data = manager_response.json()
                    
                    if 'result' in manager_data and len(manager_data['result']) > 0:
                        manager_info = manager_data['result'][0]
                        manager_name = f"{manager_info.get('NAME', '')} {manager_info.get('LAST_NAME', '')}".strip()
                        manager_email = manager_info.get('EMAIL', '')
                        
                        if not manager_name:
                            manager_name = manager_info.get('LOGIN', f'Usuário {manager_id}')
                        
                        result = {
                            'manager_id': manager_id,
                            'manager_name': manager_name,
                            'manager_email': manager_email
                        }
                        
                        print(f"[API] ✓ Coordenador encontrado: {manager_name} (ID: {manager_id}, Email: {manager_email})")
                        return result
                    else:
                        print(f"[API] Coordenador ID {manager_id} não encontrado na resposta")
                except Exception as e:
                    print(f"[API] Erro ao buscar dados do coordenador ID {manager_id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Se não encontrou coordenador, tentar buscar administradores ou usar um fallback
            print("[API] ⚠ Coordenador não encontrado. Tentando buscar administradores...")
            try:
                # Buscar usuários com permissões de administrador
                admin_url = f"{BITRIX24_WEBHOOK_URL}/user.get.json"
                admin_params = {
                    'filter': {'ACTIVE': 'Y'},
                    'select': ['ID', 'NAME', 'LAST_NAME', 'EMAIL', 'UF_DEPARTMENT']
                }
                admin_response = requests.get(admin_url, params=admin_params, timeout=10)
                admin_response.raise_for_status()
                admin_data = admin_response.json()
                
                if 'result' in admin_data and len(admin_data['result']) > 0:
                    # Usar o primeiro usuário ativo como fallback (pode ser ajustado)
                    fallback_user = admin_data['result'][0]
                    fallback_name = f"{fallback_user.get('NAME', '')} {fallback_user.get('LAST_NAME', '')}".strip()
                    if not fallback_name:
                        fallback_name = fallback_user.get('LOGIN', f'Usuário {fallback_user.get("ID")}')
                    
                    result = {
                        'manager_id': fallback_user.get('ID'),
                        'manager_name': fallback_name,
                        'manager_email': fallback_user.get('EMAIL', '')
                    }
                    
                    print(f"[API] ⚠ Usando usuário fallback como coordenador: {fallback_name} (ID: {fallback_user.get('ID')})")
                    return result
            except Exception as e:
                print(f"[API] Erro ao buscar usuários fallback: {e}")
            
            print("[API] ❌ Coordenador não encontrado e não foi possível usar fallback")
            return None
        
        return None
        
    except Exception as e:
        print(f"[API] Erro ao buscar coordenador: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_timeman_status(user_id=None):
    """
    Verifica o status do expediente do usuário no Bitrix24.
    
    Args:
        user_id: ID do usuário no Bitrix24 (opcional, busca automaticamente)
        
    Retorna:
        dict com:
            - 'status': 'OPENED', 'CLOSED', 'PAUSED', 'EXPIRED' ou None
            - 'worked_today': True se já trabalhou hoje (expediente foi aberto)
            - 'can_open': True se pode abrir expediente
            - 'time_start': Horário de início (se houver)
            - 'time_finish': Horário de fim (se houver)
            - 'duration': Duração trabalhada (se houver)
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return {'status': None, 'worked_today': False, 'can_open': True}
    
    # Obter USER_ID se não fornecido
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/timeman.status.json"
        
        params = {}
        if user_id:
            params['USER_ID'] = user_id
            print(f"[API] Verificando status do expediente para USER_ID: {user_id}")
        else:
            print(f"[API] Verificando status do expediente (usuário do webhook)")
        
        print(f"[API] URL: {url}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Resposta: {json.dumps(data, indent=2)}")
        
        if 'result' in data:
            result = data['result']
            status = result.get('STATUS', 'CLOSED')
            time_start = result.get('TIME_START')
            time_finish = result.get('TIME_FINISH')
            duration = result.get('DURATION', '00:00:00')
            time_leaks = result.get('TIME_LEAKS', '00:00:00')  # Tempo de pausas
            
            # Verificar se TIME_START é do dia anterior (novo dia = novo expediente)
            is_new_day = False
            if time_start:
                try:
                    # Parse do TIME_START (formato: "2025-12-01T09:01:01-03:00")
                    start_datetime = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
                    # Comparar apenas a data (sem hora)
                    today = datetime.now().date()
                    start_date = start_datetime.date()
                    
                    if start_date < today:
                        is_new_day = True
                        print(f"[API] 📅 TIME_START é do dia anterior ({start_date}), considerando novo expediente")
                except Exception as e:
                    print(f"[API] ⚠ Erro ao verificar data do TIME_START: {e}")
            
            # Verificar se já trabalhou hoje (tem TIME_START E não é do dia anterior)
            worked_today = time_start is not None and time_start != '' and not is_new_day
            
            # Verificar se pode abrir expediente
            # Não pode abrir se: CLOSED com TIME_FINISH (já fechou hoje) E não é novo dia
            can_open = True
            if status == 'CLOSED' and time_finish and not is_new_day:
                can_open = False
                print(f"[API] ⚠ Expediente já foi encerrado hoje às {time_finish}")
                print(f"[API] ⚠ Duração trabalhada: {duration}")
            
            # Se é novo dia, pode abrir mesmo se estiver CLOSED
            if is_new_day:
                can_open = True
                print(f"[API] ✓ Novo dia detectado - permitindo abertura de novo expediente")
            
            print(f"[API] Status do expediente: {status}")
            print(f"[API] Duração: {duration} | Pausas: {time_leaks}")
            print(f"[API] TIME_START: {time_start}")
            print(f"[API] É novo dia: {is_new_day}")
            print(f"[API] Já trabalhou hoje: {worked_today}")
            print(f"[API] Pode abrir expediente: {can_open}")
            
            return {
                'status': status,
                'worked_today': worked_today,
                'can_open': can_open,
                'time_start': time_start,
                'time_finish': time_finish,
                'duration': duration,
                'time_leaks': time_leaks
            }
        else:
            print(f"[API] Resposta sem 'result': {data}")
            return {'status': 'CLOSED', 'worked_today': False, 'can_open': True}
            
    except requests.exceptions.RequestException as e:
        print(f"[API] Erro na requisição: {e}")
        return {'status': None, 'worked_today': False, 'can_open': True}
    except json.JSONDecodeError as e:
        print(f"[API] Erro ao decodificar JSON: {e}")
        return {'status': None, 'worked_today': False, 'can_open': True}
    except Exception as e:
        print(f"[API] Erro inesperado: {e}")
        return None


def open_timeman(user_id=None, report="Início do expediente via HiProd Agent"):
    """
    Abre o expediente do usuário no Bitrix24.
    
    Args:
        user_id: ID do usuário no Bitrix24 (opcional, busca automaticamente)
        report: Relatório/comentário para o início do expediente
        
    Retorna:
        - True: Expediente aberto com sucesso
        - False: Erro ao abrir expediente
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return False
    
    # Obter USER_ID se não fornecido
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/timeman.open.json"
        
        # Dados para abrir o expediente
        payload = {
            "TIME": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "REPORT": report
        }
        
        if user_id:
            payload['USER_ID'] = user_id
            print(f"[API] Abrindo expediente para USER_ID: {user_id}")
        
        print(f"[API] URL: {url}")
        print(f"[API] Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Resposta: {json.dumps(data, indent=2)}")
        
        if 'result' in data:
            status = data['result'].get('STATUS', '')
            if status == 'OPENED':
                print("[API] ✓ Expediente aberto com sucesso!")
                return True
            else:
                print(f"[API] Status após abrir: {status}")
                return True  # Pode retornar outro status mas ainda assim funcionou
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[API] Erro na requisição: {e}")
        return False
    except Exception as e:
        print(f"[API] Erro inesperado: {e}")
        return False


def close_timeman(user_id=None, report="Fim do expediente via HiProd Agent"):
    """
    Fecha o expediente do usuário no Bitrix24.
    Usa o método timeman.close
    
    Args:
        user_id: ID do usuário no Bitrix24 (opcional, busca automaticamente)
        report: Relatório/comentário para o fim do expediente
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return False
    
    # Obter USER_ID se não fornecido
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/timeman.close.json"
        
        # Obter timezone local e formatar corretamente
        now = datetime.now()
        # Formato ISO 8601 com timezone (Bitrix24 espera este formato)
        time_str = now.strftime("%Y-%m-%dT%H:%M:%S")
        # Adicionar offset de timezone (UTC-3 para Brasil)
        from datetime import timezone, timedelta
        tz_offset = timedelta(hours=-3)  # UTC-3 (Brasil)
        time_with_tz = (now.replace(tzinfo=timezone(tz_offset))).strftime("%Y-%m-%dT%H:%M:%S%z")
        # Formatar timezone como +00:00 ou -03:00
        if time_with_tz.endswith('-0300'):
            time_with_tz = time_with_tz.replace('-0300', '-03:00')
        elif time_with_tz.endswith('+0000'):
            time_with_tz = time_with_tz.replace('+0000', '+00:00')
        
        payload = {
            "TIME": time_with_tz,
            "REPORT": report
        }
        
        if user_id:
            payload['USER_ID'] = user_id
        
        print(f"[API] 🏁 Finalizando expediente para USER_ID: {user_id}")
        print(f"[API] URL: {url}")
        print(f"[API] Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Resposta close: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if 'result' in data:
            duration = data['result'].get('DURATION', 'N/A')
            print(f"[API] ✓ Expediente finalizado com sucesso! Duração total: {duration}")
            return True
        elif 'error' in data:
            error_msg = data.get('error_description', data.get('error', 'Erro desconhecido'))
            print(f"[API] ❌ Erro na resposta: {error_msg}")
            return False
        
        print("[API] ⚠ Resposta não contém 'result' ou 'error'")
        return False
        
    except Exception as e:
        print(f"[API] ❌ Erro ao fechar expediente: {e}")
        return False


def get_logged_user():
    """Obtém o nome do usuário logado no Windows"""
    try:
        users = psutil.users()
        if users:
            return users[0].name
    except:
        pass
    
    # Fallback: usar variável de ambiente
    try:
        return os.getenv('USERNAME') or os.getenv('USER')
    except:
        return "Usuário"
    
    return "Usuário"

def get_user_email(username):
    """Tenta obter o email do usuário de várias fontes"""
    email = None
    
    # Método 1: Tentar obter do Active Directory
    try:
        import win32net
        import win32netcon
        
        # Obter informações do usuário do AD
        user_info = win32net.NetUserGetInfo(None, username, 2)
        if user_info:
            # Tentar obter email de diferentes campos
            email = user_info.get('usr_comment') or user_info.get('comment') or None
            if email and '@' in email:
                return email
    except:
        pass
    
    # Método 2: Tentar obter do registro do Windows
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            f"SOFTWARE\\Microsoft\\IdentityStore\\Cache\\{username}"
        )
        try:
            email = winreg.QueryValueEx(key, "Email")[0]
            if email:
                return email
        except:
            pass
        finally:
            winreg.CloseKey(key)
    except:
        pass
    
    # Método 3: Tentar obter de variáveis de ambiente
    try:
        email = os.getenv('USER_EMAIL') or os.getenv('EMAIL')
        if email and '@' in email:
            return email
    except:
        pass
    
    # Método 4: Construir email padrão baseado no nome de usuário
    # Usar domínio fixo grupohi.com.br
    try:
        return f"{username.lower()}@grupohi.com.br"
    except:
        pass
    
    # Fallback: retornar None se não conseguir obter
    return None

def get_user_info():
    """Obtém informações completas do usuário logado"""
    username = get_logged_user()
    email = get_user_email(username)
    
    return {
        'username': username,
        'email': email,
        'display_name': username.replace('.', ' ').replace('_', ' ').title()
    }

def set_dpi_awareness():
    """Configura DPI awareness para obter coordenadas reais dos monitores"""
    try:
        import ctypes
        # Tentar SetProcessDpiAwareness (Windows 8.1+)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except:
            # Fallback para SetProcessDPIAware (Windows Vista+)
            ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

def get_all_monitors():
    """Obtém informações de todos os monitores conectados"""
    monitors = []
    
    # Configurar DPI awareness primeiro
    set_dpi_awareness()
    
    # Método 1: Usar win32api.EnumDisplayMonitors
    try:
        def callback(hmonitor, hdc, rect, data):
            monitors.append({
                'x': rect[0],
                'y': rect[1],
                'width': rect[2] - rect[0],
                'height': rect[3] - rect[1]
            })
            return True
        
        win32api.EnumDisplayMonitors(None, None, callback, None)
        if len(monitors) > 0:
            print(f"[DEBUG] Método win32api.EnumDisplayMonitors encontrou {len(monitors)} monitor(es)")
            return monitors
    except Exception as e:
        print(f"[DEBUG] Erro no EnumDisplayMonitors: {e}")
    
    # Método 2: Usar ctypes diretamente
    try:
        import ctypes
        from ctypes import wintypes
        
        monitors = []
        
        # Definir o callback
        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.POINTER(wintypes.RECT),
            ctypes.c_double
        )
        
        def callback_ctypes(hmonitor, hdc, lprect, lparam):
            rect = lprect.contents
            monitors.append({
                'x': rect.left,
                'y': rect.top,
                'width': rect.right - rect.left,
                'height': rect.bottom - rect.top
            })
            return True
        
        callback_func = MONITORENUMPROC(callback_ctypes)
        ctypes.windll.user32.EnumDisplayMonitors(None, None, callback_func, 0)
        
        if len(monitors) > 0:
            print(f"[DEBUG] Método ctypes.EnumDisplayMonitors encontrou {len(monitors)} monitor(es)")
            return monitors
    except Exception as e:
        print(f"[DEBUG] Erro no ctypes EnumDisplayMonitors: {e}")
    
    # Método 3: Usar EnumDisplayDevices + EnumDisplaySettings
    try:
        import ctypes
        from ctypes import wintypes
        
        monitors = []
        
        class DISPLAY_DEVICE(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('DeviceName', wintypes.WCHAR * 32),
                ('DeviceString', wintypes.WCHAR * 128),
                ('StateFlags', wintypes.DWORD),
                ('DeviceID', wintypes.WCHAR * 128),
                ('DeviceKey', wintypes.WCHAR * 128),
            ]
        
        class DEVMODE(ctypes.Structure):
            _fields_ = [
                ('dmDeviceName', wintypes.WCHAR * 32),
                ('dmSpecVersion', wintypes.WORD),
                ('dmDriverVersion', wintypes.WORD),
                ('dmSize', wintypes.WORD),
                ('dmDriverExtra', wintypes.WORD),
                ('dmFields', wintypes.DWORD),
                ('dmPositionX', wintypes.LONG),
                ('dmPositionY', wintypes.LONG),
                ('dmDisplayOrientation', wintypes.DWORD),
                ('dmDisplayFixedOutput', wintypes.DWORD),
                ('dmColor', wintypes.SHORT),
                ('dmDuplex', wintypes.SHORT),
                ('dmYResolution', wintypes.SHORT),
                ('dmTTOption', wintypes.SHORT),
                ('dmCollate', wintypes.SHORT),
                ('dmFormName', wintypes.WCHAR * 32),
                ('dmLogPixels', wintypes.WORD),
                ('dmBitsPerPel', wintypes.DWORD),
                ('dmPelsWidth', wintypes.DWORD),
                ('dmPelsHeight', wintypes.DWORD),
                ('dmDisplayFlags', wintypes.DWORD),
                ('dmDisplayFrequency', wintypes.DWORD),
            ]
        
        DISPLAY_DEVICE_ACTIVE = 0x00000001
        ENUM_CURRENT_SETTINGS = -1
        
        i = 0
        while True:
            device = DISPLAY_DEVICE()
            device.cb = ctypes.sizeof(device)
            
            if not ctypes.windll.user32.EnumDisplayDevicesW(None, i, ctypes.byref(device), 0):
                break
            
            if device.StateFlags & DISPLAY_DEVICE_ACTIVE:
                devmode = DEVMODE()
                devmode.dmSize = ctypes.sizeof(devmode)
                
                if ctypes.windll.user32.EnumDisplaySettingsW(device.DeviceName, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode)):
                        monitors.append({
                        'x': devmode.dmPositionX,
                        'y': devmode.dmPositionY,
                        'width': devmode.dmPelsWidth,
                        'height': devmode.dmPelsHeight
                    })
            i += 1
        
        if len(monitors) > 0:
            print(f"[DEBUG] Método EnumDisplayDevices encontrou {len(monitors)} monitor(es)")
            return monitors
    except Exception as e:
        print(f"[DEBUG] Erro no EnumDisplayDevices: {e}")
    
    # Fallback final: usar tkinter para pegar ao menos o monitor principal
    try:
        root = tk.Tk()
        monitors = [{
            'x': 0,
            'y': 0,
            'width': root.winfo_screenwidth(),
            'height': root.winfo_screenheight()
        }]
        root.destroy()
        print(f"[DEBUG] Fallback tkinter: usando monitor principal")
    except:
        monitors = [{'x': 0, 'y': 0, 'width': 1920, 'height': 1080}]
        print(f"[DEBUG] Fallback padrão: 1920x1080")
    
    return monitors


class LockScreen:
    """Tela de bloqueio estilo Windows para um monitor específico"""
    
    def __init__(self, monitor_info, shared_state):
        self.monitor_info = monitor_info
        self.shared_state = shared_state  # Estado compartilhado entre todas as janelas
        self.root = None
        self.status_label = None
        self.start_button = None
        
        # Criar janela (Tk para primeira, Toplevel para outras)
        if not hasattr(tk, '_default_root') or tk._default_root is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel()
        
        # Configurar janela
        self.setup_window()
        
        # Criar interface
        self.create_ui()
        
        # Configurar eventos
        self.setup_events()
    
    def setup_window(self):
        """Configura a janela para tela de bloqueio"""
        # Usar informações do monitor específico
        self.screen_width = self.monitor_info['width']
        self.screen_height = self.monitor_info['height']
        monitor_x = self.monitor_info['x']
        monitor_y = self.monitor_info['y']
        
        # Configurar janela
        self.root.title("HiProd Agent - Tela de Bloqueio")
        
        # Remover bordas e barra de título ANTES de definir geometria
        self.root.overrideredirect(True)
        
        # NÃO usar -fullscreen pois ele ignora a posição e vai sempre pro monitor principal
        # Em vez disso, usar geometria manual para cobrir o monitor específico
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+{monitor_x}+{monitor_y}")
        
        # Manter sempre no topo
        self.root.attributes('-topmost', True)
        
        # Cor de fundo escura
        self.root.configure(bg='#0d1117')
        
        # Forçar atualização da janela para garantir que o winfo_id() funcione
        self.root.update_idletasks()
        
        # Tentar tornar a janela sempre no topo usando Win32 API
        try:
            hwnd = self.root.winfo_id()
            # Usar HWND_TOPMOST para manter sempre no topo
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                monitor_x, monitor_y, self.screen_width, self.screen_height,
                win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED
            )
            # Armazenar o hwnd para uso posterior
            self.hwnd = hwnd
        except Exception as e:
            self.hwnd = None
            print(f"[WARN] Não foi possível configurar janela via Win32: {e}")
        
        # Iniciar loop de manutenção para manter janela no topo
        self.start_topmost_loop()
    
    def create_ui(self):
        """Cria a interface da tela de bloqueio"""
        # Obter informações do usuário
        user_info = get_user_info()
        
        # Frame principal centralizado
        main_frame = tk.Frame(self.root, bg='#0d1117')
        main_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Mensagem de bem-vindo
        welcome_label = tk.Label(
            main_frame,
            text="Bem-vindo",
            font=('Segoe UI', 24),
            fg='#8b949e',
            bg='#0d1117'
        )
        welcome_label.pack(pady=(0, 20))
        
        # Nome do usuário
        username_label = tk.Label(
            main_frame,
            text=user_info['display_name'],
            font=('Segoe UI', 42, 'bold'),
            fg='#ffffff',
            bg='#0d1117'
        )
        username_label.pack(pady=(0, 10))
        
        # Email do usuário (se disponível)
        if user_info['email']:
            email_label = tk.Label(
                main_frame,
                text=user_info['email'],
                font=('Segoe UI', 16),
                fg='#58a6ff',
                bg='#0d1117'
            )
            email_label.pack(pady=(0, 40))
        else:
            # Mostrar nome de usuário se não tiver email
            username_display_label = tk.Label(
                main_frame,
                text=f"@{user_info['username']}",
                font=('Segoe UI', 16),
                fg='#8b949e',
                bg='#0d1117'
            )
            username_display_label.pack(pady=(0, 40))
        
        # Informação sobre controle de acesso
        access_info_label = tk.Label(
            main_frame,
            text="Sistema de Controle de Acesso",
            font=('Segoe UI', 18, 'bold'),
            fg='#f85149',
            bg='#0d1117'
        )
        access_info_label.pack(pady=(0, 10))
        
        access_desc_label = tk.Label(
            main_frame,
            text="Este sistema monitora atividades para controle de acesso e produtividade",
            font=('Segoe UI', 12),
            fg='#6e7681',
            bg='#0d1117',
            wraplength=600,
            justify='center'
        )
        access_desc_label.pack(pady=(0, 50))
        
        # Logo/Título (menor, abaixo das informações do usuário)
        title_label = tk.Label(
            main_frame,
            text="HiProd Agent",
            font=('Segoe UI', 32, 'bold'),
            fg='#58a6ff',
            bg='#0d1117'
        )
        title_label.pack(pady=(0, 30))
        
        # Verificar se precisa de aprovação
        needs_approval = self.shared_state.get('needs_approval', False)
        timeman_info = self.shared_state.get('timeman_info')
        approval_requested = self.shared_state.get('approval_requested', False)
        is_machine_unlock = self.shared_state.get('is_machine_unlock', False)
        
        # PRIMEIRO: verificar se é tela de bloqueio pós-expediente (com botões de ação)
        if is_machine_unlock:
            # Tela de bloqueio simplificada - apenas botões de ação
            self.status_label = tk.Label(
                main_frame,
                text="🔒 Tempo Esgotado",
                font=('Segoe UI', 24, 'bold'),
                fg='#f85149',
                bg='#0d1117'
            )
            self.status_label.pack(pady=(0, 40))
            
            # Buscar coordenador
            user_id = self.shared_state.get('bitrix_user_id')
            manager_info = get_user_manager(user_id) if user_id else None
            manager_name = manager_info.get('manager_name', 'Coordenador') if manager_info else 'Coordenador'
            manager_id = manager_info.get('manager_id') if manager_info else None
            
            # Função para solicitar mais tempo
            def request_more_time():
                if user_id:
                    reason = f"Solicitação de mais tempo. Enviada para {manager_name}."
                    result = request_manager_approval(user_id=user_id, reason=reason, manager_id=manager_id)
                    if result and result.get('success'):
                        show_windows_notification("HiProd", f"Liberado! {manager_name} notificado.", 5)
                        self.root.after(1000, self.release_machine_without_agent)
            
            # Botão de solicitar mais tempo
            request_btn = tk.Button(
                main_frame,
                text="📧 Solicitar Mais Tempo",
                font=('Segoe UI', 18, 'bold'),
                bg='#f59e0b',
                fg='#ffffff',
                activebackground='#d97706',
                relief='flat',
                padx=50,
                pady=18,
                cursor='hand2',
                command=request_more_time
            )
            request_btn.pack(pady=(0, 20), fill='x', padx=80)
            
            # Função para logout
            def logout_user():
                import subprocess
                subprocess.run(['shutdown', '/l'], shell=True)
            
            # Botão de sair do usuário
            logout_btn = tk.Button(
                main_frame,
                text="🚪 Sair do Usuário",
                font=('Segoe UI', 18, 'bold'),
                bg='#6366f1',
                fg='#ffffff',
                activebackground='#4f46e5',
                relief='flat',
                padx=50,
                pady=18,
                cursor='hand2',
                command=logout_user
            )
            logout_btn.pack(pady=(0, 20), fill='x', padx=80)
            
            # Função para desligar
            def shutdown_machine():
                import subprocess
                subprocess.run(['shutdown', '/s', '/t', '5', '/c', 'HiProd - Desligando'], shell=True)
            
            # Botão de desligar máquina
            shutdown_btn = tk.Button(
                main_frame,
                text="⏻ Desligar Máquina",
                font=('Segoe UI', 18, 'bold'),
                bg='#dc2626',
                fg='#ffffff',
                activebackground='#b91c1c',
                relief='flat',
                padx=50,
                pady=18,
                cursor='hand2',
                command=shutdown_machine
            )
            shutdown_btn.pack(pady=(0, 20), fill='x', padx=80)
            
            # Não precisa de botão start_button separado
            self.start_button = None
            
        elif needs_approval:
            # Mensagem de expediente já encerrado
            warning_label = tk.Label(
                main_frame,
                text="⚠️ Expediente Já Encerrado Hoje",
                font=('Segoe UI', 18, 'bold'),
                fg='#fbbf24',
                bg='#0d1117'
            )
            warning_label.pack(pady=(0, 10))
            
            if timeman_info:
                time_start = timeman_info.get('time_start', 'N/A')
                time_finish = timeman_info.get('time_finish', 'N/A')
                duration = timeman_info.get('duration', 'N/A')
                
                info_text = f"Horário: {time_start} - {time_finish}\nDuração: {duration}"
                info_label = tk.Label(
                    main_frame,
                    text=info_text,
                    font=('Segoe UI', 12),
                    fg='#8b949e',
                    bg='#0d1117',
                    justify='center'
                )
                info_label.pack(pady=(0, 20))
            
            # Status - Enviando notificação automaticamente
            self.status_label = tk.Label(
                main_frame,
                text="📧 Enviando notificação ao coordenador...",
                font=('Segoe UI', 14),
                fg='#58a6ff',
                bg='#0d1117'
            )
            self.status_label.pack(pady=(0, 15))
            
            # Frame para o contador
            countdown_frame = tk.Frame(main_frame, bg='#1a1a2e', padx=30, pady=20)
            countdown_frame.pack(pady=(0, 20))
            
            tk.Label(
                countdown_frame,
                text="⏱ Tempo de acesso concedido:",
                font=('Segoe UI', 12),
                fg='#8b949e',
                bg='#1a1a2e'
            ).pack()
            
            self.countdown_label = tk.Label(
                countdown_frame,
                text="01:00",
                font=('Segoe UI', 36, 'bold'),
                fg='#fbbf24',
                bg='#1a1a2e'
            )
            self.countdown_label.pack()
            
            self.alert_label = tk.Label(
                countdown_frame,
                text="⏰ Tempo de acesso (1 min teste)",
                font=('Segoe UI', 11),
                fg='#4ade80',
                bg='#1a1a2e'
            )
            self.alert_label.pack(pady=(5, 0))
            
            # Variável para contador - 1 minuto para teste (60 segundos)
            self.approval_countdown = [60]  # 1 minuto para teste
            
            # Variável para controlar notificações já enviadas
            self.notifications_sent = set()
            
            # Função para enviar notificação automaticamente
            def send_auto_notification():
                user_id = self.shared_state.get('bitrix_user_id')
                if user_id:
                    print("[INFO] Enviando notificação automática ao coordenador...")
                    manager_info = get_user_manager(user_id)
                    manager_name = manager_info.get('manager_name', 'Coordenador') if manager_info else 'Coordenador'
                    manager_id = manager_info.get('manager_id') if manager_info else None
                    
                    reason = f"Acesso automático fora do horário de expediente. O expediente já foi encerrado hoje. Usuário está usando a máquina por 30 minutos."
                    
                    result = request_manager_approval(
                        user_id=user_id,
                        reason=reason,
                        manager_id=manager_id
                    )
                    
                    if result and result.get('success'):
                        self.status_label.config(
                            text=f"✓ Notificação enviada ao {manager_name}!",
                            fg='#4ade80'
                        )
                        print(f"[INFO] ✓ Notificação enviada ao coordenador {manager_name}")
                        # Notificação Windows
                        show_windows_notification(
                            "HiProd - Liberação Automática",
                            f"Máquina liberada por 60 minutos. Coordenador {manager_name} foi notificado.",
                            duration=10
                        )
                    else:
                        self.status_label.config(
                            text="⚠️ Falha ao enviar notificação",
                            fg='#f59e0b'
                        )
                        print("[WARN] Falha ao enviar notificação automática")
                else:
                    print("[ERROR] USER_ID não encontrado para enviar notificação")
            
            # Função para atualizar contador e liberar máquina
            def update_approval_countdown():
                if self.approval_countdown[0] > 0:
                    minutes = self.approval_countdown[0] // 60
                    seconds = self.approval_countdown[0] % 60
                    self.countdown_label.config(text=f"{minutes:02d}:{seconds:02d}")
                    
                    # Alertas progressivos com notificações Windows
                    total = self.approval_countdown[0]
                    
                    # Notificações em momentos específicos
                    if total == 1500 and 'min25' not in self.notifications_sent:  # 25 min restantes
                        self.notifications_sent.add('min25')
                        show_windows_notification("HiProd - Alerta", "Restam 25 minutos de uso da máquina", 5)
                    elif total == 1200 and 'min20' not in self.notifications_sent:  # 20 min restantes
                        self.notifications_sent.add('min20')
                        show_windows_notification("HiProd - Alerta", "Restam 20 minutos de uso da máquina", 5)
                    elif total == 900 and 'min15' not in self.notifications_sent:  # 15 min restantes
                        self.notifications_sent.add('min15')
                        show_windows_notification("HiProd - Atenção", "Restam 15 minutos de uso da máquina", 5)
                    elif total == 600 and 'min10' not in self.notifications_sent:  # 10 min restantes
                        self.notifications_sent.add('min10')
                        show_windows_notification("HiProd - Atenção", "Restam apenas 10 minutos!", 5)
                        self.alert_label.config(text="⚠️ Restam 10 minutos", fg='#f59e0b')
                    elif total == 300 and 'min5' not in self.notifications_sent:  # 5 min restantes
                        self.notifications_sent.add('min5')
                        show_windows_notification("HiProd - URGENTE", "Restam apenas 5 minutos! Máquina será bloqueada em breve.", 5)
                        self.alert_label.config(text="🔶 Restam 5 minutos!", fg='#f59e0b')
                        self.countdown_label.config(fg='#f59e0b')
                    elif total == 120 and 'min2' not in self.notifications_sent:  # 2 min restantes
                        self.notifications_sent.add('min2')
                        show_windows_notification("HiProd - URGENTE", "Restam apenas 2 minutos!", 5)
                        self.alert_label.config(text="🔴 Restam 2 minutos!", fg='#f85149')
                        self.countdown_label.config(fg='#f85149')
                    elif total == 60 and 'min1' not in self.notifications_sent:  # 1 min restante
                        self.notifications_sent.add('min1')
                        show_windows_notification("HiProd - BLOQUEIO IMINENTE", "Restam apenas 60 segundos!", 5)
                        self.alert_label.config(text="🔴 Último minuto!", fg='#f85149')
                    elif total <= 10:
                        self.alert_label.config(text="🔴 Bloqueio iminente!", fg='#f85149')
                    elif total > 600:
                        self.alert_label.config(text="⏰ Tempo de acesso pós-expediente", fg='#4ade80')
                    
                    self.approval_countdown[0] -= 1
                    self.root.after(1000, update_approval_countdown)
                else:
                    # Tempo acabou - mostrar que pode clicar para acessar
                    self.countdown_label.config(text="00:00", fg='#f85149')
                    self.alert_label.config(
                        text="⏳ Clique no botão para acessar",
                        fg='#fbbf24',
                        font=('Segoe UI', 12, 'bold')
                    )
                    show_windows_notification("HiProd", "Tempo disponível. Clique para acessar a máquina.", 5)
            
            # Iniciar contador e enviar notificação automaticamente
            self.root.after(500, send_auto_notification)  # Enviar notificação após 0.5s
            self.root.after(1000, update_approval_countdown)  # Iniciar contador após 1s
            
            # Informações adicionais
            info_label = tk.Label(
                main_frame,
                text="A máquina será liberada por 30 minutos.\nO agente NÃO enviará informações para a API.",
                font=('Segoe UI', 11),
                fg='#6e7681',
                bg='#0d1117',
                wraplength=600,
                justify='center'
            )
            info_label.pack(pady=(10, 0))
            
            # Botão de Acessar Máquina (não iniciar expediente)
            self.start_button = tk.Button(
                main_frame,
                text="🖥️ Acessar Máquina (30 min)",
                font=('Segoe UI', 18, 'bold'),
                bg='#f59e0b',
                fg='#ffffff',
                activebackground='#d97706',
                activeforeground='#ffffff',
                relief='flat',
                padx=50,
                pady=20,
                cursor='hand2',
                command=self.release_machine_without_agent,
                bd=0,
                highlightthickness=0
            )
            self.start_button.pack(pady=(20, 20))
            
            # Hover effect
            def on_enter_access(e):
                self.start_button.config(bg='#d97706')
            def on_leave_access(e):
                self.start_button.config(bg='#f59e0b')
            self.start_button.bind('<Enter>', on_enter_access)
            self.start_button.bind('<Leave>', on_leave_access)
        else:
                # Status do expediente normal
                self.status_label = tk.Label(
                    main_frame,
                    text="⏸️ Expediente Não Iniciado",
                    font=('Segoe UI', 16),
                    fg='#f85149',
                    bg='#0d1117'
                )
                self.status_label.pack(pady=(0, 50))
                
                # Botão de iniciar
                self.start_button = tk.Button(
                    main_frame,
                    text="▶ Iniciar Expediente",
                    font=('Segoe UI', 20, 'bold'),
                    bg='#238636',
                    fg='#ffffff',
                    activebackground='#2ea043',
                    activeforeground='#ffffff',
                    relief='flat',
                    padx=50,
                    pady=25,
                    cursor='hand2',
                    command=self.toggle_agent,
                    bd=0,
                    highlightthickness=0
                )
                self.start_button.pack(pady=(0, 40))
                
                # Adicionar efeito hover
                def on_enter(e):
                    if self.shared_state['agent_running']:
                        self.start_button.config(bg='#f85149')
                    else:
                        self.start_button.config(bg='#2ea043')
                def on_leave(e):
                    if self.shared_state['agent_running']:
                        self.start_button.config(bg='#da3633')
                    else:
                        self.start_button.config(bg='#238636')
                self.start_button.bind('<Enter>', on_enter)
                self.start_button.bind('<Leave>', on_leave)
                
                # Informações adicionais
                info_label = tk.Label(
                    main_frame,
                    text="Clique em 'Iniciar Expediente' para liberar sua estação de trabalho",
                    font=('Segoe UI', 12),
                    fg='#6e7681',
                    bg='#0d1117'
                )
                info_label.pack(pady=(30, 0))
        
    
    def start_topmost_loop(self):
        """Inicia um loop para manter a janela sempre no topo (apenas se bloqueio ativo)"""
        def keep_topmost():
            try:
                if not self.root.winfo_exists():
                    return
                
                # Só manter no topo se o bloqueio estiver ativo
                if not self.shared_state.get('lock_screen_active', True):
                    # Reagendar para verificar novamente depois
                    self.root.after(500, keep_topmost)
                    return
                
                # Reforçar topmost via tkinter
                self.root.attributes('-topmost', True)
                self.root.lift()
                
                # Reforçar via Win32 API
                if hasattr(self, 'hwnd') and self.hwnd:
                    try:
                        win32gui.SetWindowPos(
                            self.hwnd,
                            win32con.HWND_TOPMOST,
                            self.monitor_info['x'], 
                            self.monitor_info['y'], 
                            self.screen_width, 
                            self.screen_height,
                            win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
                        )
                        # Garantir que a janela está visível
                        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
                    except:
                        pass
                
                # Reagendar a cada 500ms
                self.root.after(500, keep_topmost)
            except:
                pass
        
        # Iniciar o loop após um pequeno delay
        self.root.after(100, keep_topmost)
    
    def hide_all_lock_screens(self):
        """Esconde todas as telas de bloqueio e mostra botão flutuante"""
        self.shared_state['lock_screen_active'] = False
        
        for window in self.shared_state.get('windows', []):
            try:
                # Remover topmost
                window.root.attributes('-topmost', False)
                # Minimizar a janela
                window.root.withdraw()
                
                # Via Win32 API, minimizar
                if hasattr(window, 'hwnd') and window.hwnd:
                    try:
                        win32gui.ShowWindow(window.hwnd, win32con.SW_HIDE)
                    except:
                        pass
            except:
                pass
        
        print("[INFO] Telas de bloqueio ocultadas - Expediente iniciado")
        
        # Criar ou reutilizar botão flutuante
        user_id = self.shared_state.get('bitrix_user_id')
        
        # Verificar se já existe um botão no shared_state
        existing_button = self.shared_state.get('floating_button')
        if existing_button and hasattr(existing_button, 'root') and existing_button.root:
            try:
                existing_button.root.winfo_exists()
                print("[INFO] Botão flutuante já existe no shared_state, reutilizando...")
                return  # Já existe, não criar novo
            except:
                pass  # Botão inválido, criar novo
        
        print("[INFO] Criando botão flutuante do HiProd Agent...")
        self.shared_state['floating_button'] = create_floating_button(user_id=user_id)
        print("[INFO] ✓ Botão flutuante criado!")
    
    def show_all_lock_screens(self):
        """Mostra todas as telas de bloqueio novamente"""
        self.shared_state['lock_screen_active'] = True
        
        # Fechar popup do botão flutuante se estiver aberto (mas manter o botão)
        floating_button = self.shared_state.get('floating_button')
        if floating_button and hasattr(floating_button, 'popup_visible') and floating_button.popup_visible:
            try:
                floating_button._close_popup()
            except:
                pass
        
        for window in self.shared_state.get('windows', []):
            try:
                # Mostrar a janela
                window.root.deiconify()
                window.root.attributes('-topmost', True)
                window.root.lift()
                window.root.focus_force()
                
                # Via Win32 API, mostrar
                if hasattr(window, 'hwnd') and window.hwnd:
                    try:
                        win32gui.SetWindowPos(
                            window.hwnd,
                            win32con.HWND_TOPMOST,
                            window.monitor_info['x'],
                            window.monitor_info['y'],
                            window.screen_width,
                            window.screen_height,
                            win32con.SWP_SHOWWINDOW
                        )
                        win32gui.ShowWindow(window.hwnd, win32con.SW_SHOW)
                    except:
                        pass
            except:
                pass
        
        print("[INFO] Telas de bloqueio restauradas - Expediente encerrado")
    
    def release_machine_without_agent(self):
        """Libera a máquina SEM iniciar o agente (não envia dados para API)"""
        print("[INFO] Liberando máquina SEM agente (não envia dados para API)...")
        
        self.shared_state['lock_screen_active'] = False
        self.shared_state['agent_running'] = False  # Garantir que agente não está rodando
        
        for window in self.shared_state.get('windows', []):
            try:
                # Remover topmost
                window.root.attributes('-topmost', False)
                # Minimizar a janela
                window.root.withdraw()
                
                # Via Win32 API, minimizar
                if hasattr(window, 'hwnd') and window.hwnd:
                    try:
                        win32gui.ShowWindow(window.hwnd, win32con.SW_HIDE)
                    except:
                        pass
            except:
                pass
        
        print("[INFO] ✓ Telas de bloqueio ocultadas - Máquina liberada SEM agente")
        print("[INFO] ⚠ O agente NÃO está enviando informações para a API")
        
        # Criar popup flutuante com contador de tempo pós-expediente
        user_id = self.shared_state.get('bitrix_user_id')
        self._create_post_workday_popup(user_id)
    
    def _create_post_workday_popup(self, user_id):
        """Cria popup flutuante com contador de tempo pós-expediente"""
        print("[INFO] Criando popup de tempo pós-expediente...")
        
        # Criar janela flutuante
        popup_root = tk.Toplevel()
        popup_root.title("HiProd - Acesso Pós-Expediente")
        popup_root.overrideredirect(True)
        popup_root.attributes('-topmost', True)
        popup_root.attributes('-alpha', 0.95)
        
        # Tamanho e posição
        popup_width = 280
        popup_height = 180
        screen_width = popup_root.winfo_screenwidth()
        x = screen_width - popup_width - 20
        y = 100
        popup_root.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        
        # Frame principal
        main_frame = tk.Frame(popup_root, bg='#1a1a2e', padx=15, pady=12)
        main_frame.pack(fill='both', expand=True)
        
        # Título
        tk.Label(
            main_frame,
            text="⏰ Acesso Pós-Expediente",
            font=('Segoe UI', 11, 'bold'),
            fg='#f59e0b',
            bg='#1a1a2e'
        ).pack(pady=(0, 8))
        
        # Frame do contador
        countdown_frame = tk.Frame(main_frame, bg='#252542', padx=15, pady=10)
        countdown_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(
            countdown_frame,
            text="Tempo restante:",
            font=('Segoe UI', 9),
            fg='#8b8b9e',
            bg='#252542'
        ).pack()
        
        countdown_label = tk.Label(
            countdown_frame,
            text="01:00:00",
            font=('Segoe UI', 28, 'bold'),
            fg='#fbbf24',
            bg='#252542'
        )
        countdown_label.pack()
        
        alert_label = tk.Label(
            countdown_frame,
            text="⏰ 1 hora de acesso",
            font=('Segoe UI', 9),
            fg='#4ade80',
            bg='#252542'
        )
        alert_label.pack()
        
        # Variáveis para controle
        post_countdown = [3600]  # 1 hora (3600 segundos)
        notifications_sent = set()
        
        def update_post_countdown():
            if post_countdown[0] > 0:
                total_seconds = post_countdown[0]
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                # Mostrar formato HH:MM:SS quando tiver horas, senão MM:SS
                if hours > 0:
                    countdown_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                else:
                    countdown_label.config(text=f"{minutes:02d}:{seconds:02d}")
                
                # Alertas e notificações
                total = post_countdown[0]
                if total == 1500 and 'min25' not in notifications_sent:
                    notifications_sent.add('min25')
                    show_windows_notification("HiProd", "Restam 25 minutos de acesso", 5)
                elif total == 1200 and 'min20' not in notifications_sent:
                    notifications_sent.add('min20')
                    show_windows_notification("HiProd", "Restam 20 minutos de acesso", 5)
                elif total == 900 and 'min15' not in notifications_sent:
                    notifications_sent.add('min15')
                    show_windows_notification("HiProd - Atenção", "Restam 15 minutos de acesso", 5)
                    alert_label.config(text="⚠️ 15 min restantes", fg='#fbbf24')
                elif total == 600 and 'min10' not in notifications_sent:
                    notifications_sent.add('min10')
                    show_windows_notification("HiProd - Atenção", "Restam 10 minutos!", 5)
                    alert_label.config(text="⚠️ 10 min restantes", fg='#f59e0b')
                    countdown_label.config(fg='#f59e0b')
                elif total == 300 and 'min5' not in notifications_sent:
                    notifications_sent.add('min5')
                    show_windows_notification("HiProd - URGENTE", "Restam 5 minutos! Máquina será bloqueada.", 5)
                    alert_label.config(text="🔶 5 min restantes!", fg='#f59e0b')
                elif total == 120 and 'min2' not in notifications_sent:
                    notifications_sent.add('min2')
                    show_windows_notification("HiProd - URGENTE", "Restam 2 minutos!", 5)
                    alert_label.config(text="🔴 2 min restantes!", fg='#f85149')
                    countdown_label.config(fg='#f85149')
                elif total == 60 and 'min1' not in notifications_sent:
                    notifications_sent.add('min1')
                    show_windows_notification("HiProd - BLOQUEIO IMINENTE", "Último minuto!", 5)
                    alert_label.config(text="🔴 Último minuto!", fg='#f85149')
                elif total <= 10:
                    alert_label.config(text="🔴 Bloqueio iminente!", fg='#f85149')
                
                post_countdown[0] -= 1
                popup_root.after(1000, update_post_countdown)
            else:
                # Tempo acabou - bloquear máquina
                countdown_label.config(text="00:00:00", fg='#f85149')
                alert_label.config(text="🔒 Bloqueando...", fg='#f85149')
                show_windows_notification("HiProd - Bloqueio", "Tempo esgotado! Máquina será bloqueada.", 5)
                
                # Bloquear após 2 segundos
                popup_root.after(2000, lambda: self._block_after_post_workday(popup_root))
        
        # Botão de solicitar mais tempo
        def request_more_time():
            manager_info = get_user_manager(user_id) if user_id else None
            manager_name = manager_info.get('manager_name', 'Coordenador') if manager_info else 'Coordenador'
            manager_id = manager_info.get('manager_id') if manager_info else None
            
            reason = f"Solicitação de mais 30 minutos de acesso pós-expediente."
            result = request_manager_approval(user_id=user_id, reason=reason, manager_id=manager_id)
            
            if result and result.get('success'):
                post_countdown[0] = 1800  # Reset para 30 minutos (1800 segundos)
                notifications_sent.clear()
                countdown_label.config(text="00:30:00", fg='#fbbf24')
                alert_label.config(text=f"✓ +30 min! {manager_name} notificado", fg='#4ade80')
                show_windows_notification("HiProd", f"Mais 30 minutos concedidos. {manager_name} notificado.", 10)
            else:
                alert_label.config(text="⚠️ Erro ao solicitar", fg='#f59e0b')
        
        request_btn = tk.Button(
            main_frame,
            text="📧 +30 min",
            font=('Segoe UI', 10, 'bold'),
            bg='#f59e0b',
            fg='white',
            activebackground='#d97706',
            relief='flat',
            cursor='hand2',
            command=request_more_time,
            pady=5
        )
        request_btn.pack(fill='x')
        
        # Hover effect
        def on_enter(e):
            request_btn.config(bg='#d97706')
        def on_leave(e):
            request_btn.config(bg='#f59e0b')
        request_btn.bind('<Enter>', on_enter)
        request_btn.bind('<Leave>', on_leave)
        
        # Permitir arrastar a janela
        def start_drag(event):
            popup_root._drag_x = event.x
            popup_root._drag_y = event.y
        def do_drag(event):
            x = popup_root.winfo_x() + event.x - popup_root._drag_x
            y = popup_root.winfo_y() + event.y - popup_root._drag_y
            popup_root.geometry(f"+{x}+{y}")
        main_frame.bind('<Button-1>', start_drag)
        main_frame.bind('<B1-Motion>', do_drag)
        
        # Iniciar contador
        popup_root.after(1000, update_post_countdown)
        
        print("[INFO] ✓ Popup de tempo pós-expediente criado!")
    
    def _block_after_post_workday(self, popup):
        """Bloqueia a máquina após tempo pós-expediente"""
        print("[INFO] Bloqueando máquina após tempo pós-expediente...")
        
        # Fechar popup
        try:
            popup.destroy()
        except:
            pass
        
        # Mostrar as telas de bloqueio novamente
        self.shared_state['lock_screen_active'] = True
        self.shared_state['is_machine_unlock'] = True  # Manter como liberação de máquina
        
        for window in self.shared_state.get('windows', []):
            try:
                # Mostrar a janela
                window.root.deiconify()
                window.root.attributes('-topmost', True)
                window.root.lift()
                window.root.focus_force()
                
                # Via Win32 API, mostrar
                if hasattr(window, 'hwnd') and window.hwnd:
                    try:
                        win32gui.SetWindowPos(
                            window.hwnd,
                            win32con.HWND_TOPMOST,
                            window.monitor_info['x'],
                            window.monitor_info['y'],
                            window.screen_width,
                            window.screen_height,
                            win32con.SWP_SHOWWINDOW
                        )
                        win32gui.ShowWindow(window.hwnd, win32con.SW_SHOW)
                    except:
                        pass
            except Exception as e:
                print(f"[ERROR] Erro ao mostrar janela: {e}")
        
        print("[INFO] Telas de bloqueio restauradas - Tempo pós-expediente esgotado")
    
    def setup_events(self):
        """Configura eventos da janela"""
        # Bloquear Alt+Tab, Win+Tab, ESC, Alt+F4, etc.
        self.root.bind('<Alt-Tab>', lambda e: 'break')
        self.root.bind('<Alt-F4>', lambda e: 'break')
        self.root.bind('<Escape>', lambda e: 'break')
        self.root.bind('<F4>', lambda e: 'break')
        self.root.bind('<F11>', lambda e: 'break')
        
        # Bloquear tentativas de minimizar ou fechar
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Manter foco quando perder
        self.root.bind('<FocusOut>', lambda e: self.root.after(100, self.root.focus_force))
        
        # Focar na janela
        self.root.focus_force()
    
    def toggle_agent(self):
        """Inicia ou para o agent"""
        if not self.shared_state['agent_running']:
            self.start_agent()
        else:
            self.stop_agent()
    
    def request_approval(self):
        """Solicita liberação ao coordenador"""
        user_id = self.shared_state.get('bitrix_user_id')
        if not user_id:
            print("[ERROR] USER_ID não encontrado")
            return
        
        # Atualizar status visual
        self.status_label.config(
            text="⏳ Enviando solicitação...",
            fg='#f0ad4e'
        )
        self.root.update()
        
        # Solicitar aprovação
        result = request_manager_approval(
            user_id=user_id,
            reason="Acesso adicional após expediente encerrado"
        )
        
        if result and result.get('success'):
            # Marcar como solicitado
            self.shared_state['approval_requested'] = True
            self.shared_state['approval_status'] = 'pending'
            
            # Atualizar UI
            self.status_label.config(
                text="📧 Solicitação Enviada ao Coordenador",
                fg='#58a6ff'
            )
            
            # Atualizar botão
            self.start_button.config(
                text="🔄 Verificar Status",
                bg='#58a6ff',
                activebackground='#3b82f6',
                command=self.check_approval_status
            )
            
            # Atualizar hover
            def on_enter(e):
                self.start_button.config(bg='#3b82f6')
            def on_leave(e):
                self.start_button.config(bg='#58a6ff')
            self.start_button.unbind('<Enter>')
            self.start_button.unbind('<Leave>')
            self.start_button.bind('<Enter>', on_enter)
            self.start_button.bind('<Leave>', on_leave)
            
            # Atualizar todas as janelas
            self.update_all_windows_ui()
            
            print("[INFO] ✓ Solicitação enviada com sucesso!")
        else:
            error_msg = result.get('message', 'Erro desconhecido') if result else 'Erro ao enviar solicitação'
            self.status_label.config(
                text=f"❌ Erro: {error_msg[:40]}",
                fg='#f85149'
            )
            print(f"[ERROR] Falha ao solicitar aprovação: {error_msg}")
    
    def check_approval_status(self):
        """Verifica o status da aprovação"""
        user_id = self.shared_state.get('bitrix_user_id')
        
        # Atualizar status visual
        self.status_label.config(
            text="⏳ Verificando status...",
            fg='#f0ad4e'
        )
        self.root.update()
        
        # Verificar status (por enquanto, sempre retorna False - não implementado completamente)
        approved = check_approval_status(user_id)
        
        if approved:
            # Aprovação concedida - iniciar agent
            self.shared_state['approval_status'] = 'approved'
            self.status_label.config(
                text="✅ Acesso Liberado!",
                fg='#4ade80'
            )
            
            # Aguardar um pouco e iniciar
            self.root.after(2000, self.start_agent)
        else:
            # Ainda pendente
            self.status_label.config(
                text="📧 Aguardando Aprovação...",
                fg='#58a6ff'
            )
            print("[INFO] Aprovação ainda pendente")
    
    def start_agent(self):
        """Inicia o agent em uma thread separada e libera a estação"""
        try:
            # Atualizar status visual
            self.status_label.config(
                text="⏳ Iniciando expediente...",
                fg='#f0ad4e'
            )
            self.root.update()
            
            # 1. Obter USER_ID do Bitrix24 (do shared_state ou buscar)
            user_id = self.shared_state.get('bitrix_user_id')
            if not user_id:
                print("[WARN] USER_ID não encontrado no shared_state, buscando novamente...")
                user_id = get_current_bitrix_user_id()
            
            print(f"[INFO] USER_ID para abertura: {user_id}")
            
            # 2. Verificar status atual antes de tentar abrir
            timeman_info = check_timeman_status(user_id)
            status = timeman_info.get('status')
            can_open = timeman_info.get('can_open', True)
            worked_today = timeman_info.get('worked_today', False)
            time_start = timeman_info.get('time_start')
            
            print(f"[INFO] Status do expediente: {status}")
            print(f"[INFO] Pode abrir: {can_open}")
            print(f"[INFO] Trabalhou hoje: {worked_today}")
            print(f"[INFO] TIME_START: {time_start}")
            
            # 3. Abrir o expediente no Bitrix24 via API (apenas se permitido)
            expediente_aberto = False
            if status == 'OPENED':
                print("[INFO] ✓ Expediente já está aberto no Bitrix24!")
                expediente_aberto = True
            elif worked_today and not can_open:
                print("[INFO] ⚠ Expediente já foi trabalhado hoje e não pode ser reaberto.")
                print(f"[INFO] Horário trabalhado: {time_start} - {timeman_info.get('time_finish')}")
                print("[WARN] Expediente já finalizado. Agente de atividades não será iniciado.")
                expediente_aberto = False
            elif can_open:
                # Se pode abrir, tentar abrir (pode ser novo dia ou expediente não iniciado)
                if status == 'CLOSED' and time_start:
                    # Verificar se TIME_START é do dia anterior (novo dia)
                    try:
                        start_datetime = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
                        today = datetime.now().date()
                        start_date = start_datetime.date()
                        is_new_day = start_date < today
                        
                        if is_new_day:
                            print(f"[INFO] 📅 Detectado novo dia! TIME_START ({start_date}) é anterior a hoje ({today})")
                            print("[INFO] Abrindo novo expediente no Bitrix24...")
                        else:
                            print("[INFO] Abrindo expediente no Bitrix24...")
                    except Exception as e:
                        print(f"[WARN] Erro ao verificar data: {e}")
                        print("[INFO] Abrindo expediente no Bitrix24...")
                else:
                    print("[INFO] Abrindo expediente no Bitrix24...")
                
                if open_timeman(user_id=user_id, report="Início do expediente via HiProd Agent"):
                    print("[INFO] ✓ Expediente aberto com sucesso no Bitrix24!")
                    expediente_aberto = True
                else:
                    # Mesmo com erro na API, permitir continuar (pode estar offline)
                    print("[WARN] Não foi possível registrar abertura no Bitrix24, continuando...")
                    # Verificar novamente o status após tentar abrir
                    timeman_info_after = check_timeman_status(user_id)
                    if timeman_info_after.get('status') == 'OPENED':
                        expediente_aberto = True
                        print("[INFO] ✓ Expediente confirmado como aberto após verificação")
            else:
                print("[WARN] ⚠ Não é possível abrir expediente no momento.")
                print(f"[WARN] Status: {status}, can_open: {can_open}, worked_today: {worked_today}")
                expediente_aberto = False
            
            # 4. Só iniciar o agente se o expediente estiver aberto
            if not expediente_aberto:
                print("[WARN] ⚠ Expediente não está aberto. Agente de atividades NÃO será iniciado.")
                print("[INFO] Apenas liberando a máquina sem iniciar o agente de envio de dados.")
                # Atualizar UI para indicar que não há agente rodando
                self.status_label.config(
                    text="✅ Máquina Liberada\n(Agente não iniciado - expediente não aberto)",
                    fg='#f0ad4e'
                )
                # Esconder telas de bloqueio mesmo sem agente
                self.hide_all_lock_screens()
                return  # Não iniciar o agente
            
            # 5. Importar o agent apenas quando o expediente estiver aberto
            agent_module = import_agent_module()
            
            if agent_module is None:
                raise FileNotFoundError("Não foi possível importar o módulo agent")
            
            # 6. Atualizar estado compartilhado e iniciar agente
            print("[INFO] ✓ Expediente aberto. Iniciando agente de atividades...")
            self.shared_state['agent_running'] = True
            self.shared_state['agent_thread'] = threading.Thread(
                target=self.run_agent,
                args=(agent_module,),
                daemon=True
            )
            self.shared_state['agent_thread'].start()
            
            # 4. Atualizar UI em todas as janelas
            self.update_all_windows_ui()
            
            # 5. Esconder todas as telas de bloqueio para liberar a estação
            self.hide_all_lock_screens()
            
        except Exception as e:
            import traceback
            error_msg = str(e)[:50]
            self.status_label.config(
                text=f"❌ Erro ao iniciar: {error_msg}",
                fg='#f85149'
            )
            self.shared_state['agent_running'] = False
            # Log do erro completo
            print(f"Erro ao iniciar agent: {traceback.format_exc()}")
    
    def run_agent(self, agent_module):
        """Executa o agent"""
        try:
            # Executar a função main do agent
            agent_module.main()
        except Exception as e:
            # Em caso de erro, atualizar status
            error_msg = str(e)[:50]
            if 'windows' in self.shared_state:
                for window in self.shared_state['windows']:
                    try:
                        window.root.after(0, lambda w=window, msg=error_msg: 
                                         w.status_label.config(
                                             text=f"❌ Erro: {msg}",
                                             fg='#f85149'
                                         ))
                    except:
                        pass
            self.shared_state['agent_running'] = False
            import traceback
            print(f"Erro ao executar agent: {traceback.format_exc()}")
    
    def stop_agent(self):
        """Para o agent e bloqueia a estação novamente"""
        # Nota: Esta é uma implementação básica
        # Em produção, seria necessário um mecanismo de parada mais robusto
        self.shared_state['agent_running'] = False
        
        # Fechar expediente no Bitrix24
        print("[INFO] Fechando expediente no Bitrix24...")
        if not close_timeman("Fim do expediente via HiProd Agent"):
            print("[WARN] Não foi possível registrar fechamento no Bitrix24")
        
        # Mostrar telas de bloqueio novamente
        self.show_all_lock_screens()
        
        # Atualizar UI em todas as janelas
        self.update_all_windows_ui()
    
    def update_all_windows_ui(self):
        """Atualiza a UI em todas as janelas de bloqueio"""
        if self.shared_state['agent_running']:
            status_text = "▶ Expediente em Andamento"
            status_color = '#238636'
            button_text = "⏹ Encerrar Expediente"
            button_bg = '#da3633'
            button_active = '#f85149'
        else:
            status_text = "⏸️ Expediente Não Iniciado"
            status_color = '#f85149'
            button_text = "▶ Iniciar Expediente"
            button_bg = '#238636'
            button_active = '#2ea043'
        
        # Atualizar esta janela
        self.status_label.config(text=status_text, fg=status_color)
        self.start_button.config(
            text=button_text,
            bg=button_bg,
            activebackground=button_active
        )
        
        # Atualizar outras janelas através do estado compartilhado
        if 'windows' in self.shared_state:
            for window in self.shared_state['windows']:
                if window != self:
                    try:
                        window.root.after(0, lambda w=window, st=status_text, sc=status_color, 
                                         bt=button_text, bb=button_bg, ba=button_active: 
                                         w.update_ui(st, sc, bt, bb, ba))
                    except:
                        pass
    
    def update_ui(self, status_text, status_color, button_text, button_bg, button_active):
        """Atualiza a UI desta janela"""
        self.status_label.config(text=status_text, fg=status_color)
        self.start_button.config(
            text=button_text,
            bg=button_bg,
            activebackground=button_active
        )


# FloatingButton e create_floating_button movidos para floating_button.py

def pause_timeman(user_id=None):
    """
    Pausa o expediente do usuário no Bitrix24.
    Usa o método timeman.pause
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return False
    
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/timeman.pause.json"
        
        payload = {}
        if user_id:
            payload['USER_ID'] = user_id
        
        print(f"[API] ☕ Pausando expediente para USER_ID: {user_id}")
        print(f"[API] URL: {url}")
        print(f"[API] Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Resposta pause: {json.dumps(data, indent=2)}")
        
        if 'result' in data:
            print(f"[API] ✓ Expediente pausado com sucesso!")
            return True
        
        return True
        
    except Exception as e:
        print(f"[API] ❌ Erro ao pausar expediente: {e}")
        return False


def resume_timeman(user_id=None, report="Retorno do intervalo via HiProd Agent"):
    """
    Retoma o expediente do usuário no Bitrix24 após pausa.
    Usa o método timeman.open para retomar
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return False
    
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    try:
        url = f"{BITRIX24_WEBHOOK_URL}/timeman.open.json"
        
        payload = {
            "REPORT": report
        }
        if user_id:
            payload['USER_ID'] = user_id
        
        print(f"[API] ▶️ Retomando expediente para USER_ID: {user_id}")
        print(f"[API] URL: {url}")
        print(f"[API] Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Resposta resume: {json.dumps(data, indent=2)}")
        
        if 'result' in data:
            status = data['result'].get('STATUS', '')
            print(f"[API] ✓ Expediente retomado! Status: {status}")
            return True
        
        return True
        
    except Exception as e:
        print(f"[API] ❌ Erro ao retomar expediente: {e}")
        return False


def request_manager_approval(user_id=None, reason="Acesso adicional após expediente encerrado", manager_id=None):
    """
    Solicita aprovação do coordenador para liberar acesso à máquina.
    
    Args:
        user_id: ID do usuário no Bitrix24
        reason: Motivo da solicitação
        manager_id: ID do coordenador (opcional, busca automaticamente se não fornecido)
        
    Retorna:
        dict com status da solicitação ou None em caso de erro
    """
    if requests is None:
        print("[ERROR] Módulo requests não disponível")
        return None
    
    if user_id is None:
        user_id = get_current_bitrix_user_id()
    
    # Buscar coordenador se não fornecido
    if manager_id is None:
        manager_info = get_user_manager(user_id)
        if manager_info:
            manager_id = manager_info.get('manager_id')
    
    # Verificar se temos coordenador
    if not manager_id:
        print("[API] ⚠ Coordenador não encontrado. Não é possível enviar mensagem.")
        return {'success': False, 'message': 'Coordenador não encontrado'}
    
    # Endpoint específico para enviar mensagem ao coordenador
    SEND_MESSAGE_URL = "https://grupohi.bitrix24.com.br/rest/43669/ya2tcweewvwbaydf/im.message.add"
    
    # Obter email e nome do usuário
    email = get_user_email_for_bitrix()
    user_info = get_user_work_schedule(user_id)
    user_name = user_info.get('name', email) if user_info else email
    
    # Criar mensagem para o coordenador
    message = (
        f"🔓 Solicitação de Liberação de Máquina\n\n"
        f"👤 Usuário: {user_name}\n"
        f"📧 Email: {email}\n"
        f"🆔 USER_ID: {user_id}\n\n"
        f"📝 Motivo: {reason}\n\n"
        f"⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    
    try:
        # Preparar dados da mensagem conforme o modelo fornecido
        message_data = {
            'DIALOG_ID': manager_id,  # ID do coordenador
            'MESSAGE': message
        }
        
        print(f"[API] 📧 Enviando mensagem ao coordenador (ID: {manager_id})")
        print(f"[API] URL: {SEND_MESSAGE_URL}")
        print(f"[API] Dados da mensagem: {json.dumps(message_data, indent=2, ensure_ascii=False)}")
        
        # Enviar mensagem usando o modelo fornecido
        response = requests.post(SEND_MESSAGE_URL, json=message_data, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"[API] Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Verificar se a mensagem foi enviada com sucesso
        if 'result' in data and data['result']:
            message_id = data['result'].get('id') if isinstance(data['result'], dict) else data['result']
            print(f"[API] ✓ Mensagem enviada ao coordenador com sucesso! Message ID: {message_id}")
            return {
                'success': True,
                'message_id': message_id,
                'manager_id': manager_id,
                'message': 'Mensagem enviada ao coordenador com sucesso'
            }
        else:
            print(f"[API] ⚠ Resposta não contém resultado válido: {data}")
            return {'success': False, 'message': 'Resposta da API não contém resultado válido'}
        
    except requests.exceptions.HTTPError as e:
        print(f"[API] ❌ Erro HTTP ao enviar mensagem: {e}")
        if hasattr(e.response, 'text'):
            print(f"[API] Resposta do erro: {e.response.text}")
        return {'success': False, 'message': f'Erro HTTP: {str(e)}'}
    except Exception as e:
        print(f"[API] ❌ Erro ao enviar mensagem: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Erro: {str(e)}'}


def check_approval_status(user_id=None):
    """
    Verifica se há aprovação pendente ou aprovada para o usuário.
    Por enquanto, retorna sempre False (não implementado completamente).
    Em produção, isso verificaria o status da tarefa de aprovação.
    """
    # TODO: Implementar verificação real do status de aprovação
    # Por enquanto, retorna False (não aprovado)
    return False


class MultiMonitorLockScreen:
    """Gerenciador de telas de bloqueio para múltiplos monitores"""
    
    def __init__(self, bitrix_user_id=None, needs_approval=False, timeman_info=None, is_machine_unlock=False):
        self.windows = []
        self.shared_state = {
            'agent_running': False,
            'agent_thread': None,
            'windows': [],
            'lock_screen_active': True,  # Tela de bloqueio ativa por padrão
            'bitrix_user_id': bitrix_user_id,  # USER_ID do Bitrix24
            'needs_approval': needs_approval,  # Requer aprovação do coordenador
            'timeman_info': timeman_info,  # Informações do expediente já trabalhado
            'approval_requested': False,  # Se já solicitou aprovação
            'approval_status': None,  # Status da aprovação
            'is_machine_unlock': is_machine_unlock  # Se é apenas liberação de máquina (não expediente)
        }
        
    def create_windows(self):
        """Cria uma janela de bloqueio para cada monitor"""
        try:
            monitors = get_all_monitors()
            
            if not monitors or len(monitors) == 0:
                print("[ERROR] Nenhum monitor detectado! Usando configuração padrão...")
                # Criar monitor padrão se nenhum for detectado
                import tkinter as tk
                root = tk.Tk()
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                root.destroy()
                monitors = [{'width': screen_width, 'height': screen_height, 'x': 0, 'y': 0}]
            
            print(f"[INFO] Detectados {len(monitors)} monitor(es)")
            for i, mon in enumerate(monitors):
                print(f"  Monitor {i+1}: {mon['width']}x{mon['height']} em ({mon['x']}, {mon['y']})")
            
            # Associar a lista de janelas ao estado compartilhado ANTES de criar janelas
            self.shared_state['windows'] = self.windows
            
            # Criar janela principal (primeira) - usa Tk()
            print("[INFO] Criando janela principal de bloqueio...")
            try:
                first_window = LockScreen(monitors[0], self.shared_state)
                self.windows.append(first_window)
                print("[INFO] ✓ Janela principal criada com sucesso")
            except Exception as e:
                print(f"[ERROR] Erro ao criar janela principal: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Criar janelas adicionais para outros monitores - usam Toplevel()
            for i, monitor in enumerate(monitors[1:], start=2):
                print(f"[INFO] Criando janela de bloqueio para monitor {i}...")
                try:
                    window = LockScreen(monitor, self.shared_state)
                    self.windows.append(window)
                    print(f"[INFO] ✓ Janela do monitor {i} criada com sucesso")
                except Exception as e:
                    print(f"[ERROR] Erro ao criar janela do monitor {i}: {e}")
                    # Continuar mesmo se uma janela falhar
                    import traceback
                    traceback.print_exc()
            
            print(f"[INFO] Criadas {len(self.windows)} janela(s) de bloqueio")
            
            # Verificar se pelo menos uma janela foi criada
            if len(self.windows) == 0:
                raise Exception("Nenhuma janela de bloqueio foi criada!")
                
        except Exception as e:
            print(f"[ERROR] Erro crítico ao criar janelas: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def run(self):
        """Inicia o loop principal de todas as janelas"""
        # Executar loop principal da primeira janela
        # As outras janelas são Toplevel e compartilham o mesmo loop
        if not self.windows or len(self.windows) == 0:
            print("[ERROR] Nenhuma janela disponível para executar!")
            raise Exception("Nenhuma janela de bloqueio foi criada")
        
        print(f"[INFO] Iniciando loop principal com {len(self.windows)} janela(s)...")
        try:
            # Garantir que a primeira janela está visível
            if self.windows[0].root:
                self.windows[0].root.deiconify()
                self.windows[0].root.lift()
                self.windows[0].root.focus_force()
                self.windows[0].root.update()
                print("[INFO] ✓ Janela principal exibida")
            
            # Executar loop principal
            self.windows[0].root.mainloop()
        except Exception as e:
            print(f"[ERROR] Erro ao executar loop principal: {e}")
            import traceback
            traceback.print_exc()
            raise


def main():
    """Função principal"""
    try:
        print("=" * 50)
        print("HiProd Agent - Tela de Bloqueio")
        print("=" * 50)
        
        # Limpar cache para garantir dados frescos
        _bitrix_user_cache['user_id'] = None
        _bitrix_user_cache['email'] = None
        
        # Identificar usuário
        email = get_user_email_for_bitrix()
        print(f"\n[INFO] Usuário identificado:")
        print(f"       Email: {email}")
        
        # Buscar USER_ID no Bitrix24
        user_id = None
        if email:
            print(f"\n[INFO] Buscando usuário no Bitrix24 pelo email...")
            user_id = get_bitrix_user_id_by_email(email)
            if user_id:
                print(f"[INFO] [OK] USER_ID no Bitrix24: {user_id}")
            else:
                print(f"[WARN] Usuário não encontrado no Bitrix24 pelo email: {email}")
        
        # Buscar dados do usuário e horário configurado
        if user_id:
            print(f"\n[INFO] Buscando dados do usuário e configurações de horário...")
            
            # Buscar dados do usuário
            user_data = get_user_work_schedule(user_id)
            if user_data:
                print(f"[INFO] Nome: {user_data.get('name', 'N/A')}")
                print(f"[INFO] Cargo: {user_data.get('work_position', 'N/A')}")
                print(f"[INFO] Timeman habilitado: {user_data.get('timeman_enabled', False)}")
            
            # Buscar configurações de horário
            settings = get_timeman_settings(user_id)
            if settings:
                print(f"\n[INFO] Configurações de horário:")
                print(f"       Horário máximo início: {settings.get('UF_TM_MAX_START', 'N/A')}")
                print(f"       Horário mínimo término: {settings.get('UF_TM_MIN_FINISH', 'N/A')}")
                print(f"       Duração mínima: {settings.get('UF_TM_MIN_DURATION', 'N/A')}")
        
        # Verificar status do expediente no Bitrix24
        print("\n[INFO] Verificando status do expediente no Bitrix24...")
        timeman_info = check_timeman_status(user_id)
        if not timeman_info:
            print("[WARN] Resposta do Bitrix vazia, usando tela de bloqueio.")
            timeman_info = {'status': None, 'worked_today': False, 'can_open': True}
        status = timeman_info.get('status')
        worked_today = timeman_info.get('worked_today', False)
        can_open = timeman_info.get('can_open', True)
        print(f"[FLUXO] status={status!r} | worked_today={worked_today} | can_open={can_open}")

        # Verificar se tempo em serviço > 10 horas e pedir para finalizar no Bitrix
        def _duration_to_seconds(s):
            if not s or not isinstance(s, str):
                return 0
            parts = s.strip().split(':')
            if len(parts) >= 3:
                try:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except (ValueError, TypeError):
                    pass
            return 0

        duration_seconds = _duration_to_seconds(timeman_info.get('duration', '00:00:00'))
        if worked_today and duration_seconds >= 10 * 3600:
            try:
                import tkinter as _tk
                import tkinter.messagebox as msgbox
                msgbox.showwarning(
                    "HiProd - Tempo em serviço",
                    "Você possui mais de 10 horas de tempo em serviço hoje.\n\n"
                    "Por favor, finalize seu dia no Bitrix24 (registre sua saída) antes de continuar."
                )
                print("[INFO] Usuário avisado: finalizar dia no Bitrix24 (mais de 10h em serviço).")
                # Destruir root criado pelo messagebox para o botão flutuante ser Tk() e aparecer
                if getattr(_tk, '_default_root', None) is not None:
                    try:
                        _tk._default_root.destroy()
                    except Exception:
                        pass
                    _tk._default_root = None
            except Exception:
                print("[WARN] Você possui mais de 10h de tempo em serviço. Finalize seu dia no Bitrix24.")
        
        # Função auxiliar para iniciar agent sem tela de bloqueio
        def start_agent_directly(start_time=None):
            print("[FLUXO] start_agent_directly() iniciado.")
            try:
                # Verificar se está em horário de expediente antes de iniciar o agente
                print("[INFO] Verificando horário de expediente...")
                if not is_work_hours(user_id):
                    print("[WARN] [AVISO] Nao esta em horario de expediente. Agente nao sera iniciado.")
                    print("[INFO] Criando apenas botão flutuante sem agente de atividades...")
                    floating_btn = create_floating_button(user_id=user_id, start_time=start_time)
                    if floating_btn and floating_btn.root:
                        floating_btn.root.mainloop()
                    return
                
                # Verificar se o expediente está aberto antes de iniciar o agente
                print("[INFO] Verificando se expediente está aberto...")
                timeman_check = check_timeman_status(user_id)
                expediente_status = timeman_check.get('status')
                
                if expediente_status != 'OPENED':
                    print(f"[WARN] [AVISO] Expediente nao esta aberto (status: {expediente_status}). Agente NAO sera iniciado.")
                    print("[INFO] Criando apenas botão flutuante sem agente de atividades...")
                    floating_btn = create_floating_button(user_id=user_id, start_time=start_time)
                    if floating_btn and floating_btn.root:
                        floating_btn.root.mainloop()
                    return
                
                print("[INFO] [OK] Expediente esta aberto. Iniciando agente de atividades...")
                
                # Criar ou reutilizar botão flutuante
                print("[FLUXO] Chamando create_floating_button()...")
                try:
                    floating_btn = create_floating_button(user_id=user_id, start_time=start_time)
                except Exception as e_btn:
                    print(f"[ERROR] Falha ao criar botão flutuante: {e_btn}")
                    import traceback
                    traceback.print_exc()
                    return
                if not floating_btn or not getattr(floating_btn, 'root', None):
                    print("[ERROR] create_floating_button retornou sem janela válida.")
                    return
                print("[FLUXO] Botão flutuante criado. Agendando agent em background e iniciando mainloop...")
                
                # Iniciar mainloop primeiro; import do agent em background para não travar a UI
                def start_agent_after_import(agent_module):
                    if agent_module is None:
                        return
                    try:
                        global AGENT_THREAD, AGENT_RUNNING
                        try:
                            flag_file = os.path.join(os.path.dirname(__file__), '.agent_stop_flag')
                            if os.path.exists(flag_file):
                                os.remove(flag_file)
                        except Exception:
                            pass
                        AGENT_RUNNING = True
                        AGENT_THREAD = threading.Thread(target=agent_module.main, daemon=False)
                        AGENT_THREAD.start()
                        print("[INFO] [OK] Agent iniciado com sucesso! (monitoramento em execucao)")
                    except Exception as e:
                        print(f"[ERROR] Erro ao iniciar thread do agent: {e}")
                
                def load_agent_in_background():
                    print("[INFO] Importando módulo agent em background...")
                    agent_module = import_agent_module()
                    if floating_btn and floating_btn.root:
                        try:
                            floating_btn.root.after(0, lambda: start_agent_after_import(agent_module))
                        except tk.TclError:
                            pass

                # Agendar carregamento do agent em thread (não bloqueia a janela)
                if floating_btn and floating_btn.root:
                    floating_btn.root.after(0, lambda: threading.Thread(target=load_agent_in_background, daemon=True).start())
                    floating_btn.root.mainloop()
                
                # Janela fechada: parar o agent de forma ordenada antes de encerrar o processo
                try:
                    global AGENT_THREAD, AGENT_RUNNING
                    AGENT_RUNNING = False
                    try:
                        flag_file = os.path.join(os.path.dirname(__file__), '.agent_stop_flag')
                        with open(flag_file, 'w') as f:
                            f.write('STOP')
                    except Exception:
                        pass
                    if AGENT_THREAD and AGENT_THREAD.is_alive():
                        AGENT_THREAD.join(timeout=10)
                except NameError:
                    pass
            except Exception as e:
                print(f"[ERROR] Erro ao iniciar agent: {e}")
                import traceback
                traceback.print_exc()
        
        if status == 'OPENED':
            print("[INFO] [OK] Expediente esta ABERTO no Bitrix24!")
            print("[FLUXO] Chamando start_agent_directly() (criar botao flutuante + agent)...")
            start_agent_directly(start_time=timeman_info.get('time_start'))
            print("[FLUXO] start_agent_directly() retornou (janela fechada).")
            return
        
        elif status == 'CLOSED' and worked_today and not can_open:
            # Expediente já foi trabalhado e encerrado hoje
            print("[INFO] [AVISO] Expediente ja foi TRABALHADO e ENCERRADO hoje!")
            print(f"[INFO] Horário: {timeman_info.get('time_start')} - {timeman_info.get('time_finish')}")
            print(f"[INFO] Duração: {timeman_info.get('duration')}")
            print("[INFO] Acesso adicional requer aprovação do coordenador.")
            print("[INFO] Mostrando tela de bloqueio para solicitar liberação...")
        
        elif status == 'PAUSED':
            print("[INFO] [PAUSADO] Expediente esta PAUSADO no Bitrix24")
            print("[INFO] Mostrando tela de bloqueio para retomar...")
        
        elif status == 'EXPIRED':
            print("[INFO] [AVISO] Expediente EXPIRADO (nao fechado ontem)")
            print("[INFO] Mostrando tela de bloqueio para iniciar novo expediente...")
        
        elif status == 'CLOSED' and can_open:
            print("[INFO] [X] Expediente NAO INICIADO no Bitrix24")
            print("[INFO] Mostrando tela de bloqueio...")
        
        else:
            # status é None (erro na API) - mostrar tela de bloqueio por segurança
            print("[WARN] Não foi possível verificar status (API offline ou erro)")
            print("[INFO] Mostrando tela de bloqueio por segurança...")
        
        # Criar gerenciador de múltiplos monitores e mostrar tela de bloqueio
        # Passar o user_id e informações sobre expediente já trabalhado
        needs_approval = status == 'CLOSED' and worked_today and not can_open
        print(f"\n[INFO] Iniciando tela de bloqueio com USER_ID: {user_id}")
        print(f"[INFO] Requer aprovação: {needs_approval}")
        
        # Se expediente já foi encerrado, usar a tela simplificada com botões de ação
        app = MultiMonitorLockScreen(
            bitrix_user_id=user_id,
            needs_approval=needs_approval,
            timeman_info=timeman_info if needs_approval else None,
            is_machine_unlock=needs_approval  # Usar tela simplificada se expediente já encerrado
        )
        app.create_windows()
        app.run()
        
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"Erro ao iniciar interface: {e}")
        try:
            print(traceback.format_exc())
        except UnicodeEncodeError:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
