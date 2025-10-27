import requests

token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Buscar mais atividades
response = requests.get('http://192.241.155.236:8010/atividades?limite=20', headers=headers)
activities = response.json()

# Procurar pela atividade 6363
activity_6363 = next((a for a in activities if a.get('id') == 6363), None)
if activity_6363:
    print('Atividade 6363 encontrada:')
    print(f'  Screenshot: {"SIM" if activity_6363.get("has_screenshot") else "NAO"}')
    print(f'  Screenshot size: {activity_6363.get("screenshot_size", "N/A")}')
    print(f'  Janela: {activity_6363.get("active_window", "N/A")}')
else:
    print('Atividade 6363 nao encontrada nas ultimas 20')

# Contar screenshots
screenshots = [a for a in activities if a.get('has_screenshot')]
print(f'\nTotal de atividades: {len(activities)}')
print(f'Com screenshots: {len(screenshots)}')

# Mostrar IDs das atividades
print('\nIDs das atividades:')
for a in activities[:10]:
    print(f'  ID: {a.get("id")}')
