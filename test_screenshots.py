#!/usr/bin/env python3
"""
Script para testar o sistema de screenshots
"""

import requests
import json
import base64
from PIL import Image
import io

def test_screenshot_system():
    """Testa o sistema completo de screenshots"""
    
    print("🧪 Testando sistema de screenshots...")
    
    try:
        # 1. Testar login
        print("1. Testando login...")
        login_response = requests.post('http://localhost:8000/login', json={
            'nome': 'admin',
            'senha': 'Brasil@1402'
        })
        
        if login_response.status_code != 200:
            print(f"❌ Erro no login: {login_response.status_code}")
            return False
            
        token = login_response.json().get('token')
        print("✅ Login realizado com sucesso")
        
        # 2. Testar busca de atividades
        print("2. Testando busca de atividades...")
        headers = {'Authorization': f'Bearer {token}'}
        activities_response = requests.get('http://localhost:8000/atividades', headers=headers)
        
        if activities_response.status_code != 200:
            print(f"❌ Erro ao buscar atividades: {activities_response.status_code}")
            return False
            
        activities = activities_response.json()
        print(f"✅ {len(activities)} atividades encontradas")
        
        # 3. Verificar atividades com screenshot
        activities_with_screenshot = [a for a in activities if a.get('has_screenshot')]
        print(f"📸 {len(activities_with_screenshot)} atividades com screenshot")
        
        if not activities_with_screenshot:
            print("⚠️ Nenhuma atividade com screenshot encontrada")
            return True
            
        # 4. Testar carregamento de screenshot
        activity_id = activities_with_screenshot[0]['id']
        print(f"3. Testando screenshot da atividade {activity_id}...")
        
        screenshot_response = requests.get(f'http://localhost:8000/atividade/screenshot/{activity_id}', headers=headers)
        
        if screenshot_response.status_code == 200:
            print("✅ Screenshot carregado com sucesso!")
            print(f"   Tamanho: {len(screenshot_response.content)} bytes")
            print(f"   Content-Type: {screenshot_response.headers.get('Content-Type')}")
            
            # 5. Testar se é uma imagem válida
            try:
                img = Image.open(io.BytesIO(screenshot_response.content))
                print(f"✅ Imagem válida: {img.size[0]}x{img.size[1]} pixels")
                return True
            except Exception as e:
                print(f"❌ Erro ao processar imagem: {e}")
                return False
        else:
            print(f"❌ Erro ao carregar screenshot: {screenshot_response.status_code}")
            print(f"   Resposta: {screenshot_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

if __name__ == "__main__":
    success = test_screenshot_system()
    if success:
        print("\n🎉 Sistema de screenshots funcionando corretamente!")
    else:
        print("\n❌ Problemas encontrados no sistema de screenshots")
