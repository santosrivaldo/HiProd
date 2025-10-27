import requests

token = requests.post('http://192.241.155.236:8010/login', json={'nome': 'connect', 'senha': 'L@undry60'}).json()['token']
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://192.241.155.236:8010/tags/18', headers=headers)
tag = response.json()

print('Detalhes da tag Navegador:')
print(f'Nome: {tag.get("nome")}')
print(f'Descricao: {tag.get("descricao")}')
print(f'Produtividade: {tag.get("produtividade")}')
print(f'Palavras-chave: {tag.get("palavras_chave", [])}')
