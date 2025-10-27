import requests

token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://192.241.155.236:8010/atividades?limite=10', headers=headers)
activities = response.json()

print('Ultimas 10 atividades (apos teste):')
for i, a in enumerate(activities[:10]):
    print(f'{i+1}. ID: {a.get("id")}, Categoria: {a.get("categoria")}, Janela: {a.get("active_window", "N/A")[:40]}...')
