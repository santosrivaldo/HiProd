import io
import logging
import os
from typing import Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from .config import Config
from .database import DatabaseConnection

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_drive_service = None


def _get_drive_service():
    """
    Retorna uma instância singleton do serviço do Google Drive.
    Usa service account definida em GDRIVE_SERVICE_ACCOUNT_FILE.
    """
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    if not Config.GDRIVE_ENABLED:
        logging.warning("Google Drive desabilitado (GDRIVE_ENABLED=false).")
        return None

    service_account_file = Config.GDRIVE_SERVICE_ACCOUNT_FILE
    if not service_account_file:
        logging.error("GDRIVE_SERVICE_ACCOUNT_FILE não configurado.")
        return None

    if not os.path.isfile(service_account_file):
        logging.error("Arquivo de service account não encontrado: %s", service_account_file)
        return None

    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=SCOPES
        )
        _drive_service = build("drive", "v3", credentials=credentials)
        return _drive_service
    except Exception as exc:
        logging.exception("Erro ao inicializar serviço do Google Drive: %s", exc)
        return None


def _get_or_create_user_folder(usuario_monitorado_id: int) -> Optional[str]:
    """
    Busca ou cria a pasta do usuário no Drive, armazenando o ID em usuarios_monitorados.google_drive_folder_id.
    A pasta é criada dentro de GDRIVE_ROOT_FOLDER_ID.
    """
    root_folder_id = Config.GDRIVE_ROOT_FOLDER_ID
    if not root_folder_id:
        logging.error("GDRIVE_ROOT_FOLDER_ID não configurado.")
        return None

    service = _get_drive_service()
    if service is None:
        return None

    # Verificar se já existe pasta salva no banco
    with DatabaseConnection() as db:
        db.cursor.execute(
            """
            SELECT google_drive_folder_id
            FROM usuarios_monitorados
            WHERE id = %s;
            """,
            (usuario_monitorado_id,),
        )
        row = db.cursor.fetchone()
        if row and row[0]:
            return row[0]

    # Criar pasta no Drive
    folder_metadata = {
        "name": f"user_{usuario_monitorado_id}",
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [root_folder_id],
    }
    try:
        folder = service.files().create(body=folder_metadata, fields="id").execute()
    except Exception as exc:
        logging.exception("Erro ao criar pasta do usuário no Drive: %s", exc)
        return None

    folder_id = folder.get("id")
    if not folder_id:
        logging.error("Não foi possível obter o ID da pasta criada no Drive.")
        return None

    # Persistir no banco
    with DatabaseConnection() as db:
        db.cursor.execute(
            """
            UPDATE usuarios_monitorados
            SET google_drive_folder_id = %s
            WHERE id = %s;
            """,
            (folder_id, usuario_monitorado_id),
        )

    return folder_id


def upload_image_for_user(
    usuario_monitorado_id: int,
    image_bytes: bytes,
    filename: str,
    mime_type: str,
) -> Optional[str]:
    """
    Faz upload de uma imagem para a pasta do usuário no Google Drive.
    Retorna o file_id do Drive ou None em caso de erro.
    """
    if not image_bytes:
        return None

    service = _get_drive_service()
    if service is None:
        return None

    folder_id = _get_or_create_user_folder(usuario_monitorado_id)
    if not folder_id:
        return None

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type, resumable=False)

    try:
        created = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()
        return created.get("id")
    except Exception as exc:
        logging.exception("Erro ao fazer upload de imagem para o Drive: %s", exc)
        return None


def download_image(file_id: str) -> Optional[Tuple[bytes, str]]:
    """
    Baixa um arquivo de imagem do Google Drive.
    Retorna (bytes, mime_type) ou None em caso de erro.
    """
    if not file_id:
        return None

    service = _get_drive_service()
    if service is None:
        return None

    try:
        # Primeiro buscar o mimetype
        metadata = service.files().get(fileId=file_id, fields="mimeType").execute()
        mime_type = metadata.get("mimeType", "image/jpeg")

        request = service.files().get_media(fileId=file_id)
        # Para tamanhos pequenos, execute() direto é suficiente
        data = request.execute()
        if not isinstance(data, (bytes, bytearray)):
            logging.error("Resposta inesperada ao baixar arquivo do Drive (não é bytes).")
            return None
        return bytes(data), mime_type
    except Exception as exc:
        logging.exception("Erro ao baixar imagem do Drive: %s", exc)
        return None

