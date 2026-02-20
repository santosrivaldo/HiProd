#!/usr/bin/env python3
"""
HiProd Agent - Serviço Windows
==============================
Instala e executa o HiProd Agent como serviço do Windows.
O serviço inicia o agent na sessão do usuário logado para que a interface (botão flutuante, tela de bloqueio) funcione.

Uso (executar como Administrador):
  python agent_service.py install   - Instala o serviço
  python agent_service.py remove    - Remove o serviço
  python agent_service.py start    - Inicia o serviço
  python agent_service.py stop     - Para o serviço
  python agent_service.py debug    - Roda em primeiro plano (para testes)
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Diretório do agent (onde está main.py e .env) ou do exe (quando rodando como .exe do serviço)
IS_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
if IS_FROZEN:
    AGENT_DIR = Path(sys.executable).resolve().parent
else:
    AGENT_DIR = Path(__file__).resolve().parent
if not IS_FROZEN:
    os.chdir(AGENT_DIR)
    if str(AGENT_DIR) not in sys.path:
        sys.path.insert(0, str(AGENT_DIR))

# Nome e descrição do serviço
SERVICE_NAME = "HiProdAgent"
SERVICE_DISPLAY_NAME = "HiProd Agent"
SERVICE_DESCRIPTION = "Agent HiProd - Integração Bitrix24, monitoramento de atividades e tela de bloqueio."


def get_agent_command():
    """Retorna o comando para iniciar o agent: exe na mesma pasta (quando serviço é .exe) ou python main.py."""
    # Quando o serviço roda como .exe, o agent é o HiProd-Agent.exe na mesma pasta
    if IS_FROZEN:
        agent_exe = AGENT_DIR / "HiProd-Agent.exe"
        if agent_exe.exists():
            return [str(agent_exe)], str(AGENT_DIR)
    # Desenvolvimento ou exe em dist
    exe_onefile = AGENT_DIR / "dist" / "HiProd-Agent.exe"
    exe_old = AGENT_DIR / "dist" / "hiprod-agent.exe"
    exe_dir = AGENT_DIR / "dist" / "hiprod-agent" / "hiprod-agent.exe"
    main_py = AGENT_DIR / "main.py"
    candidates = [exe_onefile, exe_old, exe_dir]
    for exe in candidates:
        if exe and exe.exists():
            return [str(exe)], str(AGENT_DIR)
    return [sys.executable, str(main_py)], str(AGENT_DIR)


def start_agent_in_user_session():
    """
    Inicia o agent na sessão ativa do usuário (para a interface gráfica aparecer).
    Deve ser chamado de dentro do serviço (pywin32).
    """
    try:
        import win32ts
        import win32process
        import win32security
        import win32con
        import win32api
    except ImportError:
        print("[SERVICE] pywin32 nao encontrado. Instale: pip install pyinstaller pywin32")
        return False

    session_id = win32ts.WTSGetActiveConsoleSessionId()
    if session_id == 0xFFFFFFFF or session_id == 0:
        return False

    try:
        user_token = win32ts.WTSQueryUserToken(session_id)
    except Exception as e:
        print(f"[SERVICE] WTSQueryUserToken falhou: {e}")
        return False

    try:
        dup_token = win32security.DuplicateTokenEx(
            user_token,
            win32security.MaximumAllowed,
            None,
            win32security.SecurityIdentification,
            win32security.TokenPrimary,
        )
    except Exception as e:
        print(f"[SERVICE] DuplicateTokenEx falhou: {e}")
        win32api.CloseHandle(user_token)
        return False

    cmd, cwd = get_agent_command()
    cmd_line = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    try:
        startup = win32process.STARTUPINFO()
        startup.dwFlags = win32con.STARTF_USESHOWWINDOW
        startup.wShowWindow = win32con.SW_SHOW
        startup.lpDesktop = "winsta0\\default"
        win32process.CreateProcessAsUser(
            dup_token,
            None,
            cmd_line,
            None,
            None,
            False,
            win32con.CREATE_NEW_CONSOLE,
            None,
            cwd,
            startup,
        )
        return True
    except Exception as e:
        print(f"[SERVICE] CreateProcessAsUser falhou: {e}")
        return False
    finally:
        win32api.CloseHandle(dup_token)
        win32api.CloseHandle(user_token)


def run_agent_subprocess():
    """
    Inicia o agent como subprocess (fallback quando não há sessão de usuário ou para debug).
    """
    cmd, cwd = get_agent_command()
    try:
        subprocess.Popen(
            cmd,
            cwd=cwd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        print(f"[SERVICE] subprocess.Popen falhou: {e}")
        return False


def debug_run():
    """Modo debug: tenta iniciar o agent na sessão do usuário (para testar sem instalar o serviço)."""
    print("[SERVICE] Modo debug - iniciando agent na sessao do usuario...")
    if sys.platform != "win32":
        print("[SERVICE] So Windows e suportado.")
        return
    ok = start_agent_in_user_session()
    if not ok:
        print("[SERVICE] Fallback: iniciando como subprocess...")
        ok = run_agent_subprocess()
    print("[SERVICE] OK" if ok else "[SERVICE] Falha ao iniciar")


# --- Serviço Windows (pywin32) ---
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    HAS_WIN32_SERVICE = True
except ImportError:
    HAS_WIN32_SERVICE = False


if HAS_WIN32_SERVICE:

    class HiProdAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME
        _svc_description_ = SERVICE_DESCRIPTION

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.agent_started = False

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            self.main()

        def main(self):
            # Tenta iniciar o agent na sessão do usuário; se não houver sessão, espera e tenta de novo
            while True:
                if win32event.WaitForSingleObject(self.stop_event, 30000) == win32event.WAIT_OBJECT_0:
                    break
                if not self.agent_started:
                    if start_agent_in_user_session():
                        self.agent_started = True


def install_service():
    if not HAS_WIN32_SERVICE:
        print("Instale pywin32: pip install pywin32")
        return
    win32serviceutil.HandleCommandLine(HiProdAgentService, argv=sys.argv)


if __name__ == "__main__":
    # debug: testar início do agent na sessão do usuário (sem instalar serviço)
    if len(sys.argv) >= 2 and sys.argv[1].lower() == "debug":
        debug_run()
        sys.exit(0)
    if HAS_WIN32_SERVICE:
        # install/remove/start/stop ou, com 1 arg (exe sozinho), inicia o loop do serviço (SCM)
        win32serviceutil.HandleCommandLine(HiProdAgentService, argv=sys.argv)
    else:
        if len(sys.argv) == 1:
            print(__doc__)
            print("Comandos: install, remove, start, stop, debug")
        print("Para instalar o servico, instale pywin32: pip install pywin32")
        print("Em seguida execute como Administrador: python agent_service.py install")
        sys.exit(1)
