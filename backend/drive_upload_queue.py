"""
Fila de upload para o Google Drive.
Processa itens pendentes em background: lê arquivo temporário, envia ao Drive, atualiza screen_frames.
"""
import logging
import os
import threading
import time
from typing import Optional

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
