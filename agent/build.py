#!/usr/bin/env python3
"""
Script de build para gerar o executável do HiProd Agent
Automatiza o processo de compilação com PyInstaller
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
import time

# Tentar importar PyInstaller para verificar disponibilidade
try:
    import PyInstaller
    PYINSTALLER_AVAILABLE = True
    PYINSTALLER_VERSION = PyInstaller.__version__
except ImportError:
    PYINSTALLER_AVAILABLE = False
    PYINSTALLER_VERSION = None

class AgentBuilder:
    def __init__(self):
        self.agent_dir = Path(__file__).parent
        self.venv_dir = self.agent_dir / "venv"
        self.dist_dir = self.agent_dir / "dist"
        self.build_dir = self.agent_dir / "build"
        self.spec_file = self.agent_dir / "hiprod-agent.spec"
        
        # Determinar caminhos baseado no OS
        system = platform.system()
        if system == "Windows":
            self.python_path = self.venv_dir / "Scripts" / "python.exe"
            self.pyinstaller_path = self.venv_dir / "Scripts" / "pyinstaller.exe"
        else:
            self.python_path = self.venv_dir / "bin" / "python"
            self.pyinstaller_path = self.venv_dir / "bin" / "pyinstaller"
    
    def print_step(self, message):
        """Imprime uma etapa do processo"""
        print(f"\n[INFO] {message}")
        print("=" * 60)
    
    def print_success(self, message):
        """Imprime mensagem de sucesso"""
        print(f"[OK] {message}")
    
    def print_error(self, message):
        """Imprime mensagem de erro"""
        print(f"[ERROR] {message}")
    
    def run_command(self, command, description=""):
        """Executa um comando e trata erros"""
        print(f"[EXEC] {description}")
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                capture_output=True, 
                text=True,
                cwd=self.agent_dir
            )
            print(f"[OK] {description} - Concluido")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Erro: {description}")
            print(f"   Comando: {command}")
            print(f"   Erro: {e.stderr}")
            return False
    
    def check_prerequisites(self):
        """Verifica se os pré-requisitos estão atendidos"""
        self.print_step("Verificando pré-requisitos")
        
        # Verificar se o PyInstaller está instalado (usar Python atual)
        pyinstaller_found = False
        if PYINSTALLER_AVAILABLE:
            pyinstaller_found = True
            self.print_success(f"PyInstaller encontrado (versão: {PYINSTALLER_VERSION})")
        elif self.pyinstaller_path.exists():
            pyinstaller_found = True
            self.print_success(f"PyInstaller encontrado em: {self.pyinstaller_path}")
        else:
            # Tentar usar python -m PyInstaller como último recurso
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'PyInstaller', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    pyinstaller_found = True
                    self.print_success("PyInstaller encontrado via python -m PyInstaller")
            except:
                pass
        
        if not pyinstaller_found:
            self.print_error("PyInstaller nao encontrado!")
            print("Execute: pip install pyinstaller")
            return False
        
        # Verificar se os arquivos principais existem
        # NOTA: face_detection.py está integrado em agent.py, não é necessário como arquivo separado
        main_file = self.agent_dir / "main.py"
        agent_file = self.agent_dir / "agent.py"
        lock_screen_file = self.agent_dir / "lock_screen.py"
        
        if not main_file.exists():
            self.print_error("Arquivo main.py nao encontrado!")
            return False
        if not agent_file.exists():
            self.print_error("Arquivo agent.py nao encontrado!")
            return False
        if not lock_screen_file.exists():
            self.print_error("Arquivo lock_screen.py nao encontrado!")
            return False
        
        # Verificar se agent.py contém o código de detecção facial integrado
        try:
            with open(agent_file, 'r', encoding='utf-8') as f:
                agent_content = f.read()
                if 'FACE_DETECTION_AVAILABLE' not in agent_content:
                    self.print_error("Arquivo agent.py nao contem codigo de deteccao facial integrado!")
                    return False
        except Exception as e:
            self.print_error(f"Erro ao verificar agent.py: {e}")
            return False
        
        self.print_success("Todos os pre-requisitos atendidos")
        return True
    
    def clean_build_dirs(self):
        """Limpa diretórios de build anteriores"""
        self.print_step("Limpando builds anteriores")
        
        dirs_to_clean = [self.dist_dir, self.build_dir]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                print(f"[CLEAN] Removendo: {dir_path}")
                shutil.rmtree(dir_path)
        
        self.print_success("Diretorios limpos")
    
    def create_icon(self):
        """Cria um ícone simples se não existir"""
        icon_path = self.agent_dir / "icon.ico"
        
        if not icon_path.exists():
            print("[ICON] Criando icone padrao...")
            try:
                from PIL import Image, ImageDraw
                
                # Criar uma imagem 64x64 com ícone simples
                img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Desenhar um círculo azul simples
                draw.ellipse([8, 8, 56, 56], fill=(59, 130, 246, 255))
                draw.ellipse([16, 16, 48, 48], fill=(255, 255, 255, 255))
                draw.ellipse([24, 24, 40, 40], fill=(59, 130, 246, 255))
                
                # Salvar como ICO
                img.save(icon_path, format='ICO')
                print(f"[OK] Icone criado: {icon_path}")
                
                return str(icon_path)
            except ImportError:
                print("[WARN] Pillow nao disponivel para criar icone")
                return None
        else:
            return str(icon_path)
    
    def build_executable(self):
        """Compila o executável usando PyInstaller com arquivo spec"""
        self.print_step("Compilando executável")
        
        # Criar ícone se necessário
        icon_path = self.create_icon()
        
        # Verificar se o arquivo spec existe
        if not self.spec_file.exists():
            self.print_error(f"Arquivo spec nao encontrado: {self.spec_file}")
            return False
        
        # Determinar comando PyInstaller
        # Tentar usar python -m PyInstaller primeiro (mais confiável)
        if PYINSTALLER_AVAILABLE:
            command = f'"{sys.executable}" -m PyInstaller --clean --noconfirm "{self.spec_file}"'
        elif self.pyinstaller_path.exists():
            command = f'"{self.pyinstaller_path}" --clean --noconfirm "{self.spec_file}"'
        else:
            # Última tentativa: usar pyinstaller diretamente
            command = f'pyinstaller --clean --noconfirm "{self.spec_file}"'
        
        if not self.run_command(command, "Executando PyInstaller com arquivo spec"):
            return False
        
        self.print_success("Executavel compilado com sucesso!")
        return True
    
    def create_installer_package(self):
        """Cria um pacote de instalação"""
        self.print_step("Criando pacote de distribuição")
        
        # Criar diretório de release
        release_dir = self.agent_dir / "release"
        if release_dir.exists():
            shutil.rmtree(release_dir)
        release_dir.mkdir()
        
        # Copiar executável
        exe_name = "HiProd-Agent.exe" if platform.system() == "Windows" else "HiProd-Agent"
        exe_source = self.dist_dir / exe_name
        exe_dest = release_dir / exe_name
        
        if exe_source.exists():
            shutil.copy2(exe_source, exe_dest)
            print(f"[OK] Executavel copiado: {exe_dest}")
        else:
            self.print_error(f"Executavel nao encontrado: {exe_source}")
            return False
        
        # Copiar arquivo de configuração
        config_source = self.agent_dir / "config.example"
        config_dest = release_dir / "config.example"
        
        if config_source.exists():
            shutil.copy2(config_source, config_dest)
            print(f"[OK] Configuracao copiada: {config_dest}")
        
        # Criar README de instalação
        readme_content = f"""# HiProd Agent - Instalação

## Como usar:

1. **Configuração (PRIMEIRA VEZ):**
   - Na primeira execução, o arquivo `.env` será criado automaticamente
   - Abra o arquivo `.env` que foi criado
   - Edite apenas a URL da API se necessário:
     - API_URL=http://192.241.155.236:8010 → Ajuste se necessário
   - ⚠️ NÃO é mais necessário configurar credenciais!
   - A API identifica o usuário automaticamente pelo nome do usuário do Windows
   - Salve o arquivo e execute novamente

2. **Execução:**
   - Execute `{exe_name}`
   - O agent iniciará automaticamente
   - Verifique os logs para confirmar funcionamento

3. **Instalação como Serviço (Opcional):**
   - Execute como Administrador
   - O agent pode ser configurado para iniciar com o Windows

## Arquivos inclusos:
- `{exe_name}`: Executável principal
- `config.example`: Exemplo de configuração
- `README.txt`: Este arquivo

## Suporte:
- Documentação: README.md do projeto
- Issues: GitHub do projeto HiProd

Versão: 1.0.0
Data: {time.strftime('%d/%m/%Y %H:%M')}
"""
        
        readme_path = release_dir / "README.txt"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"[OK] README criado: {readme_path}")
        
        # Mostrar informações do pacote
        exe_size = exe_dest.stat().st_size / (1024 * 1024)  # MB
        print(f"\n[PACKAGE] Pacote criado em: {release_dir}")
        print(f"[SIZE] Tamanho do executavel: {exe_size:.1f} MB")
        
        return True
    
    def build(self):
        """Processo completo de build"""
        start_time = time.time()
        
        print("HiProd Agent - Build para Executavel")
        print("=" * 60)
        
        # Verificar pré-requisitos
        if not self.check_prerequisites():
            return False
        
        # Limpar builds anteriores
        self.clean_build_dirs()
        
        # Compilar executável
        if not self.build_executable():
            return False
        
        # Criar pacote de distribuição
        if not self.create_installer_package():
            return False
        
        # Sucesso
        elapsed_time = time.time() - start_time
        print(f"\n[SUCCESS] Build concluido com sucesso!")
        print(f"[TIME] Tempo total: {elapsed_time:.1f} segundos")
        print(f"[PACKAGE] Pacote disponivel em: {self.agent_dir / 'release'}")
        
        return True

def main():
    """Função principal"""
    try:
        builder = AgentBuilder()
        success = builder.build()
        
        if not success:
            print("\n[ERROR] Build falhou!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[WARN] Build interrompido pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
