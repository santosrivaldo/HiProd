#!/usr/bin/env python3
"""
Script de teste para verificar se o agente está funcionando corretamente
"""

import sys
import os
import time
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

def test_screenshot_capture():
    """Testa a captura de screenshot"""
    print("\n[TEST] Testando captura de screenshot...")
    try:
        screenshot = capture_screenshot()
        if screenshot:
            print(f"[OK] Screenshot capturado: {len(screenshot)} bytes")
            return True
        else:
            print("[ERROR] Falha ao capturar screenshot")
            return False
    except Exception as e:
        print(f"[ERROR] Erro na captura de screenshot: {e}")
        return False

def test_window_info():
    """Testa a captura de informações da janela"""
    print("\n[TEST] Testando captura de informações da janela...")
    try:
        window_info = get_active_window_info()
        print(f"[OK] Informações capturadas:")
        print(f"   - Janela: {window_info['window_title']}")
        print(f"   - Aplicação: {window_info['application']}")
        print(f"   - URL: {window_info.get('url', 'N/A')}")
        print(f"   - Página: {window_info.get('page_title', 'N/A')}")
        print(f"   - Domínio: {window_info.get('domain', 'N/A')}")
        return True
    except Exception as e:
        print(f"[ERROR] Erro na captura de informações: {e}")
        return False

def test_login():
    """Testa o login na API"""
    print("\n[TEST] Testando login na API...")
    try:
        login()
        print("[OK] Login realizado com sucesso")
        return True
    except Exception as e:
        print(f"[ERROR] Erro no login: {e}")
        return False

def test_user_monitoring():
    """Testa a obtenção do usuário monitorado"""
    print("\n[TEST] Testando obtenção do usuário monitorado...")
    try:
        user = get_logged_user()
        print(f"[OK] Usuário logado: {user}")
        
        user_id = get_usuario_monitorado_id(user)
        if user_id:
            print(f"[OK] ID do usuário monitorado: {user_id}")
            return True
        else:
            print("[ERROR] Falha ao obter ID do usuário monitorado")
            return False
    except Exception as e:
        print(f"[ERROR] Erro na obtenção do usuário: {e}")
        return False

def test_activity_sending():
    """Testa o envio de atividade com screenshot"""
    print("\n[TEST] Testando envio de atividade...")
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
        
        print(f"[INFO] Registro criado:")
        print(f"   - Screenshot: {'OK' if screenshot else 'ERROR'} ({len(screenshot) if screenshot else 0} bytes)")
        print(f"   - URL: {registro['url'] or 'N/A'}")
        print(f"   - Página: {registro['page_title'] or 'N/A'}")
        print(f"   - Domínio: {registro['domain'] or 'N/A'}")
        
        # Enviar atividade
        success = enviar_atividade(registro)
        if success:
            print("[OK] Atividade enviada com sucesso!")
            return True
        else:
            print("[ERROR] Falha ao enviar atividade")
            return False
            
    except Exception as e:
        print(f"[ERROR] Erro no envio de atividade: {e}")
        return False

def main():
    """Função principal de teste"""
    print("HiProd Agent - Teste de Funcionamento")
    print("=" * 50)
    
    tests = [
        ("Captura de Screenshot", test_screenshot_capture),
        ("Informações da Janela", test_window_info),
        ("Login na API", test_login),
        ("Usuário Monitorado", test_user_monitoring),
        ("Envio de Atividade", test_activity_sending),
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
    print("RESUMO DOS TESTES:")
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
        print("[SUCCESS] Todos os testes passaram! O agente está funcionando corretamente.")
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
