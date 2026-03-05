"""
Script auxiliar para gerar um REFRESH_TOKEN OAuth do Google Drive
para a conta rivaldo.santos@grupohi.com.br.

Modo de uso (fora do Docker, com venv ou Python local):

    python backend/gdrive_oauth_setup.py

O script vai pedir:
  - CLIENT_ID
  - CLIENT_SECRET

Ambos são obtidos em: Google Cloud Console -> APIs & Services -> Credentials
-> Create credentials -> OAuth client ID (tipo Desktop).

Ao final, imprime o REFRESH_TOKEN que deve ser colocado no .env
como GDRIVE_REFRESH_TOKEN.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main():
    client_id = input("Informe o GOOGLE DRIVE CLIENT_ID: ").strip()
    client_secret = input("Informe o GOOGLE DRIVE CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        print("CLIENT_ID e CLIENT_SECRET são obrigatórios.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                "urn:ietf:wg:oauth:2.0:oob",
                "http://localhost",
            ],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # Algumas versões da lib não possuem run_console; usar run_local_server
    creds = flow.run_local_server(port=0, prompt="consent")

    print("\n===== COPIE ESTES VALORES PARA O .env =====")
    print(f"GDRIVE_CLIENT_ID={client_id}")
    print(f"GDRIVE_CLIENT_SECRET={client_secret}")
    print(f"GDRIVE_REFRESH_TOKEN={creds.refresh_token}")
    print("===========================================")


if __name__ == "__main__":
    main()

