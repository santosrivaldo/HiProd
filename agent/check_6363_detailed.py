import requests

# Fazer uma query direta para verificar o screenshot
token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Buscar atividade específica
response = requests.get('http://192.241.155.236:8010/atividades?limite=50', headers=headers)
activities = response.json()

# Procurar pela atividade 6363
activity_6363 = next((a for a in activities if a.get('id') == 6363), None)
if activity_6363:
    print('Atividade 6363 encontrada:')
    print(f'  has_screenshot: {activity_6363.get("has_screenshot")}')
    print(f'  screenshot_size: {activity_6363.get("screenshot_size")}')
    print(f'  active_window: {activity_6363.get("active_window")}')
else:
    print('Atividade 6363 nao encontrada')
