import requests

# Login
token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']

# Buscar atividades recentes
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://192.241.155.236:8010/atividades?limite=10', headers=headers)
activities = response.json()

print('Ultimas 10 atividades:')
for i, a in enumerate(activities):
    screenshot_status = "SIM" if a.get('has_screenshot') else "NAO"
    window = a.get('active_window', 'N/A')[:40]
    print(f'{i+1}. ID: {a.get("id")}, Screenshot: {screenshot_status}, Janela: {window}...')

# Verificar se há screenshots
screenshots = [a for a in activities if a.get('has_screenshot')]
print(f'\nTotal com screenshots: {len(screenshots)}')

if screenshots:
    print('Atividades com screenshots:')
    for s in screenshots:
        print(f'  - ID: {s.get("id")}, Tamanho: {s.get("screenshot_size", "N/A")} bytes')
