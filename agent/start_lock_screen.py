#!/usr/bin/env python3
"""
Arquivo principal para iniciar a tela de bloqueio do HiProd Agent
Execute este arquivo para abrir a interface gráfica
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

from lock_screen import main

if __name__ == '__main__':
    main()



