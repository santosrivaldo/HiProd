import requests

token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://192.241.155.236:8010/tags', headers=headers)
tags = response.json()

print('Tags existentes:')
for tag in tags:
    print(f'ID: {tag.get("id")}, Nome: {tag.get("nome")}, Produtividade: {tag.get("produtividade")}, Ativo: {tag.get("ativo")}')
