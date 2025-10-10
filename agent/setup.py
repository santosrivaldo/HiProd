#!/usr/bin/env python3
"""
Script de setup para o HiProd Agent
Configura o ambiente virtual e instala as dependências
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description=""):
    """Executa um comando e trata erros"""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Concluído")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro: {description}")
        print(f"   Comando: {command}")
        print(f"   Erro: {e.stderr}")
        return None

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ é necessário")
        print(f"   Versão atual: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatível")
    return True

def setup_venv():
    """Configura o ambiente virtual"""
    agent_dir = Path(__file__).parent
    venv_dir = agent_dir / "venv"
    
    print("🚀 Configurando HiProd Agent")
    print(f"📁 Diretório: {agent_dir}")
    
    # Verificar versão do Python
    if not check_python_version():
        return False
    
    # Criar ambiente virtual
    if venv_dir.exists():
        print("⚠️  Ambiente virtual já existe, removendo...")
        import shutil
        shutil.rmtree(venv_dir)
    
    if not run_command(f"python -m venv {venv_dir}", "Criando ambiente virtual"):
        return False
    
    # Determinar comando de ativação baseado no OS
    system = platform.system()
    if system == "Windows":
        activate_script = venv_dir / "Scripts" / "activate.bat"
        pip_path = venv_dir / "Scripts" / "pip.exe"
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        activate_script = venv_dir / "bin" / "activate"
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
    
    # Atualizar pip
    if not run_command(f'"{python_path}" -m pip install --upgrade pip', "Atualizando pip"):
        return False
    
    # Instalar dependências
    requirements_file = agent_dir / "requirements.txt"
    if requirements_file.exists():
        if not run_command(f'"{pip_path}" install -r "{requirements_file}"', "Instalando dependências"):
            return False
    else:
        print("⚠️  Arquivo requirements.txt não encontrado")
        return False
    
    # Criar script de execução
    create_run_script(agent_dir, venv_dir, system)
    
    print("\n🎉 Setup concluído com sucesso!")
    print("\n📋 Próximos passos:")
    if system == "Windows":
        print(f"   1. Executar agent: agent\\run.bat")
        print(f"   2. Gerar executável: build.bat")
        print(f"   3. Ou ative manualmente: {activate_script}")
    else:
        print(f"   1. Executar agent: ./agent/run.sh")
        print(f"   2. Gerar executável: python build.py")
        print(f"   3. Ou ative manualmente: source {activate_script}")
    
    print(f"\n📖 Documentação de build: BUILD.md")
    
    return True

def create_run_script(agent_dir, venv_dir, system):
    """Cria script para executar o agent"""
    if system == "Windows":
        # Script para Windows
        run_script = agent_dir / "run.bat"
        python_path = venv_dir / "Scripts" / "python.exe"
        
        script_content = f"""@echo off
echo 🚀 Iniciando HiProd Agent...
echo.

REM Verificar se o venv existe
if not exist "{venv_dir}" (
    echo ❌ Ambiente virtual não encontrado!
    echo Execute: python setup.py
    pause
    exit /b 1
)

REM Executar o agent
cd /d "{agent_dir}"
"{python_path}" agent.py

if errorlevel 1 (
    echo.
    echo ❌ Erro ao executar o agent
    pause
)
"""
    else:
        # Script para Linux/Mac
        run_script = agent_dir / "run.sh"
        python_path = venv_dir / "bin" / "python"
        
        script_content = f"""#!/bin/bash
echo "🚀 Iniciando HiProd Agent..."
echo

# Verificar se o venv existe
if [ ! -d "{venv_dir}" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "Execute: python3 setup.py"
    exit 1
fi

# Executar o agent
cd "{agent_dir}"
"{python_path}" agent.py

if [ $? -ne 0 ]; then
    echo
    echo "❌ Erro ao executar o agent"
    read -p "Pressione Enter para continuar..."
fi
"""
        # Tornar executável
        os.chmod(run_script, 0o755)
    
    with open(run_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Script de execução criado: {run_script}")

if __name__ == "__main__":
    try:
        success = setup_venv()
        if not success:
            print("\n❌ Setup falhou!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)
