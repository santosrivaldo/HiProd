import time
import psutil
import requests
import json
import win32gui
from datetime import datetime
import os
import pytz 

API_BASE_URL = 'https://30639375-c8ee-4839-b62a-4cdd5cf7f23e-00-29im557edjni.worf.replit.dev:5000'
ATIVIDADE_URL = f"{API_BASE_URL}/atividade"
USUARIOS_MONITORADOS_URL = f"{API_BASE_URL}/usuarios-monitorados"

# Definir o token JWT (pode ser obtido no login da API)
JWT_TOKEN = os.getenv("JWT_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}" if JWT_TOKEN else "",
    "Content-Type": "application/json"
}

def get_logged_user():
    users = psutil.users()
    return users[0].name if users else None

def get_active_window_title():
    window = win32gui.GetForegroundWindow()
    window_title = win32gui.GetWindowText(window)
    return window_title

def get_usuario_monitorado_id(usuario_nome):
    response = requests.get(USUARIOS_MONITORADOS_URL, params={'nome': usuario_nome}, headers=HEADERS)
    if response.status_code == 200:
        user_data = response.json()
        return user_data.get('id')
    else:
        print(f"❌ Erro ao buscar usuário monitorado: {response.text}")
        return None

def main():
    last_usuario_nome = get_logged_user()
    usuario_monitorado_id = get_usuario_monitorado_id(last_usuario_nome)

    last_window_title = ""
    ociosidade = 0
    registros = []

    # Define o fuso horário de São Paulo
    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')

    while True:
        current_window_title = get_active_window_title()
        current_usuario_nome = get_logged_user()

        if current_usuario_nome != last_usuario_nome:
            last_usuario_nome = current_usuario_nome
            usuario_monitorado_id = get_usuario_monitorado_id(current_usuario_nome)

        if current_window_title != last_window_title:
            ociosidade = 0
            last_window_title = current_window_title
        else:
            ociosidade += 10

        if ociosidade % 10 == 0:
            horario_sao_paulo = datetime.now(sao_paulo_tz).isoformat()
            registro = {
                'usuario_monitorado_id': usuario_monitorado_id,
                'ociosidade': ociosidade,
                'active_window': current_window_title,
                'horario': horario_sao_paulo
            }
            registros.append(registro)

        if len(registros) >= 6:
            for registro in registros:
                try:
                    response = requests.post(ATIVIDADE_URL, json=registro, headers=HEADERS)
                    if response.status_code != 201:
                        print(f"❌ Erro ao enviar registro: {response.status_code} {response.text}")
                except Exception as e:
                    print(f"Erro ao enviar registro: {e}")
            registros.clear()

        time.sleep(10)

if __name__ == '__main__':
    main()
