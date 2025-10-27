#!/usr/bin/env python3
"""
Script para testar especificamente o envio de screenshots
"""

import sys
import os
import base64
import requests
from datetime import datetime
import pytz

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importar funções do agente
try:
    from agent import (
        login, 
        get_active_window_info, 
        capture_screenshot,
        enviar_atividade,
        get_usuario_monitorado_id,
        get_logged_user
    )
    print("[OK] Imports do agente funcionando")
except ImportError as e:
    print(f"[ERROR] Erro ao importar agente: {e}")
    sys.exit(1)

def test_screenshot_size():
    """Testa o tamanho do screenshot capturado"""
    print("\n[TEST] Testando tamanho do screenshot...")
    try:
        screenshot = capture_screenshot()
        if screenshot:
            # Calcular tamanho em diferentes unidades
            size_bytes = len(screenshot)
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            
            print(f"[INFO] Screenshot capturado:")
            print(f"   - Tamanho: {size_bytes} bytes")
            print(f"   - Tamanho: {size_kb:.1f} KB")
            print(f"   - Tamanho: {size_mb:.2f} MB")
            
            # Verificar se está dentro do limite do servidor (200KB)
            if size_bytes > 200 * 1024:
                print(f"[WARNING] Screenshot muito grande! Limite do servidor: 200KB")
                print(f"   O servidor vai rejeitar este screenshot.")
                return False
            else:
                print(f"[OK] Screenshot dentro do limite do servidor")
                return True
        else:
            print("[ERROR] Falha ao capturar screenshot")
            return False
    except Exception as e:
        print(f"[ERROR] Erro na captura de screenshot: {e}")
        return False

def test_screenshot_encoding():
    """Testa se o screenshot está sendo codificado corretamente"""
    print("\n[TEST] Testando codificação do screenshot...")
    try:
        screenshot = capture_screenshot()
        if screenshot:
            # Verificar se é base64 válido
            try:
                decoded = base64.b64decode(screenshot)
                print(f"[OK] Screenshot é base64 válido")
                print(f"   - Tamanho original: {len(screenshot)} caracteres")
                print(f"   - Tamanho decodificado: {len(decoded)} bytes")
                return True
            except Exception as e:
                print(f"[ERROR] Screenshot não é base64 válido: {e}")
                return False
        else:
            print("[ERROR] Nenhum screenshot para testar")
            return False
    except Exception as e:
        print(f"[ERROR] Erro no teste de codificação: {e}")
        return False

def test_activity_with_screenshot():
    """Testa o envio de uma atividade com screenshot"""
    print("\n[TEST] Testando envio de atividade com screenshot...")
    try:
        # Obter informações
        user = get_logged_user()
        user_id = get_usuario_monitorado_id(user)
        
        if not user_id:
            print("[ERROR] Não foi possível obter ID do usuário")
            return False
        
        # Capturar informações
        window_info = get_active_window_info()
        screenshot = capture_screenshot()
        
        if not screenshot:
            print("[ERROR] Não foi possível capturar screenshot")
            return False
        
        print(f"[INFO] Screenshot capturado: {len(screenshot)} bytes")
        
        # Criar registro de teste
        registro = {
            'usuario_monitorado_id': user_id,
            'ociosidade': 0,
            'active_window': window_info['window_title'],
            'url': window_info.get('url'),
            'page_title': window_info.get('page_title'),
            'domain': window_info.get('domain'),
            'application': window_info['application'],
            'screenshot': screenshot,
            'horario': datetime.now(pytz.timezone('America/Sao_Paulo')).isoformat()
        }
        
        print(f"[INFO] Enviando atividade com screenshot...")
        
        # Enviar atividade
        success = enviar_atividade(registro)
        if success:
            print("[OK] Atividade com screenshot enviada com sucesso!")
            return True
        else:
            print("[ERROR] Falha ao enviar atividade com screenshot")
            return False
            
    except Exception as e:
        print(f"[ERROR] Erro no envio de atividade: {e}")
        return False

def check_recent_activities_for_screenshots():
    """Verifica se há atividades recentes com screenshots"""
    print("\n[TEST] Verificando atividades recentes com screenshots...")
    try:
        # Fazer login
        login()
        
        # Buscar atividades recentes
        headers = {"Authorization": f"Bearer {login()}"}
        response = requests.get("http://192.241.155.236:8010/atividades?limite=10", headers=headers)
        
        if response.status_code == 200:
            activities = response.json()
            screenshots = [a for a in activities if a.get('has_screenshot')]
            
            print(f"[INFO] Atividades recentes: {len(activities)}")
            print(f"[INFO] Com screenshots: {len(screenshots)}")
            
            if screenshots:
                print(f"[OK] Encontradas atividades com screenshots!")
                for activity in screenshots[:3]:
                    print(f"   - ID: {activity.get('id')}, Tamanho: {activity.get('screenshot_size', 'N/A')} bytes")
                return True
            else:
                print("[WARNING] Nenhuma atividade com screenshot encontrada")
                return False
        else:
            print(f"[ERROR] Erro ao buscar atividades: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Erro na verificação: {e}")
        return False

def main():
    """Função principal de teste"""
    print("HiProd Agent - Teste de Screenshots")
    print("=" * 50)
    
    tests = [
        ("Tamanho do Screenshot", test_screenshot_size),
        ("Codificação do Screenshot", test_screenshot_encoding),
        ("Envio de Atividade com Screenshot", test_activity_with_screenshot),
        ("Verificação de Screenshots no Servidor", check_recent_activities_for_screenshots),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n[EXEC] Executando: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] Erro inesperado em {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n" + "=" * 50)
    print("RESUMO DOS TESTES DE SCREENSHOT:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "[OK] PASSOU" if result else "[ERROR] FALHOU"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n[INFO] Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("[SUCCESS] Todos os testes de screenshot passaram!")
    else:
        print("[WARNING] Alguns testes falharam. Verifique os erros acima.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
