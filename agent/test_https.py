#!/usr/bin/env python3
"""
Script de teste para verificar conexão HTTPS com handshake TLS
"""

import os
import sys

# Configurar HTTPS antes de importar agent
os.environ['API_URL'] = 'https://hiprod.grupohi.com.br'
os.environ['SSL_VERIFY'] = 'true'

# Adicionar diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("TESTE DE CONEXÃO HTTPS COM HANDSHAKE TLS")
print("=" * 60)
print(f"API_URL: {os.environ.get('API_URL')}")
print(f"SSL_VERIFY: {os.environ.get('SSL_VERIFY')}")
print("=" * 60)
print()

# Importar módulos do agent
try:
    from agent import (
        API_BASE_URL,
        perform_tls_handshake,
        get_secure_session,
        get_usuario_monitorado_id,
        get_logged_user
    )
    
    print(f"[TEST] API_BASE_URL configurado: {API_BASE_URL}")
    print()
    
    # Teste 1: Handshake TLS
    print("[TEST 1] Testando handshake TLS...")
    if API_BASE_URL.startswith('https://'):
        if perform_tls_handshake(API_BASE_URL):
            print("[TEST 1] ✅ Handshake TLS bem-sucedido!")
        else:
            print("[TEST 1] ❌ Falha no handshake TLS")
            sys.exit(1)
    else:
        print("[TEST 1] ⚠️ URL não é HTTPS, pulando handshake TLS")
    print()
    
    # Teste 2: Criar sessão segura
    print("[TEST 2] Criando sessão HTTP segura...")
    try:
        session = get_secure_session()
        print("[TEST 2] ✅ Sessão segura criada com sucesso!")
        print(f"[TEST 2]    SSL Verify: {session.verify}")
    except Exception as e:
        print(f"[TEST 2] ❌ Erro ao criar sessão: {e}")
        sys.exit(1)
    print()
    
    # Teste 3: Testar conexão com API
    print("[TEST 3] Testando conexão com API...")
    try:
        usuario_nome = get_logged_user()
        print(f"[TEST 3] Usuário Windows: {usuario_nome}")
        
        if usuario_nome:
            user_id = get_usuario_monitorado_id(usuario_nome)
            if user_id:
                print(f"[TEST 3] ✅ Conexão com API bem-sucedida!")
                print(f"[TEST 3]    Usuário ID: {user_id}")
            else:
                print("[TEST 3] ⚠️ Não foi possível obter ID do usuário (pode ser normal se usuário não existe)")
        else:
            print("[TEST 3] ⚠️ Não foi possível obter nome do usuário Windows")
    except Exception as e:
        print(f"[TEST 3] ❌ Erro ao conectar com API: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print()
    
    print("=" * 60)
    print("✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
    print("=" * 60)
    print()
    print("O agente está configurado para usar HTTPS com handshake TLS.")
    print("Você pode iniciar o agente normalmente com: python main.py")
    
except ImportError as e:
    print(f"❌ Erro ao importar módulos do agent: {e}")
    print("Certifique-se de que está no diretório correto e que agent.py existe.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erro durante teste: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

