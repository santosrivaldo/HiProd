#!/usr/bin/env python3
"""Remove a classe Popup de lock_screen.py (agora em floating_button.py)."""
with open('lock_screen.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start = None
for i, line in enumerate(lines):
    if line.strip().startswith('class Popup:'):
        start = i
    if start is not None and i > start and line.strip().startswith('class LockScreen:'):
        end = i
        break
else:
    end = None

if end is None:
    print("LockScreen not found")
    exit(1)

# Remove from class Popup through the line before class LockScreen
new_lines = lines[:start] + ['\n'] + lines[end:]
with open('lock_screen.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Removed Popup class, lines", start + 1, "to", end)
