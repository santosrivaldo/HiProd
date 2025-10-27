import requests

# Testar diretamente o endpoint de screenshot
token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Tentar acessar o screenshot da atividade 6363
response = requests.get('http://192.241.155.236:8010/screenshot/6363', headers=headers)
print(f'Status: {response.status_code}')
print(f'Content-Type: {response.headers.get("Content-Type")}')
print(f'Content-Length: {response.headers.get("Content-Length")}')

if response.status_code == 200:
    print('Screenshot encontrado!')
else:
    print('Screenshot nao encontrado')
