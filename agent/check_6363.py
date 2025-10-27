import requests

token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Buscar a atividade específica que acabamos de criar
response = requests.get('http://192.241.155.236:8010/atividades?limite=5', headers=headers)
activities = response.json()

print('Ultimas 5 atividades:')
for i, a in enumerate(activities):
    screenshot_status = 'SIM' if a.get('has_screenshot') else 'NAO'
    print(f'{i+1}. ID: {a.get("id")}, Screenshot: {screenshot_status}, Janela: {a.get("active_window", "N/A")}')

# Verificar se a atividade 6363 tem screenshot
activity_6363 = next((a for a in activities if a.get('id') == 6363), None)
if activity_6363:
    print(f'\nAtividade 6363:')
    print(f'  Screenshot: {"SIM" if activity_6363.get("has_screenshot") else "NAO"}')
    print(f'  Screenshot size: {activity_6363.get("screenshot_size", "N/A")}')
else:
    print('\nAtividade 6363 nao encontrada')
