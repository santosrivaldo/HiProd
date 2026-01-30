#!/usr/bin/env python3
"""
Módulo de Detecção Facial para HiProd Agent
Verifica se há uma pessoa em frente à câmera usando detecção facial
Rastreia o tempo de presença do colaborador
"""

import cv2
import sys
import os
import time
from datetime import datetime

# Detectar se está rodando como executável
IS_EXECUTABLE = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Classe para rastrear tempo de presença
class FacePresenceTracker:
    """
    Rastreia o tempo que uma pessoa passa em frente à câmera.
    Mantém um histórico de detecções e calcula o tempo total de presença.
    """
    def __init__(self):
        self.presence_start = None  # Timestamp quando a presença começou
        self.last_detection = None  # Timestamp da última detecção
        self.total_presence_time = 0  # Tempo total acumulado em segundos
        self.last_check_time = None  # Timestamp da última verificação
        self.check_interval = 60  # Intervalo entre verificações (60 segundos = 1 minuto)
        self.presence_threshold = 3  # Número de detecções consecutivas para confirmar presença
        
    def update_presence(self, face_detected, check_time=None):
        """
        Atualiza o estado de presença baseado na detecção facial.
        
        Args:
            face_detected: bool - Se uma face foi detectada
            check_time: float - Timestamp da verificação (opcional, usa time.time() se None)
        
        Returns:
            dict: Informações sobre o estado atual de presença
        """
        if check_time is None:
            check_time = time.time()
        
        current_time = check_time
        
        if face_detected:
            # Face detectada
            if self.last_detection is None:
                # Primeira detecção - iniciar rastreamento
                self.presence_start = current_time
                self.last_detection = current_time
            else:
                # Continuidade de presença - atualizar última detecção
                time_since_last = current_time - self.last_detection
                
                # Se passou muito tempo desde a última detecção, reiniciar
                if time_since_last > self.check_interval * 2:
                    # Presença interrompida e retomada
                    if self.presence_start is not None:
                        # Adicionar tempo acumulado antes de reiniciar
                        self.total_presence_time += self.last_detection - self.presence_start
                    self.presence_start = current_time
                
                self.last_detection = current_time
        else:
            # Nenhuma face detectada
            if self.last_detection is not None:
                # Havia presença antes - finalizar período
                time_since_last = current_time - self.last_detection
                
                if time_since_last > self.check_interval * 2:
                    # Presença definitivamente encerrada
                    if self.presence_start is not None:
                        self.total_presence_time += self.last_detection - self.presence_start
                    self.presence_start = None
                    self.last_detection = None
        
        self.last_check_time = current_time
        
        # Calcular tempo de presença atual
        current_presence_time = 0
        if self.presence_start is not None and self.last_detection is not None:
            current_presence_time = self.last_detection - self.presence_start
        
        return {
            'is_present': face_detected and self.last_detection is not None,
            'current_session_time': current_presence_time,
            'total_presence_time': self.total_presence_time + current_presence_time,
            'last_detection': self.last_detection,
            'presence_start': self.presence_start
        }
    
    def get_presence_time(self):
        """
        Retorna o tempo total de presença acumulado (em segundos).
        Inclui o tempo da sessão atual se houver presença ativa.
        
        Returns:
            float: Tempo total em segundos
        """
        current_presence = 0
        if self.presence_start is not None and self.last_detection is not None:
            current_presence = self.last_detection - self.presence_start
        
        return self.total_presence_time + current_presence
    
    def reset(self):
        """Reseta o rastreamento (útil ao trocar de usuário)"""
        # Salvar tempo atual antes de resetar
        final_time = self.get_presence_time()
        self.presence_start = None
        self.last_detection = None
        self.total_presence_time = 0
        self.last_check_time = None
        return final_time

# Instância global do tracker
_presence_tracker = FacePresenceTracker()

def get_haarcascade_path():
    """
    Retorna o caminho para o arquivo haarcascade_frontalface_default.xml
    Tenta encontrar em vários locais possíveis
    """
    # Lista de possíveis locais
    possible_paths = []
    
    # Se for executável, procurar primeiro em sys._MEIPASS (onde PyInstaller coloca os dados)
    if IS_EXECUTABLE:
        try:
            meipass = sys._MEIPASS
            possible_paths.extend([
                os.path.join(meipass, 'haarcascade_frontalface_default.xml'),
                os.path.join(meipass, 'data', 'haarcascade_frontalface_default.xml'),
                # Procurar no caminho do OpenCV dentro do _MEIPASS
                os.path.join(meipass, 'cv2', 'data', 'haarcascades', 'haarcascade_frontalface_default.xml'),
            ])
            
            # Tentar usar cv2.data mesmo quando executável (pode funcionar se PyInstaller incluiu corretamente)
            try:
                possible_paths.append(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
            except:
                pass
        except:
            pass
        
        # Também procurar no diretório do executável
        base_dir = os.path.dirname(sys.executable)
        possible_paths.extend([
            os.path.join(base_dir, 'haarcascade_frontalface_default.xml'),
            os.path.join(base_dir, 'data', 'haarcascade_frontalface_default.xml'),
        ])
    
    # Procurar no diretório do script (quando rodando como script Python)
    if not IS_EXECUTABLE:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths.extend([
            os.path.join(script_dir, 'haarcascade_frontalface_default.xml'),
            os.path.join(script_dir, 'data', 'haarcascade_frontalface_default.xml'),
        ])
    
    # Procurar no diretório de dados do OpenCV (instalação padrão)
    # cv2 já está importado no topo do arquivo
    try:
        possible_paths.append(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
    except:
        pass
    
    # Verificar cada caminho
    for path in possible_paths:
        if os.path.exists(path):
            if IS_EXECUTABLE:
                print(f"[FACE] Haarcascade encontrado em: {path}")
            return path
    
    # Se não encontrou, mostrar informações de debug quando executável
    if IS_EXECUTABLE:
        print(f"[FACE] AVISO: Haarcascade não encontrado em nenhum dos caminhos:")
        for i, path in enumerate(possible_paths, 1):
            print(f"  {i}. {path} (existe: {os.path.exists(path)})")
        try:
            print(f"[FACE] sys._MEIPASS: {sys._MEIPASS}")
            print(f"[FACE] sys.executable: {sys.executable}")
        except:
            pass
    
    # Se não encontrou, retornar None (será tratado no código)
    return None

def check_face_presence(timeout=5, camera_index=0):
    """
    Verifica se há uma pessoa em frente à câmera usando detecção facial.
    
    Args:
        timeout: Tempo máximo em segundos para tentar detectar uma face
        camera_index: Índice da câmera a ser usada (padrão: 0)
    
    Returns:
        bool: True se uma face foi detectada, False caso contrário
    """
    try:
        # Obter caminho do classificador
        cascade_path = get_haarcascade_path()
        face_cascade = None
        
        if cascade_path is None:
            # Tentar usar o caminho padrão do OpenCV
            try:
                # cv2 já está importado no topo do arquivo, apenas acessar cv2.data
                default_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
                if IS_EXECUTABLE:
                    print(f"[FACE] Procurando haarcascade em: {default_path}")
                face_cascade = cv2.CascadeClassifier(default_path)
                if face_cascade.empty():
                    if IS_EXECUTABLE:
                        print(f"[FACE] Erro: Classificador vazio em {default_path}")
                    return False
            except Exception as e:
                if IS_EXECUTABLE:
                    print(f"[FACE] Erro ao usar caminho padrão do OpenCV: {e}")
                return False
        else:
            if IS_EXECUTABLE:
                print(f"[FACE] Usando haarcascade encontrado em: {cascade_path}")
            face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Verificar se o classificador foi carregado corretamente
        if face_cascade is None or face_cascade.empty():
            if IS_EXECUTABLE:
                print(f"[FACE] Erro: Classificador de faces vazio ou inválido em: {cascade_path}")
            return False
        
        # Tentar abrir a câmera
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"[FACE] Erro: Não foi possível abrir a câmera (índice {camera_index})")
            return False
        
        # Configurar resolução (reduzir para melhor performance)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        start_time = time.time()
        face_detected = False
        
        # Tentar detectar face por até 'timeout' segundos
        while (time.time() - start_time) < timeout:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Converter para escala de cinza (mais rápido para detecção)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detectar faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Se detectou pelo menos uma face
            if len(faces) > 0:
                face_detected = True
                print(f"[FACE] ✓ Face detectada! ({len(faces)} face(s) encontrada(s))")
                break
            
            # Pequeno delay para não sobrecarregar a CPU
            time.sleep(0.1)
        
        # Liberar recursos
        cap.release()
        
        if not face_detected:
            print("[FACE] ✗ Nenhuma face detectada no tempo limite")
        
        return face_detected
        
    except Exception as e:
        print(f"[FACE] Erro durante detecção facial: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_face_presence_silent(timeout=5, camera_index=0):
    """
    Versão silenciosa da verificação de presença (sem prints).
    Útil quando executado como executável.
    
    Args:
        timeout: Tempo máximo em segundos para tentar detectar uma face
        camera_index: Índice da câmera a ser usada (padrão: 0)
    
    Returns:
        bool: True se uma face foi detectada, False caso contrário
    """
    try:
        # Obter caminho do classificador
        cascade_path = get_haarcascade_path()
        
        if cascade_path is None:
            try:
                # cv2 já está importado no topo do arquivo
                default_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
                face_cascade = cv2.CascadeClassifier(default_path)
                if face_cascade.empty():
                    return False
            except:
                return False
        else:
            face_cascade = cv2.CascadeClassifier(cascade_path)
            if face_cascade.empty():
                return False
        
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            return False
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        start_time = time.time()
        face_detected = False
        
        while (time.time() - start_time) < timeout:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) > 0:
                face_detected = True
                break
            
            time.sleep(0.1)
        
        cap.release()
        return face_detected
        
    except Exception as e:
        return False

def get_presence_tracker():
    """
    Retorna a instância global do rastreador de presença.
    
    Returns:
        FacePresenceTracker: Instância do tracker
    """
    return _presence_tracker

def reset_presence_tracker():
    """
    Reseta o rastreador de presença e retorna o tempo total acumulado.
    
    Returns:
        float: Tempo total de presença antes do reset (em segundos)
    """
    return _presence_tracker.reset()

if __name__ == '__main__':
    # Teste simples
    print("[FACE] Testando detecção facial...")
    print("[FACE] Por favor, posicione-se em frente à câmera")
    result = check_face_presence(timeout=10)
    if result:
        print("[FACE] ✓ Teste bem-sucedido! Face detectada.")
    else:
        print("[FACE] ✗ Teste falhou. Nenhuma face detectada.")

