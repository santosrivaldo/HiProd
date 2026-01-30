#!/usr/bin/env python3
"""
HiProd Agent - Executável Único Integrado
==========================================

Este é o ponto de entrada principal que integra todos os componentes:
- lock_screen.py: Tela de bloqueio e interface gráfica
- agent.py: Monitoramento de atividades e envio para API
- face_detection.py: Detecção facial e rastreamento de presença

Fluxo de execução:
1. Inicia a tela de bloqueio (lock_screen)
2. Quando o expediente é aberto, inicia o agent em thread separada
3. O agent automaticamente integra a detecção facial
4. Tudo roda em um único executável (.exe)

Para compilar:
    python build.py
    ou
    build.bat (Windows)
"""

import sys
import os

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
    Função principal - inicia o sistema completo
    
    O lock_screen gerencia:
    - Interface gráfica de bloqueio
    - Integração com Bitrix24 Timeman
    - Inicialização do agent quando expediente é aberto
    
    O agent gerencia:
    - Monitoramento de atividades (janelas, URLs, aplicações)
    - Envio de dados para API
    - Detecção facial e rastreamento de presença
    
    Tudo integrado em um único executável!
    """
    try:
        # Garantir que o Tkinter está disponível
        try:
            import tkinter as tk
            # Testar se Tkinter funciona
            test_root = tk.Tk()
            test_root.withdraw()  # Esconder janela de teste
            test_root.destroy()
        except Exception as tk_error:
            error_msg = f"[ERROR] Tkinter não está disponível: {tk_error}"
            print(error_msg)
            # Tentar mostrar mensagem de erro mesmo sem Tkinter
            try:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Erro", f"Tkinter não está disponível:\n{tk_error}")
            except:
                pass
            sys.exit(1)
        
        # Importar lock_screen (que gerencia tudo)
        try:
            from lock_screen import main as lock_screen_main
        except ImportError as import_error:
            error_msg = f"[ERROR] Erro ao importar lock_screen: {import_error}"
            print(error_msg)
            print("[ERROR] Verifique se todos os arquivos estão presentes:")
            print("  - lock_screen.py")
            print("  - agent.py")
            print("  - face_detection.py")
            
            # Tentar mostrar erro em janela
            try:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Erro de Importação", 
                    f"Não foi possível importar lock_screen:\n{import_error}\n\n"
                    "Verifique se todos os arquivos estão presentes.")
            except:
                pass
            sys.exit(1)
        
        # Iniciar a tela de bloqueio
        # Ela automaticamente iniciará o agent quando necessário
        # O agent automaticamente usará face_detection se disponível
        print("[INFO] Iniciando tela de bloqueio...")
        lock_screen_main()
        
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


