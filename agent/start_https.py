#!/usr/bin/env python3
"""
Script para iniciar o HiProd Agent com HTTPS configurado
"""

import os
import sys

# Configurar HTTPS antes de importar qualquer módulo
os.environ['API_URL'] = 'https://hiprod.grupohi.com.br'
os.environ['SSL_VERIFY'] = 'true'

print("=" * 60)
print("INICIANDO HIPROD AGENT COM HTTPS")
print("=" * 60)
print(f"API_URL: {os.environ.get('API_URL')}")
print(f"SSL_VERIFY: {os.environ.get('SSL_VERIFY')}")
print("=" * 60)
print()

# Adicionar diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar e executar main
try:
    from main import main
    main()
except KeyboardInterrupt:
    print("\n[INFO] Agente interrompido pelo usuário")
    sys.exit(0)
except Exception as e:
    print(f"\n[ERROR] Erro ao iniciar agente: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

