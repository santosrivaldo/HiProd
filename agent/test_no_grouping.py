import requests

# Testar com uma query mais simples
token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Buscar atividades sem agrupamento
response = requests.get('http://192.241.155.236:8010/atividades?limite=10&agrupar=false', headers=headers)
activities = response.json()

print('Atividades sem agrupamento:')
for i, a in enumerate(activities[:5]):
    print(f'{i+1}. ID: {a.get("id")}, has_screenshot: {a.get("has_screenshot")}, screenshot_size: {a.get("screenshot_size")}')

# Procurar pela atividade 6363
activity_6363 = next((a for a in activities if a.get('id') == 6363), None)
if activity_6363:
    print(f'\nAtividade 6363 (sem agrupamento):')
    print(f'  has_screenshot: {activity_6363.get("has_screenshot")}')
    print(f'  screenshot_size: {activity_6363.get("screenshot_size")}')
else:
    print('\nAtividade 6363 nao encontrada sem agrupamento')
