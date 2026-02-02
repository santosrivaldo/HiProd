#!/usr/bin/env python3
"""
Script para verificar se o build do agent inclui a verificação facial
Verifica OpenCV, haarcascades e funcionalidades relacionadas
"""

import os
import sys
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def check_opencv_installation():
    """Verifica se OpenCV está instalado"""
    print_header("Verificando Instalação do OpenCV")
    
    try:
        import cv2
        print_success(f"OpenCV encontrado: {cv2.__version__}")
        print_info(f"Localização: {cv2.__file__}")
        
        # Verificar cv2.data
        try:
            haarcascades_path = cv2.data.haarcascades
            print_success(f"Haarcascades path: {haarcascades_path}")
            
            # Verificar arquivo haarcascade
            haarcascade_file = os.path.join(haarcascades_path, 'haarcascade_frontalface_default.xml')
            if os.path.exists(haarcascade_file):
                print_success(f"Haarcascade encontrado: {haarcascade_file}")
                file_size = os.path.getsize(haarcascade_file)
                print_info(f"Tamanho: {file_size / 1024:.1f} KB")
            else:
                print_error(f"Haarcascade não encontrado: {haarcascade_file}")
                return False
            
            # Listar outros haarcascades disponíveis
            if os.path.exists(haarcascades_path):
                xml_files = [f for f in os.listdir(haarcascades_path) if f.endswith('.xml')]
                print_info(f"Total de arquivos haarcascade: {len(xml_files)}")
                if len(xml_files) > 0:
                    print_info(f"Primeiros 5: {', '.join(xml_files[:5])}")
            
        except AttributeError as e:
            print_error(f"cv2.data não disponível: {e}")
            return False
        
        # Verificar DLLs (Windows)
        if sys.platform == 'win32':
            cv2_dir = os.path.dirname(cv2.__file__)
            dll_files = [f for f in os.listdir(cv2_dir) if f.endswith('.dll')]
            if dll_files:
                print_success(f"DLLs do OpenCV encontradas: {len(dll_files)}")
                print_info(f"DLLs: {', '.join(dll_files[:5])}")
            else:
                print_warning("Nenhuma DLL do OpenCV encontrada")
        
        return True
        
    except ImportError as e:
        print_error(f"OpenCV não instalado: {e}")
        print_info("Instale com: pip install opencv-python")
        return False
    except Exception as e:
        print_error(f"Erro ao verificar OpenCV: {e}")
        return False

def check_agent_code():
    """Verifica se o código de detecção facial está no agent.py"""
    print_header("Verificando Código no agent.py")
    
    agent_file = Path(__file__).parent / "agent.py"
    
    if not agent_file.exists():
        print_error("agent.py não encontrado!")
        return False
    
    print_success(f"agent.py encontrado: {agent_file}")
    
    # Ler arquivo e verificar conteúdo
    with open(agent_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ("FACE_DETECTION_AVAILABLE", "Variável FACE_DETECTION_AVAILABLE"),
        ("check_face_presence", "Função check_face_presence"),
        ("check_face_presence_silent", "Função check_face_presence_silent"),
        ("enviar_face_presence_check", "Função enviar_face_presence_check"),
        ("FacePresenceTracker", "Classe FacePresenceTracker"),
        ("get_haarcascade_path", "Função get_haarcascade_path"),
        ("face-presence-check", "Endpoint face-presence-check"),
    ]
    
    all_found = True
    for keyword, description in checks:
        if keyword in content:
            print_success(f"{description} encontrado")
        else:
            print_error(f"{description} NÃO encontrado")
            all_found = False
    
    return all_found

def check_spec_file():
    """Verifica se o arquivo .spec está configurado corretamente"""
    print_header("Verificando Arquivo .spec")
    
    spec_file = Path(__file__).parent / "hiprod-agent.spec"
    
    if not spec_file.exists():
        print_error("hiprod-agent.spec não encontrado!")
        return False
    
    print_success(f"hiprod-agent.spec encontrado: {spec_file}")
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ("import cv2", "Importação do cv2"),
        ("cv2.data.haarcascades", "Referência a haarcascades"),
        ("'cv2'", "cv2 nos hiddenimports"),
        ("'cv2.data'", "cv2.data nos hiddenimports"),
        ("'numpy'", "numpy nos hiddenimports"),
        ("opencv_binaries", "Inclusão de DLLs do OpenCV"),
        ("opencv_datas", "Inclusão de dados do OpenCV"),
        ("haarcascade", "Referência a haarcascade"),
    ]
    
    all_found = True
    for keyword, description in checks:
        if keyword in content:
            print_success(f"{description} encontrado")
        else:
            print_error(f"{description} NÃO encontrado")
            all_found = False
    
    return all_found

def check_requirements():
    """Verifica se requirements.txt inclui opencv-python"""
    print_header("Verificando requirements.txt")
    
    req_file = Path(__file__).parent / "requirements.txt"
    
    if not req_file.exists():
        print_error("requirements.txt não encontrado!")
        return False
    
    print_success(f"requirements.txt encontrado: {req_file}")
    
    with open(req_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'opencv' in content.lower():
        print_success("opencv-python encontrado em requirements.txt")
        # Mostrar linha
        for line in content.split('\n'):
            if 'opencv' in line.lower():
                print_info(f"  {line.strip()}")
        return True
    else:
        print_error("opencv-python NÃO encontrado em requirements.txt")
        return False

def check_build_script():
    """Verifica se build.py verifica face_detection"""
    print_header("Verificando build.py")
    
    build_file = Path(__file__).parent / "build.py"
    
    if not build_file.exists():
        print_error("build.py não encontrado!")
        return False
    
    print_success(f"build.py encontrado: {build_file}")
    
    with open(build_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'face_detection' in content:
        print_success("Verificação de face_detection.py encontrada em build.py")
        return True
    else:
        print_warning("Verificação de face_detection.py não encontrada em build.py")
        return True  # Não é crítico, código está em agent.py

def test_face_detection():
    """Testa se a detecção facial funciona"""
    print_header("Testando Detecção Facial")
    
    try:
        from agent import FACE_DETECTION_AVAILABLE, check_face_presence
        
        if FACE_DETECTION_AVAILABLE:
            print_success("FACE_DETECTION_AVAILABLE = True")
            print_info("Testando detecção facial (timeout: 2 segundos)...")
            
            # Teste rápido
            result = check_face_presence(timeout=2)
            
            if result:
                print_success("✓ Face detectada no teste!")
            else:
                print_warning("✗ Nenhuma face detectada (pode ser normal se não houver câmera/pessoa)")
            
            return True
        else:
            print_error("FACE_DETECTION_AVAILABLE = False")
            print_info("OpenCV não está disponível ou não foi carregado corretamente")
            return False
            
    except ImportError as e:
        print_error(f"Erro ao importar do agent: {e}")
        return False
    except Exception as e:
        print_error(f"Erro ao testar detecção facial: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("\n" + "=" * 60)
    print("  VERIFICAÇÃO DE BUILD - DETECÇÃO FACIAL")
    print("=" * 60)
    
    results = []
    
    # Verificações
    results.append(("OpenCV Instalado", check_opencv_installation()))
    results.append(("Código no agent.py", check_agent_code()))
    results.append(("Arquivo .spec", check_spec_file()))
    results.append(("requirements.txt", check_requirements()))
    results.append(("build.py", check_build_script()))
    results.append(("Teste Funcional", test_face_detection()))
    
    # Resumo
    print_header("RESUMO DA VERIFICAÇÃO")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} - {name}")
    
    print(f"\n{'=' * 60}")
    print(f"Resultado: {passed}/{total} verificações passaram")
    
    if passed == total:
        print_success("Todas as verificações passaram! Build deve incluir detecção facial.")
        return 0
    else:
        print_error(f"{total - passed} verificação(ões) falharam. Corrija antes do build.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

