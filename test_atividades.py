
#!/usr/bin/env python3
import requests
import json
import time
from datetime import datetime

# Configurações
BASE_URL = 'http://localhost:5000'
TEST_USER = 'admin'
TEST_PASSWORD = 'admin123'

def test_login():
    """Testa o login e retorna o token"""
    try:
        response = requests.post(f'{BASE_URL}/login', json={
            'nome': TEST_USER,
            'senha': TEST_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login realizado com sucesso: {data['usuario']}")
            return data['token']
        else:
            print(f"❌ Erro no login: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro na conexão de login: {e}")
        return None

def test_get_monitored_user(token, user_name):
    """Testa buscar/criar usuário monitorado"""
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{BASE_URL}/usuarios-monitorados?nome={user_name}', headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Usuário monitorado: {data['nome']} (ID: {data['id']})")
            return data['id']
        else:
            print(f"❌ Erro ao buscar usuário monitorado: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return None

def test_send_activity(token, usuario_monitorado_id):
    """Testa envio de atividade"""
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        activity_data = {
            'usuario_monitorado_id': usuario_monitorado_id,
            'ociosidade': 0,
            'active_window': 'Visual Studio Code - test_atividades.py',
            'titulo_janela': 'Visual Studio Code - test_atividades.py - Activity Tracker',
            'duracao': 60
        }
        
        print(f"📤 Enviando atividade: {json.dumps(activity_data, indent=2)}")
        
        response = requests.post(f'{BASE_URL}/atividade', json=activity_data, headers=headers)
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Atividade enviada com sucesso!")
            print(f"   ID: {data['id']}")
            print(f"   Categoria: {data['categoria']}")
            print(f"   Produtividade: {data['produtividade']}")
            print(f"   Usuário: {data['usuario_monitorado']}")
            return data['id']
        else:
            print(f"❌ Erro ao enviar atividade: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return None

def test_get_activities(token):
    """Testa listagem de atividades"""
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{BASE_URL}/atividades?limite=5', headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Atividades listadas: {len(data)} registros encontrados")
            
            if data:
                print("📋 Últimas 3 atividades:")
                for i, activity in enumerate(data[:3]):
                    print(f"   {i+1}. {activity['active_window']} - {activity['categoria']} ({activity['produtividade']})")
                    print(f"      Usuário: {activity['usuario_monitorado_nome']} - {activity['horario']}")
            
            return True
        else:
            print(f"❌ Erro ao listar atividades: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def main():
    print("🔍 Iniciando teste de recebimento de atividades...")
    print("="*60)
    
    # 1. Testar login
    print("\n1️⃣ Testando login...")
    token = test_login()
    if not token:
        return
    
    # 2. Testar usuário monitorado
    print("\n2️⃣ Testando usuário monitorado...")
    test_user_name = f"TestUser_{int(time.time())}"
    usuario_monitorado_id = test_get_monitored_user(token, test_user_name)
    if not usuario_monitorado_id:
        return
    
    # 3. Testar envio de atividade
    print("\n3️⃣ Testando envio de atividade...")
    activity_id = test_send_activity(token, usuario_monitorado_id)
    if not activity_id:
        return
    
    # 4. Aguardar um momento
    print("\n⏳ Aguardando 2 segundos...")
    time.sleep(2)
    
    # 5. Testar listagem de atividades
    print("\n4️⃣ Testando listagem de atividades...")
    test_get_activities(token)
    
    print("\n" + "="*60)
    print("✅ Teste concluído!")

if __name__ == '__main__':
    main()
