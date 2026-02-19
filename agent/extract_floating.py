#!/usr/bin/env python3
"""Script para extrair Popup, FloatingButton e create_floating_button para floating_button.py"""
with open('lock_screen.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

popup = ''.join(lines[1106:1315])
floating = ''.join(lines[2623:4231])
create_fn = ''.join(lines[4433:4476])

header = '''#!/usr/bin/env python3
"""
Botao flutuante do HiProd Agent.
Contem: Popup, FloatingButton, create_floating_button.
"""

import tkinter as tk
import os
from datetime import datetime

'''

with open('floating_button.py', 'w', encoding='utf-8') as f:
    f.write(header)
    f.write(popup)
    f.write('\n\n')
    f.write(floating)
    f.write('\n\n')
    f.write(create_fn)

print('Written floating_button.py')
