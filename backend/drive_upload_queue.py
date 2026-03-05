"""
Fila de upload para o Google Drive e cache por dia no servidor.
- Durante o dia: frames vão para cache compacto (data/usuario_id).
- De madrugada (01:00 Brasília): job envia o dia anterior ao Drive e apaga os arquivos locais.
"""
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .config import Config
from .database import DatabaseConnection
from .google_drive_service import upload_image_for_user

_worker_thread: Optional[threading.Thread] = None
_worker_stop = threading.Event()
_INTERVAL_SEC = 5
_BATCH_SIZE = 20


def _ensure_queue_dir() -> str:
    path = getattr(Config, 'GDRIVE_UPLOAD_QUEUE_DIR', None) or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'uploads', 'drive_queue'
    )
    os.makedirs(path, exist_ok=True)
    return path


# ========== Cache por dia (compacto no servidor) ==========
BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")


def get_day_cache_dir(date_brasilia_str: str, usuario_monitorado_id: int) -> str:
    """Retorna o diretório do cache do dia para o usuário: BASE/YYYY-MM-DD/usuario_id"""
    base = getattr(Config, 'GDRIVE_DAY_CACHE_DIR', None) or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'uploads', 'drive_day_cache'
    )
    path = os.path.join(base, date_brasilia_str, str(usuario_monitorado_id))
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def get_day_cache_file_path(date_brasilia_str: str, usuario_monitorado_id: int, filename: str) -> str:
    """Retorna o caminho absoluto do arquivo no cache do dia."""
    dir_path = get_day_cache_dir(date_brasilia_str, usuario_monitorado_id)
    return os.path.join(dir_path, filename)


def enqueue_frame(screen_frame_id: int, file_path: str, content_type: str) -> None:
    """Registra um item na fila (já com arquivo em disco)."""
    with DatabaseConnection() as db:
        db.cursor.execute(
            """
            INSERT INTO drive_upload_queue (screen_frame_id, file_path, content_type, status)
            VALUES (%s, %s, %s, 'pending');
            """,
            (screen_frame_id, file_path, content_type),
        )


def process_queue() -> int:
    """
    Processa até BATCH_SIZE itens pendentes da fila.
    Retorna quantos itens foram processados (sucesso ou falha).
    """
    if not Config.GDRIVE_ENABLED:
        return 0

    processed = 0
    with DatabaseConnection() as db:
        db.cursor.execute(
            """
            SELECT q.id, q.screen_frame_id, q.file_path, q.content_type,
                   sf.usuario_monitorado_id, sf.captured_at, sf.monitor_index
            FROM drive_upload_queue q
            JOIN screen_frames sf ON sf.id = q.screen_frame_id
            WHERE q.status = 'pending'
            ORDER BY q.created_at ASC
            LIMIT %s;
            """,
            (_BATCH_SIZE,),
        )
        rows = db.cursor.fetchall()

    for row in rows:
        q_id, screen_frame_id, file_path, content_type, usuario_monitorado_id, captured_at, monitor_index = row
        if not os.path.isfile(file_path):
            logging.warning("Arquivo da fila não encontrado, marcando como falha: %s", file_path)
            with DatabaseConnection() as db:
                db.cursor.execute(
                    """
                    UPDATE drive_upload_queue SET status = 'failed', error_message = 'Arquivo não encontrado', updated_at = CURRENT_TIMESTAMP WHERE id = %s;
                    """,
                    (q_id,),
                )
            processed += 1
            continue

        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
        except Exception as e:
            logging.exception("Erro ao ler arquivo da fila %s: %s", file_path, e)
            with DatabaseConnection() as db:
                db.cursor.execute(
                    """
                    UPDATE drive_upload_queue SET status = 'failed', error_message = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s;
                    """,
                    (str(e)[:500], q_id),
                )
            processed += 1
            continue

        captured_str = captured_at.strftime("%Y%m%d%H%M%S") if hasattr(captured_at, "strftime") else str(captured_at)
        ext = ".jpg" if "jpeg" in (content_type or "").lower() else ".png"
        filename = f"frame_{usuario_monitorado_id}_{captured_str}_m{monitor_index or 0}{ext}"

        drive_file_id = upload_image_for_user(
            usuario_monitorado_id=usuario_monitorado_id,
            image_bytes=image_bytes,
            filename=filename,
            mime_type=content_type or "image/jpeg",
        )

        try:
            os.remove(file_path)
        except Exception:
            pass

        with DatabaseConnection() as db:
            if drive_file_id:
                db.cursor.execute(
                    """
                    UPDATE screen_frames SET drive_file_id = %s WHERE id = %s;
                    """,
                    (drive_file_id, screen_frame_id),
                )
                db.cursor.execute(
                    """
                    UPDATE drive_upload_queue SET status = 'done', drive_file_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s;
                    """,
                    (drive_file_id, q_id),
                )
            else:
                db.cursor.execute(
                    """
                    UPDATE drive_upload_queue SET status = 'failed', error_message = 'Upload retornou sem file_id', updated_at = CURRENT_TIMESTAMP WHERE id = %s;
                    """,
                    (q_id,),
                )
        processed += 1

    return processed


def _worker_loop() -> None:
    while not _worker_stop.is_set():
        try:
            process_queue()
        except Exception as e:
            logging.exception("Erro no worker da fila do Drive: %s", e)
        _worker_stop.wait(_INTERVAL_SEC)


def start_background_worker() -> None:
    """Inicia a thread que processa a fila de upload periodicamente."""
    global _worker_thread
    if not Config.GDRIVE_ENABLED:
        return
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    _worker_stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    logging.info("Worker da fila de upload do Drive iniciado (intervalo %ss).", _INTERVAL_SEC)


def stop_background_worker() -> None:
    """Sinaliza a thread para parar (útil em testes)."""
    _worker_stop.set()


# ========== Job de madrugada: enviar dia anterior ao Drive e apagar cache ==========
_midnight_thread: Optional[threading.Thread] = None
_midnight_stop = threading.Event()


def upload_yesterday_cache_to_drive() -> int:
    """
    Envia ao Drive todos os frames do dia anterior que estão no cache (file_path preenchido, drive_file_id NULL).
    Após upload, atualiza drive_file_id e remove o arquivo local.
    Retorna quantidade de frames processados.
    """
    if not Config.GDRIVE_ENABLED:
        return 0

    now_br = datetime.now(BRASILIA_TZ)
    yesterday_br = (now_br - timedelta(days=1)).date()
    date_str = yesterday_br.isoformat()

    with DatabaseConnection() as db:
        db.cursor.execute(
            """
            SELECT id, file_path, content_type, usuario_monitorado_id, captured_at, monitor_index
            FROM screen_frames
            WHERE drive_file_id IS NULL
              AND file_path IS NOT NULL
              AND file_path != ''
              AND ((captured_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date = %s::date
            ORDER BY captured_at ASC;
            """,
            (date_str,),
        )
        rows = db.cursor.fetchall()

    count = 0
    for row in rows:
        frame_id, file_path, content_type, usuario_monitorado_id, captured_at, monitor_index = row
        if not file_path or not os.path.isfile(file_path):
            with DatabaseConnection() as db:
                db.cursor.execute(
                    "UPDATE screen_frames SET file_path = NULL WHERE id = %s;",
                    (frame_id,),
                )
            count += 1
            continue

        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
        except Exception as e:
            logging.exception("Erro ao ler cache %s: %s", file_path, e)
            count += 1
            continue

        captured_str = captured_at.strftime("%Y%m%d%H%M%S") if hasattr(captured_at, "strftime") else str(captured_at)
        ext = ".jpg" if (content_type or "").lower().find("jpeg") >= 0 else ".png"
        filename = f"frame_{usuario_monitorado_id}_{captured_str}_m{monitor_index or 0}{ext}"

        drive_file_id = upload_image_for_user(
            usuario_monitorado_id=usuario_monitorado_id,
            image_bytes=image_bytes,
            filename=filename,
            mime_type=content_type or "image/jpeg",
        )

        try:
            os.remove(file_path)
        except Exception:
            pass

        with DatabaseConnection() as db:
            if drive_file_id:
                db.cursor.execute(
                    "UPDATE screen_frames SET drive_file_id = %s, file_path = NULL WHERE id = %s;",
                    (drive_file_id, frame_id),
                )
            else:
                db.cursor.execute(
                    "UPDATE screen_frames SET file_path = NULL WHERE id = %s;",
                    (frame_id,),
                )
        count += 1

    if count > 0:
        logging.info("Job madrugada: %s frames do dia %s enviados ao Drive e cache local removido.", count, date_str)
    return count


def _midnight_loop() -> None:
    """Aguarda até o horário configurado (ex.: 01:00 Brasília) e executa o upload do dia anterior."""
    hour = getattr(Config, 'GDRIVE_MIDNIGHT_UPLOAD_HOUR', 1)
    while not _midnight_stop.is_set():
        now_br = datetime.now(BRASILIA_TZ)
        next_run = now_br.replace(hour=hour, minute=0, second=0, microsecond=0)
        if next_run <= now_br:
            next_run += timedelta(days=1)
        delta = (next_run - now_br).total_seconds()
        logging.info("Próximo envio do cache ao Drive: %s (em %.0f s).", next_run.isoformat(), delta)
        while delta > 0 and not _midnight_stop.is_set():
            wait_sec = min(delta, 3600)
            if _midnight_stop.wait(timeout=wait_sec):
                return
            delta -= wait_sec
        if _midnight_stop.is_set():
            return
        try:
            upload_yesterday_cache_to_drive()
        except Exception as e:
            logging.exception("Erro no job de madrugada: %s", e)


def start_midnight_worker() -> None:
    """Inicia a thread que, de madrugada, envia o cache do dia anterior ao Drive e apaga os arquivos."""
    global _midnight_thread
    if not Config.GDRIVE_ENABLED:
        return
    if _midnight_thread is not None and _midnight_thread.is_alive():
        return
    _midnight_stop.clear()
    _midnight_thread = threading.Thread(target=_midnight_loop, daemon=True)
    _midnight_thread.start()
    logging.info("Worker de madrugada (cache -> Drive) iniciado.")
