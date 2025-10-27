import requests

# Login
token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']

# Buscar atividades
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://192.241.155.236:8010/atividades?limite=50', headers=headers)
activities = response.json()

# Filtrar atividades com screenshots
screenshots = [a for a in activities if a.get('has_screenshot')]
print(f'Total de atividades: {len(activities)}')
print(f'Com screenshots: {len(screenshots)}')

if screenshots:
    print('\nUltima atividade com screenshot:')
    last = screenshots[0]
    print(f'  ID: {last.get("id")}')
    print(f'  Janela: {last.get("active_window")}')
    print(f'  Horario: {last.get("horario")}')
    print(f'  Screenshot size: {last.get("screenshot_size", "N/A")}')
else:
    print('\nNenhuma atividade com screenshot encontrada')

# Verificar atividades recentes (ultimas 5)
print('\nUltimas 5 atividades:')
for i, activity in enumerate(activities[:5]):
    print(f'{i+1}. ID: {activity.get("id")}, Screenshot: {"SIM" if activity.get("has_screenshot") else "NAO"}, Janela: {activity.get("active_window", "N/A")[:50]}...')
