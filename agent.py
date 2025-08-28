import time
import psutil
import requests
import json
import win32gui
from datetime import datetime
import pytz

API_URL = 'http://localhost:5000/atividade'
USER_API_URL = 'http://localhost:5000/usuario'

def get_logged_user():
    users = psutil.users()
    return users[0].name if users else None

def get_active_window_title():
    window = win32gui.GetForegroundWindow()
    window_title = win32gui.GetWindowText(window)
    return window_title

def get_usuario_id(usuario_nome):
    response = requests.get(USER_API_URL, params={'usuario_nome': usuario_nome})
    user_data = response.json()
    return user_data.get('usuario_id')

def main():
    last_usuario_nome = get_logged_user()
    usuario_id = get_usuario_id(last_usuario_nome)

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
            usuario_id = get_usuario_id(current_usuario_nome)

        if current_window_title != last_window_title:
            ociosidade = 0
            last_window_title = current_window_title
        else:
            ociosidade += 10

        if ociosidade % 10 == 0:
            # Obtém a hora atual no fuso horário de São Paulo
            horario_sao_paulo = datetime.now(sao_paulo_tz).isoformat()
            registro = {
                'usuario_id': usuario_id,
                'ociosidade': ociosidade,
                'active_window': current_window_title,
                'horario': horario_sao_paulo
            }
            registros.append(registro)

        if len(registros) >= 6:
            for registro in registros:
                try:
                    requests.post(API_URL, json=registro)
                except Exception as e:
                    print(f"Erro ao enviar registro: {e}")
            registros.clear()

        time.sleep(10)

if __name__ == '__main__':
    main()