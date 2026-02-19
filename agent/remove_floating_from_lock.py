#!/usr/bin/env python3
"""Remove o corpo da classe FloatingButton que ficou em lock_screen.py."""
with open('lock_screen.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar "# FloatingButton e create_floating_button movidos" e "def pause_timeman"
start_remove = None
end_remove = None
for i, line in enumerate(lines):
    if '# FloatingButton e create_floating_button movidos' in line:
        start_remove = i + 1  # linha seguinte (remover o que vem depois do comentário)
    if start_remove is not None and end_remove is None and 'def pause_timeman(user_id=None):' in line:
        end_remove = i  # não incluir esta linha
        break

if start_remove is None or end_remove is None:
    print("Could not find boundaries", start_remove, end_remove)
    exit(1)

# Manter: linhas 0..start_remove-1, depois end_remove até o fim
# Remover: linhas start_remove até end_remove-1
new_lines = lines[:start_remove] + ['\n'] + lines[end_remove:]
with open('lock_screen.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Removed lines", start_remove + 1, "to", end_remove)
