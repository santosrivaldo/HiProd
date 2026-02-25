#!/usr/bin/env python3
"""
HiProd Agent - Executável Único Integrado
==========================================

Este é o ponto de entrada principal que integra todos os componentes:
- floating_button.py: Botão flutuante e interface gráfica
- agent.py: Monitoramento de atividades, envio para API e detecção facial (tudo integrado)

Fluxo de execução:
1. Inicia o agent em thread separada
2. Inicia o botão flutuante (interface do usuário)
3. O agent.py contém todo o código de detecção facial integrado
4. Tudo roda em um único executável (.exe) - arquivo único compilado

Para compilar:
    python build.py
    ou
    build.bat (Windows)
"""

import sys
import os
import threading

# Detectar se está rodando como executável
IS_EXECUTABLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Adicionar o diretório atual ao path
if IS_EXECUTABLE:
    # Quando executável, os módulos estão no sys._MEIPASS
    sys.path.insert(0, sys._MEIPASS)
else:
    # Quando script Python, usar o diretório do arquivo
    sys.path.insert(0, os.path.dirname(__file__))

def main():
    """
    Função principal - inicia o sistema completo (agent + botão flutuante).
    Sem tela de bloqueio (lock screen removido).
    
    O agent gerencia:
    - Monitoramento de atividades (janelas, URLs, aplicações)
    - Envio de dados para API via HTTPS com handshake TLS
    - Detecção facial e rastreamento de presença
    
    ⚠️ IMPORTANTE: Configure API_URL no arquivo .env para usar HTTPS:
    API_URL=https://hiprod.grupohi.com.br
    """
    try:
        # Verificar configuração de API_URL
        api_url = os.getenv('API_URL', '')
        if api_url:
            if api_url.startswith('https://'):
                print(f"[INFO] ✅ HTTPS configurado: {api_url}")
                print(f"[INFO] ✅ Handshake TLS será realizado automaticamente")
            elif api_url.startswith('http://'):
                print(f"[WARN] ⚠️ HTTP não seguro detectado: {api_url}")
                print(f"[WARN] ⚠️ Recomendado usar HTTPS para segurança")
            else:
                print(f"[INFO] API_URL configurado: {api_url}")
        else:
            print(f"[INFO] Usando API_URL padrão (verifique configuração)")
        # Garantir que o Tkinter está disponível
        try:
            import tkinter as tk
            test_root = tk.Tk()
            test_root.withdraw()
            test_root.destroy()
        except Exception as tk_error:
            error_msg = f"[ERROR] Tkinter não está disponível: {tk_error}"
            print(error_msg)
            try:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Erro", f"Tkinter não está disponível:\n{tk_error}")
            except:
                pass
            sys.exit(1)

        # Importar agent e floating_button
        try:
            from agent import main as agent_main, get_logged_user, get_usuario_monitorado_id
            from floating_button import create_floating_button
        except ImportError as import_error:
            error_msg = f"[ERROR] Erro ao importar módulos: {import_error}"
            print(error_msg)
            print("[ERROR] Verifique se os arquivos agent.py e floating_button.py estão presentes.")
            try:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Erro de Importação",
                    f"Não foi possível importar módulos:\n{import_error}\n\n"
                    "Verifique se agent.py e floating_button.py estão presentes.")
            except:
                pass
            sys.exit(1)

        # Obter user_id para o botão flutuante
        try:
            usuario_windows = get_logged_user()
            user_id = get_usuario_monitorado_id(usuario_windows) if usuario_windows else None
        except Exception:
            user_id = None

        # Iniciar o agent em thread separada (daemon para encerrar com o processo)
        agent_thread = threading.Thread(target=agent_main, daemon=True)
        agent_thread.start()
        print("[INFO] Agent iniciado em background.")

        # Registrar a thread do agent no floating_button (para parada/pausa)
        try:
            import floating_button as fb
            fb.AGENT_THREAD = agent_thread
            fb.AGENT_RUNNING = True
        except Exception:
            pass

        # Criar botão flutuante e rodar interface
        btn = create_floating_button(user_id=user_id)
        if not btn or not getattr(btn, 'root', None):
            print("[ERROR] Não foi possível criar o botão flutuante.")
            sys.exit(1)
        print("[INFO] Botão flutuante ativo.")
        btn.root.mainloop()
        
    except KeyboardInterrupt:
        print("[INFO] Interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        error_msg = f"[ERROR] Erro ao iniciar HiProd Agent: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        # Tentar mostrar erro em janela mesmo em caso de falha
        try:
            import tkinter as tk
            import tkinter.messagebox as msgbox
            root = tk.Tk()
            root.withdraw()
            msgbox.showerror("Erro Fatal", 
                f"Erro ao iniciar HiProd Agent:\n\n{str(e)}\n\n"
                "Verifique os logs para mais detalhes.")
            root.destroy()
        except:
            pass
        
        sys.exit(1)

if __name__ == '__main__':
    main()


