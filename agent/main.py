#!/usr/bin/env python3
"""
Arquivo principal do HiProd Agent
Integra o lock_screen e o agent em um único executável
"""

import sys
import os

# Detectar se está rodando como executável
IS_EXECUTABLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Adicionar o diretório atual ao path
if IS_EXECUTABLE:
    # Quando executável, os módulos estão no sys._MEIPASS
    sys.path.insert(0, sys._MEIPASS)
else:
    # Quando script Python, usar o diretório do arquivo
    sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Função principal - inicia o lock_screen por padrão"""
    # Importar lock_screen
    from lock_screen import main as lock_screen_main
    
    # Iniciar a tela de bloqueio (que pode iniciar o agent quando necessário)
    lock_screen_main()

if __name__ == '__main__':
    main()


