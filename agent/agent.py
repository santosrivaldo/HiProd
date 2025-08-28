import time
import psutil
import requests
import win32gui
from datetime import datetime
import pytz
import os

API_BASE_URL = 'https://30639375-c8ee-4839-b62a-4cdd5cf7f23e-00-29im557edjni.worf.replit.dev:5000'
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


def get_active_window_title():
    window = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(window)


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


def enviar_atividade(registro):
    try:
        resp = requests.post(ATIVIDADE_URL,
                             json=registro,
                             headers=get_headers())
        if resp.status_code == 201:
            print(f"✅ Atividade enviada: {registro['active_window']}")
        elif resp.status_code == 401:
            print("⚠️ Token expirado, renovando...")
            login()
            enviar_atividade(registro)
        elif resp.status_code == 404 and "Usuário monitorado não encontrado" in resp.text:
            print(f"❌ Usuário monitorado ID {registro['usuario_monitorado_id']} não encontrado!")
            print("🔄 Tentando recriar usuário monitorado...")
            # Não podemos recriar aqui pois não temos o nome, mas podemos marcar para verificação
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

    last_window_title = ""
    ociosidade = 0
    registros = []

    tz = pytz.timezone('America/Sao_Paulo')

    while True:
        current_window_title = get_active_window_title()
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

        if current_window_title != last_window_title:
            ociosidade = 0
            last_window_title = current_window_title
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
                    'active_window': current_window_title,
                    'horario': datetime.now(tz).isoformat()
                }
                registros.append(registro)
            else:
                print("❌ Não foi possível obter ID do usuário monitorado, pulando registro...")

        if len(registros) >= 6:
            for r in registros:
                enviar_atividade(r)
            registros.clear()

        time.sleep(10)


if __name__ == '__main__':
    main()
