import requests

token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://192.241.155.236:8010/tags', headers=headers)
tags = response.json()

print('Tags com palavras-chave:')
for tag in tags:
    print(f'Nome: {tag.get("nome")}')
    print(f'Palavras-chave: {[p.get("palavra") for p in tag.get("palavras_chave", [])]}')
    print('---')
