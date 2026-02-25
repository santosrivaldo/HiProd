#!/usr/bin/env python3
"""
Botao flutuante do HiProd Agent.
Contem: Popup, FloatingButton, create_floating_button.
Sem dependência de lock_screen (tela de bloqueio removida).
"""

import tkinter as tk
import os
import sys
import threading
from datetime import datetime

# Estado do agent (usado para pausa/parada sem lock_screen)
AGENT_PAUSED = False
AGENT_RUNNING = True
AGENT_THREAD = None


def check_timeman_status(user_id):
    """
    Consulta o status do expediente Bitrix (Timeman) na API.
    user_id: usuario_monitorado_id (ID do usuário monitorado).
    Retorna dict com status (OPENED/PAUSED/CLOSED), time_start, duration, time_leaks, worked_today.
    """
    api_url = os.getenv('API_URL', 'https://hiprod.grupohi.com.br').rstrip('/')
    url = f"{api_url}/api/timeman-status"
    default = {
        'status': 'CLOSED',
        'time_start': None,
        'duration': '00:00:00',
        'time_leaks': '00:00:00',
        'worked_today': False,
    }
    if not user_id:
        return default
    try:
        import urllib.request
        import urllib.parse
        req = urllib.request.Request(
            f"{url}?{urllib.parse.urlencode({'usuario_monitorado_id': user_id})}",
            headers={'Accept': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                import json
                data = json.loads(resp.read().decode())
                return {
                    'status': data.get('status', 'CLOSED'),
                    'time_start': data.get('time_start'),
                    'duration': data.get('duration', '00:00:00'),
                    'time_leaks': data.get('time_leaks', '00:00:00'),
                    'worked_today': bool(data.get('worked_today', False)),
                }
    except Exception as e:
        if not getattr(sys, 'frozen', False):
            print(f"[BITRIX] Erro ao consultar timeman-status: {e}")
    return default


def get_user_manager(user_id):
    """Stub: retorna dados do gestor quando Bitrix/lock_screen não está disponível."""
    return None


def request_manager_approval(user_id, reason, manager_id):
    """Stub: solicitação de aprovação quando Bitrix/lock_screen não está disponível."""
    return {'success': False}


def fetch_pending_agent_messages(user_id):
    """Consulta a API por mensagens pendentes para o agente (exibidas na tela)."""
    api_url = os.getenv('API_URL', 'https://hiprod.grupohi.com.br').rstrip('/')
    url = f"{api_url}/agent-messages/pending"
    if not user_id:
        return []
    try:
        import urllib.request
        import urllib.parse
        req = urllib.request.Request(
            f"{url}?{urllib.parse.urlencode({'usuario_monitorado_id': user_id})}",
            headers={'Accept': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                import json
                return json.loads(resp.read().decode())
    except Exception as e:
        if not getattr(sys, 'frozen', False):
            print(f"[AGENT-MESSAGES] Erro ao buscar pendentes: {e}")
    return []


def mark_agent_message_delivered(message_id, user_id):
    """Marca mensagem como entregue na API (após exibir na tela)."""
    api_url = os.getenv('API_URL', 'https://hiprod.grupohi.com.br').rstrip('/')
    url = f"{api_url}/agent-messages/{message_id}/deliver"
    if not user_id:
        return False
    try:
        import urllib.request
        import json
        data = json.dumps({'usuario_monitorado_id': user_id}).encode()
        req = urllib.request.Request(url, data=data, method='POST', headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        if not getattr(sys, 'frozen', False):
            print(f"[AGENT-MESSAGES] Erro ao marcar entrega: {e}")
    return False


class Popup:
    """
    Classe única para criar popups com layout consistente
    Reutilizável para todos os tipos de popup no sistema
    """
    
    # Cores padrão do tema
    BG_COLOR = '#1a1a2e'
    FRAME_COLOR = '#252542'
    TEXT_PRIMARY = '#ffffff'
    TEXT_SECONDARY = '#8b8b9e'
    ACCENT_GREEN = '#4ade80'
    ACCENT_YELLOW = '#fbbf24'
    ACCENT_ORANGE = '#f59e0b'
    ACCENT_RED = '#dc2626'
    ACCENT_BLUE = '#4361ee'
    SEPARATOR_COLOR = '#3d3d5c'
    
    def __init__(self, parent=None, title="HiProd", width=240, height=320, position='auto'):
        """
        Cria um popup com layout padrão
        
        Args:
            parent: Janela pai (Tk ou Toplevel)
            title: Título do popup
            width: Largura do popup
            height: Altura do popup
            position: Posição ('auto', 'center', 'top-right', ou tupla (x, y))
        """
        # Criar janela
        if parent:
            self.root = tk.Toplevel(parent)
        else:
            self.root = tk.Toplevel() if tk._default_root else tk.Tk()
        
        self.root.title(title)
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        self.root.configure(bg=self.BG_COLOR)
        
        # Configurar tamanho e posição
        self.width = width
        self.height = height
        self._set_position(position)
        
        # Frame principal
        self.main_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        self.main_frame.pack(fill='both', expand=True, padx=12, pady=12)
        
        # Componentes do popup
        self.header_frame = None
        self.content_frame = None
        self.buttons_frame = None
        self.widgets = {}  # Dicionário para armazenar widgets criados
        
    def _set_position(self, position):
        """Define a posição do popup"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if position == 'center':
            x = (screen_width - self.width) // 2
            y = (screen_height - self.height) // 2
        elif position == 'top-right':
            x = screen_width - self.width - 20
            y = 100
        elif isinstance(position, tuple):
            x, y = position
        else:  # 'auto' - posicionar baseado no parent
            if hasattr(self.root, 'winfo_parent'):
                try:
                    parent = self.root.nametowidget(self.root.winfo_parent())
                    btn_x = parent.winfo_x()
                    btn_y = parent.winfo_y()
                    btn_size = getattr(parent, 'btn_size', 70) if hasattr(parent, 'btn_size') else 70
                    x = btn_x - self.width - 10
                    y = btn_y - (self.height - btn_size)
                except:
                    x = screen_width - self.width - 20
                    y = screen_height - self.height - 80
            else:
                x = screen_width - self.width - 20
                y = screen_height - self.height - 80
        
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
    
    def add_header(self, title, subtitle=None, icon=None):
        """Adiciona cabeçalho ao popup"""
        if self.header_frame:
            self.header_frame.destroy()
        
        self.header_frame = tk.Frame(self.main_frame, bg=self.BG_COLOR)
        self.header_frame.pack(fill='x', pady=(0, 8))
        
        if icon:
            tk.Label(
                self.header_frame,
                text=icon,
                font=('Segoe UI', 28),
                fg=self.ACCENT_ORANGE,
                bg=self.BG_COLOR
            ).pack()
        
        tk.Label(
            self.header_frame,
            text=title,
            font=('Segoe UI', 12, 'bold'),
            fg=self.TEXT_PRIMARY,
            bg=self.BG_COLOR
        ).pack()
        
        if subtitle:
            tk.Label(
                self.header_frame,
                text=subtitle,
                font=('Segoe UI', 9),
                fg=self.TEXT_SECONDARY,
                bg=self.BG_COLOR
            ).pack(pady=(2, 0))
        
        return self.header_frame
    
    def add_separator(self):
        """Adiciona separador visual"""
        tk.Frame(self.main_frame, height=1, bg=self.SEPARATOR_COLOR).pack(fill='x', pady=6)
    
    def add_content_frame(self):
        """Cria e retorna um frame de conteúdo"""
        if self.content_frame:
            self.content_frame.destroy()
        
        self.content_frame = tk.Frame(self.main_frame, bg=self.BG_COLOR)
        self.content_frame.pack(fill='both', expand=True)
        return self.content_frame
    
    def add_info_box(self, label, value, color=None):
        """Adiciona uma caixa de informação (label + valor)"""
        if not self.content_frame:
            self.add_content_frame()
        
        info_frame = tk.Frame(self.content_frame, bg=self.FRAME_COLOR, padx=12, pady=8)
        info_frame.pack(fill='x', pady=(0, 6))
        
        tk.Label(
            info_frame,
            text=label,
            font=('Segoe UI', 9),
            fg=self.TEXT_SECONDARY,
            bg=self.FRAME_COLOR
        ).pack(anchor='w')
        
        tk.Label(
            info_frame,
            text=value,
            font=('Segoe UI', 16, 'bold'),
            fg=color or self.ACCENT_GREEN,
            bg=self.FRAME_COLOR
        ).pack(anchor='w')
        
        return info_frame
    
    def add_button(self, text, command, bg_color=None, is_primary=True):
        """Adiciona um botão ao popup"""
        if not self.buttons_frame:
            self.buttons_frame = tk.Frame(self.main_frame, bg=self.BG_COLOR)
            self.buttons_frame.pack(fill='x', pady=(10, 0))
        
        if bg_color is None:
            bg_color = self.ACCENT_RED if is_primary else self.ACCENT_ORANGE
        
        active_bg = self._darken_color(bg_color)
        
        btn = tk.Button(
            self.buttons_frame,
            text=text,
            font=('Segoe UI', 12, 'bold'),
            bg=bg_color,
            fg='white',
            activebackground=active_bg,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=command,
            pady=12
        )
        btn.pack(fill='x', pady=(0, 8))
        
        # Hover effect
        def on_enter(e):
            btn.config(bg=active_bg)
        def on_leave(e):
            btn.config(bg=bg_color)
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def add_label(self, text, font_size=9, color=None, bg=None):
        """Adiciona um label ao conteúdo"""
        if not self.content_frame:
            self.add_content_frame()
        
        label = tk.Label(
            self.content_frame,
            text=text,
            font=('Segoe UI', font_size),
            fg=color or self.TEXT_SECONDARY,
            bg=bg or self.BG_CONTENT,
        )
        label.pack(anchor='w', pady=(0, 4))
        return label

    # --- Fim da classe Popup ---


class FloatingButton:
    """Botão flutuante do HiProd Agent que fica sempre visível"""
    
    def __init__(self, user_id=None, on_pause_callback=None):
        self.user_id = user_id
        self.on_pause_callback = on_pause_callback
        self.root = None
        self.popup = None
        self.popup_visible = False
        
        # Estado do cronômetro (dados locais)
        self.is_paused = False
        self.work_start_time = datetime.now()
        self.pause_start_time = None
        self.total_pause_seconds = 0
        self.current_pause_seconds = 0
        
        # Flag para indicar que o expediente foi finalizado
        self.workday_ended = False
        # Janela de expediente finalizado/contador (pode ser minimizada; abre ao clicar no botão flutuante)
        self._countdown_window = None
        
        # Dados do Bitrix24 (garantir formato correto desde o início)
        self.bitrix_duration = "00:00:00"
        self.bitrix_pause_duration = "00:00:00"
        self.bitrix_status = "CLOSED"
        self.last_bitrix_update = None
        
        # Flag para indicar se os dados já foram buscados
        self._data_fetched = False
        
        # Labels para atualização
        self.work_time_label = None
        self.pause_time_label = None
        self.status_label = None
        
        self._create_floating_button()
        
        # Buscar dados do Bitrix em background (não bloqueia a UI)
        if self.root:
            self.root.after(0, self._fetch_bitrix_data_async)
        
        # Agendar atualização do status Bitrix a cada 2 minutos
        self._schedule_bitrix_update()
        # Mensagens do gestor: verificar a cada 10 minutos (primeira em 1 min)
        self._schedule_agent_messages_check()
    
    def _format_time_safe(self, time_str):
        """Formata string de tempo garantindo formato HH:MM:SS"""
        if not time_str or not isinstance(time_str, str):
            return "00:00:00"
        # Remover espaços e caracteres inválidos
        time_str = time_str.strip()
        # Verificar se tem formato válido
        if ':' not in time_str:
            return "00:00:00"
        parts = time_str.split(':')
        if len(parts) != 3:
            return "00:00:00"
        # Validar que cada parte é numérica
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except (ValueError, IndexError):
            return "00:00:00"
    
    def _update_time_labels(self):
        """Atualiza os labels de tempo no popup de forma centralizada"""
        if not self.popup_visible or not self.popup:
            return
        
        # Calcular tempo trabalhado e pausa em tempo real se possível
        work_time_str = self.bitrix_duration
        pause_time_str = self.bitrix_pause_duration
        
        # Se temos work_start_time, calcular em tempo real (mesmo em pausa)
        if hasattr(self, 'work_start_time') and self.work_start_time:
            try:
                current_dt = datetime.now()
                total_seconds = (current_dt - self.work_start_time).total_seconds()
                
                # Subtrair pausas
                base_pause = self._parse_time_to_seconds(self.bitrix_pause_duration)
                pause_seconds = base_pause
                
                # Se estiver em pausa local, adicionar tempo da pausa atual
                if self.is_paused and self.pause_start_time:
                    self.current_pause_seconds = (current_dt - self.pause_start_time).total_seconds()
                    pause_seconds += self.current_pause_seconds
                
                work_seconds = max(0, total_seconds - pause_seconds)
                work_time_str = self._format_time(work_seconds)
                pause_time_str = self._format_time(pause_seconds)
            except Exception as e:
                # Se der erro, usar dados do Bitrix
                pass
        
        # Formatar e atualizar tempo trabalhado
        if self.work_time_label:
            formatted_time = self._format_time_safe(work_time_str)
            self.work_time_label.config(text=formatted_time)
        
        # Formatar e atualizar tempo de pausa
        if self.pause_time_label:
            formatted_time = self._format_time_safe(pause_time_str)
            self.pause_time_label.config(text=formatted_time)
        
        # Atualizar label de última atualização
        if hasattr(self, 'update_label') and self.update_label:
            if self.last_bitrix_update:
                self.update_label.config(
                    text=f"Atualizado: {self.last_bitrix_update.strftime('%H:%M')}"
                )
            else:
                self.update_label.config(text="Atualizado: --:--")
    
    def _fetch_bitrix_data(self, update_ui=True):
        """Busca dados atualizados do Bitrix24 (usa stub se Bitrix não disponível)"""
        try:
            print("[BITRIX] Buscando dados atualizados do Bitrix24...")
            timeman_info = check_timeman_status(self.user_id)
            
            if timeman_info:
                self.bitrix_status = timeman_info.get('status', 'CLOSED')
                
                # Atualizar hora de início se disponível (fazer isso primeiro)
                time_start = timeman_info.get('time_start')
                if time_start:
                    self.set_start_time(time_start)
                
                # Atualizar tempo trabalhado do Bitrix
                duration_from_bitrix = timeman_info.get('duration', '00:00:00')
                calculated_duration = None
                
                # Se expediente está aberto, calcular duração localmente (mais preciso e atualizado)
                if self.bitrix_status == 'OPENED' and time_start:
                    try:
                        # Calcular duração desde o início
                        start_dt = None
                        if isinstance(time_start, str):
                            # Formato ISO com timezone: 2025-11-27T15:25:50-03:00
                            try:
                                start_dt = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
                            except:
                                # Tentar formato sem timezone
                                try:
                                    start_dt = datetime.strptime(time_start, '%Y-%m-%dT%H:%M:%S')
                                except:
                                    # Tentar formato com milissegundos
                                    try:
                                        start_dt = datetime.strptime(time_start.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                                    except:
                                        print(f"[BITRIX] Não foi possível fazer parse de time_start: {time_start}")
                        
                        if start_dt:
                            # Remover timezone para comparação
                            if start_dt.tzinfo:
                                start_dt = start_dt.replace(tzinfo=None)
                            
                            current_dt = datetime.now()
                            if start_dt <= current_dt:
                                total_seconds = (current_dt - start_dt).total_seconds()
                                # Subtrair pausas
                                time_leaks = timeman_info.get('time_leaks', '00:00:00')
                                pause_seconds = self._parse_time_to_seconds(time_leaks)
                                work_seconds = max(0, total_seconds - pause_seconds)
                                calculated_duration = self._format_time(work_seconds)
                                print(f"[BITRIX] Duração calculada localmente: {calculated_duration} (início: {time_start}, agora: {current_dt.strftime('%H:%M:%S')})")
                    except Exception as e:
                        print(f"[BITRIX] Erro ao calcular duração local: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Usar duração calculada se disponível, senão usar a do Bitrix
                if calculated_duration:
                    self.bitrix_duration = calculated_duration
                elif duration_from_bitrix and duration_from_bitrix != '00:00:00':
                    self.bitrix_duration = duration_from_bitrix
                    print(f"[BITRIX] Duração do Bitrix: {duration_from_bitrix}")
                else:
                    self.bitrix_duration = duration_from_bitrix
                    print(f"[BITRIX] Duração: {self.bitrix_duration}")
                
                # Atualizar tempo de pausa do Bitrix
                time_leaks = timeman_info.get('time_leaks', '00:00:00')
                if time_leaks:
                    self.bitrix_pause_duration = time_leaks
                    print(f"[BITRIX] Pausas do Bitrix: {time_leaks}")
                
                # Atualizar status de pausa baseado no Bitrix
                if self.bitrix_status == 'PAUSED':
                    self.is_paused = True
                elif self.bitrix_status == 'OPENED':
                    self.is_paused = False
                
                self.last_bitrix_update = datetime.now()
                self._data_fetched = True
                print(f"[BITRIX] ✓ Dados atualizados às {self.last_bitrix_update.strftime('%H:%M:%S')}")
                
                # Garantir que os valores estão no formato correto usando função centralizada
                self.bitrix_duration = self._format_time_safe(self.bitrix_duration)
                self.bitrix_pause_duration = self._format_time_safe(self.bitrix_pause_duration)
                
                # Atualizar UI se solicitado e popup estiver visível
                if update_ui and self.popup_visible:
                    self._update_popup_ui()
                    self._update_time_labels()
                
        except Exception as e:
            print(f"[BITRIX] Erro ao buscar dados: {e}")
            import traceback
            traceback.print_exc()
    
    def _fetch_bitrix_data_async(self):
        """Busca dados do Bitrix em thread separada para não travar o botão flutuante."""
        def run():
            self._fetch_bitrix_data(update_ui=False)
            if self.root:
                try:
                    self.root.after(0, self._after_bitrix_fetch)
                except tk.TclError:
                    pass  # janela já fechada
        threading.Thread(target=run, daemon=True).start()
    
    def _after_bitrix_fetch(self):
        """Atualiza a UI no fio principal após buscar dados do Bitrix."""
        try:
            if self.popup_visible:
                self._update_popup_ui()
                self._update_time_labels()
        except Exception:
            pass
    
    def _schedule_bitrix_update(self):
        """Agenda atualização do status Bitrix a cada 2 minutos"""
        def update_bitrix():
            self._fetch_bitrix_data_async()
            if self.root:
                self.root.after(120000, update_bitrix)  # 2 min
        
        if self.root:
            self.root.after(120000, update_bitrix)

    def _schedule_agent_messages_check(self):
        """Agenda verificação de mensagens pendentes a cada 10 minutos (primeira em 1 min)."""
        def check():
            self._check_agent_messages()
            if self.root:
                self.root.after(600000, check)  # 10 min = 600000 ms
        if self.root:
            self.root.after(60000, check)  # primeira em 1 min

    def _check_agent_messages(self):
        """Busca mensagens pendentes na API e exibe uma a uma de forma interativa."""
        if not self.user_id:
            return
        messages = fetch_pending_agent_messages(self.user_id)
        for msg in messages:
            mid = msg.get('id')
            titulo = msg.get('titulo', 'Mensagem')
            mensagem = msg.get('mensagem', '')
            tipo = msg.get('tipo', 'info')
            self._show_agent_message_popup(titulo, mensagem, tipo, mid)

    def _show_agent_message_popup(self, titulo, mensagem, tipo, message_id):
        """Exibe uma mensagem do gestor em janela interativa; ao fechar marca como entregue."""
        if not self.root:
            return
        colors = {'urgente': ('#dc2626', '#fef2f2'), 'alerta': ('#f59e0b', '#fffbeb'), 'info': ('#2563eb', '#eff6ff')}
        fg, bg = colors.get(tipo, colors['info'])
        win = tk.Toplevel(self.root)
        win.title(titulo)
        win.attributes('-topmost', True)
        win.configure(bg='#1a1a2e')
        win.geometry('420x220')
        frame = tk.Frame(win, bg='#1a1a2e', padx=16, pady=16)
        frame.pack(fill='both', expand=True)
        tk.Label(frame, text=titulo, font=('Segoe UI', 12, 'bold'), fg=fg, bg='#1a1a2e').pack(anchor='w')
        text = tk.Text(frame, wrap='word', height=6, font=('Segoe UI', 10), fg='#e5e7eb', bg='#252542',
                      relief='flat', padx=8, pady=8)
        text.pack(fill='both', expand=True, pady=(8, 12))
        text.insert('1.0', mensagem)
        text.config(state='disabled')
        def on_ok():
            win.destroy()
            if message_id and self.user_id:
                mark_agent_message_delivered(message_id, self.user_id)
        btn = tk.Button(frame, text='OK', command=on_ok, font=('Segoe UI', 10), bg=fg, fg='white',
                        activebackground=fg, cursor='hand2', relief='flat', padx=20, pady=6)
        btn.pack()
        win.transient(self.root)
        win.grab_set()
        win.focus_force()
    
    def _create_floating_button(self):
        """Cria o botão flutuante"""
        # Verificar se já existe um root válido
        if hasattr(self, 'root') and self.root:
            try:
                # Verificar se o root ainda é válido
                self.root.winfo_exists()
                # Verificar se já tem o tamanho correto
                current_geometry = self.root.geometry()
                if '70x70' in current_geometry:
                    print("[INFO] Botão flutuante já existe com tamanho correto, reutilizando...")
                    return
                else:
                    # Tamanho incorreto, corrigir
                    print(f"[INFO] Botão flutuante existe mas com tamanho incorreto ({current_geometry}), corrigindo...")
                    btn_size = 70
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    x_pos = screen_width - btn_size - 20
                    y_pos = screen_height - btn_size - 80
                    self.root.geometry(f"{btn_size}x{btn_size}+{x_pos}+{y_pos}")
                    self.btn_size = btn_size
                    return
            except:
                # Root foi destruído, criar novo
                self.root = None
        
        self.root = tk.Toplevel() if tk._default_root else tk.Tk()
        
        # Configurar janela flutuante
        self.root.title("HiProd")
        self.root.overrideredirect(True)  # Remove bordas
        self.root.attributes('-topmost', True)  # Sempre no topo
        self.root.attributes('-alpha', 0.95)  # Levemente transparente
        
        # Tamanho e posição (canto inferior direito)
        btn_size = 70  # Tamanho maior e mais visível do botão
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_pos = screen_width - btn_size - 20
        y_pos = screen_height - btn_size - 80
        
        self.root.geometry(f"{btn_size}x{btn_size}+{x_pos}+{y_pos}")
        
        # Forçar fundo escuro na janela inteira (evita janela branca no Windows)
        self.root.configure(bg='#1a1a2e', highlightthickness=0)
        self.root.option_add('*Background', '#1a1a2e')
        self.root.option_add('*HighlightBackground', '#1a1a2e')
        self.root.option_add('*HighlightColor', '#1a1a2e')
        
        # Frame que preenche a janela com a cor de fundo (garante pintura)
        self._bg_frame = tk.Frame(self.root, bg='#1a1a2e', highlightthickness=0)
        self._bg_frame.pack(expand=True, fill='both', padx=0, pady=0)
        
        self.root.deiconify()
        self.root.lift()
        self.root.update_idletasks()
        self.root.update()
        
        # Armazenar tamanho do botão para uso em outras funções
        self.btn_size = btn_size
        
        # Verificar se o botão principal já existe
        if not hasattr(self, 'main_btn') or not self.main_btn:
            # Botão principal (dentro do frame de fundo)
            self.main_btn = tk.Button(
                self._bg_frame,
                text="Hi",
                font=('Segoe UI', 14, 'bold'),  # Fonte maior para botão de 70x70
                bg='#4361ee',
                fg='white',
                activebackground='#3f37c9',
                activeforeground='white',
                relief='flat',
                cursor='hand2',
                command=self._toggle_popup,
                bd=0,
                highlightthickness=0,
                highlightbackground='#1a1a2e',
                highlightcolor='#1a1a2e'
            )
            self.main_btn.pack(expand=True, fill='both', padx=2, pady=2)
            
            # Permitir arrastar o botão
            self.main_btn.bind('<Button-1>', self._start_drag)
            self.main_btn.bind('<B1-Motion>', self._drag)
            
            # Variáveis para arrastar
            self._drag_x = 0
            self._drag_y = 0
        
        # Iniciar atualização do cronômetro
        self._update_timer()
    
    def _start_drag(self, event):
        """Inicia o arraste do botão"""
        self._drag_x = event.x
        self._drag_y = event.y
    
    def _drag(self, event):
        """Arrasta o botão"""
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")
        
        # Se popup está visível, mover junto
        if self.popup_visible and self.popup and hasattr(self.popup, 'root'):
            btn_size = getattr(self, 'btn_size', 70)
            popup_width = self.popup.width
            popup_height = self.popup.height
            popup_x = x - popup_width - 10
            popup_y = y - (popup_height - btn_size)
            self.popup.root.geometry(f"+{popup_x}+{popup_y}")
    
    def _toggle_popup(self):
        """Abre ou fecha o popup"""
        if self.popup_visible:
            self._close_popup()
        else:
            self._open_popup()
    
    def _open_popup(self):
        """Abre o popup com informações e controles usando a classe Popup unificada"""
        if self.popup:
            try:
                if hasattr(self.popup, 'destroy'):
                    self.popup.destroy()
            except:
                pass
        
        # Buscar dados atualizados do Bitrix antes de criar o popup
        if not self._data_fetched:
            self._fetch_bitrix_data(update_ui=False)
            self.root.update_idletasks()
            self.root.update()
        
        # Garantir que os valores estão no formato correto antes de usar
        self.bitrix_duration = self._format_time_safe(self.bitrix_duration)
        self.bitrix_pause_duration = self._format_time_safe(self.bitrix_pause_duration)
        
        # Usar a classe Popup unificada (apenas informações de tempo, sem botões de intervalo/finalizar)
        self.popup = Popup(
            parent=self.root,
            title="HiProd Agent",
            width=320,
            height=280,
            position='auto'
        )
        
        # Acessar o frame principal da classe Popup
        main_frame = self.popup.main_frame
        
        # Cabeçalho com título e status
        header_frame = tk.Frame(main_frame, bg='#1a1a2e')
        header_frame.pack(fill='x', pady=(0, 8))
        
        tk.Label(
            header_frame,
            text="HiProd",
            font=('Segoe UI', 12, 'bold'),
            fg='#ffffff',
            bg='#1a1a2e'
        ).pack(side='left')
        
        # Status badge (conforme Bitrix: OPENED = ativo, PAUSED = pausa, CLOSED = finalizado)
        status_map = {'OPENED': ('● Expediente ativo', '#4ade80'), 'PAUSED': ('● Em pausa', '#fbbf24'), 'CLOSED': ('● Dia finalizado', '#8b8b9e')}
        st = status_map.get(self.bitrix_status, ('● Dia finalizado', '#8b8b9e'))
        status_text = st[0] if not self.is_paused else "● Em pausa (local)"
        status_color = '#fbbf24' if self.is_paused else st[1]
        self.status_label = tk.Label(
            header_frame,
            text=status_text,
            font=('Segoe UI', 9),
            fg=status_color,
            bg='#1a1a2e'
        )
        self.status_label.pack(side='right')
        
        # Separador
        tk.Frame(main_frame, height=1, bg='#3d3d5c').pack(fill='x', pady=6)
        
        # Calcular tempos em tempo real
        work_time_display = self.bitrix_duration
        pause_time_display = self.bitrix_pause_duration
        
        if hasattr(self, 'work_start_time') and self.work_start_time:
            try:
                current_dt = datetime.now()
                total_seconds = (current_dt - self.work_start_time).total_seconds()
                base_pause = self._parse_time_to_seconds(self.bitrix_pause_duration)
                pause_seconds = base_pause
                
                if self.is_paused and self.pause_start_time:
                    self.current_pause_seconds = (current_dt - self.pause_start_time).total_seconds()
                    pause_seconds += self.current_pause_seconds
                
                work_seconds = max(0, total_seconds - pause_seconds)
                work_time_display = self._format_time(work_seconds)
            except:
                pass
        
        if self.is_paused and self.pause_start_time:
            try:
                current_dt = datetime.now()
                self.current_pause_seconds = (current_dt - self.pause_start_time).total_seconds()
                base_pause = self._parse_time_to_seconds(self.bitrix_pause_duration)
                total_pause = base_pause + self.current_pause_seconds
                pause_time_display = self._format_time(total_pause)
            except:
                pass
        
        work_time_display = self._format_time_safe(work_time_display)
        pause_time_display = self._format_time_safe(pause_time_display)
        
        # Container dos tempos (lado a lado)
        times_frame = tk.Frame(main_frame, bg=Popup.BG_COLOR)
        times_frame.pack(fill='x', pady=8)
        
        # Tempo trabalhado (esquerda)
        work_frame = tk.Frame(times_frame, bg=Popup.FRAME_COLOR, padx=8, pady=6)
        work_frame.pack(side='left', expand=True, fill='both', padx=(0, 4))
        
        tk.Label(
            work_frame,
            text="⏱ Trabalhado",
            font=('Segoe UI', 9),
            fg=Popup.TEXT_SECONDARY,
            bg=Popup.FRAME_COLOR
        ).pack(anchor='center')
        
        self.work_time_label = tk.Label(
            work_frame,
            text=work_time_display,
            font=('Segoe UI', 16, 'bold'),
            fg=Popup.ACCENT_GREEN,
            bg=Popup.FRAME_COLOR
        )
        self.work_time_label.pack(anchor='center')
        
        # Tempo em pausa (direita)
        pause_frame = tk.Frame(times_frame, bg=Popup.FRAME_COLOR, padx=8, pady=6)
        pause_frame.pack(side='right', expand=True, fill='both', padx=(4, 0))
        
        tk.Label(
            pause_frame,
            text="☕ Pausas",
            font=('Segoe UI', 9),
            fg=Popup.TEXT_SECONDARY,
            bg=Popup.FRAME_COLOR
        ).pack(anchor='center')
        
        self.pause_time_label = tk.Label(
            pause_frame,
            text=pause_time_display,
            font=('Segoe UI', 16, 'bold'),
            fg=Popup.ACCENT_YELLOW,
            bg=Popup.FRAME_COLOR
        )
        self.pause_time_label.pack(anchor='center')
        
        # Info de última atualização
        update_text = ""
        if self.last_bitrix_update:
            update_text = f"Atualizado: {self.last_bitrix_update.strftime('%H:%M')}"
        self.update_label = tk.Label(
            main_frame,
            text=update_text,
            font=('Segoe UI', 7),
            fg='#5a5a7a',
            bg='#1a1a2e'
        )
        self.update_label.pack(anchor='e', pady=(0, 5))
        
        # Fechar ao clicar fora
        self.popup.root.bind('<FocusOut>', lambda e: self._schedule_close_check())
        
        self.popup_visible = True
        self.popup.root.focus_set()
        
        # Forçar atualização da UI após criar o popup
        # Isso garante que os valores sejam atualizados mesmo se foram buscados após a criação
        self.popup.root.after(100, lambda: self._update_popup_ui_after_open())
    
    def _update_popup_ui_after_open(self):
        """Atualiza a UI do popup logo após abrir, garantindo valores corretos"""
        if not self.popup_visible or not self.popup:
            return
        
        # Buscar dados atualizados
        self._fetch_bitrix_data(update_ui=False)
        
        # Atualizar labels usando função centralizada
        self._update_time_labels()
        
        # Atualizar status
        self._update_popup_ui()
    
    def _schedule_close_check(self):
        """Agenda verificação para fechar popup"""
        if self.popup:
            popup_root = self.popup.root if hasattr(self.popup, 'root') else self.popup
            if popup_root:
                popup_root.after(200, self._check_close_popup)
    
    def _check_close_popup(self):
        """Verifica se deve fechar o popup"""
        try:
            popup_root = self.popup.root if hasattr(self.popup, 'root') else self.popup
            if popup_root and not popup_root.focus_get():
                # Verificar se o foco está no botão principal
                focused = self.root.focus_get()
                if focused != self.main_btn:
                    pass  # Não fechar automaticamente por enquanto
        except:
            pass
    
    def _close_popup(self):
        """Fecha o popup"""
        if self.popup:
            try:
                if hasattr(self.popup, 'destroy'):
                    self.popup.destroy()
                elif hasattr(self.popup, 'root'):
                    self.popup.root.destroy()
            except:
                pass
            self.popup = None
        # Limpar referências de widgets do popup (evita usar botões/labels já destruídos em callbacks futuros)
        self.popup_visible = False
        self.pause_btn = None
        self.end_day_btn = None
        self.work_time_label = None
        self.pause_time_label = None
        self.status_label = None
    
    def _toggle_pause(self):
        """Alterna entre pausa e trabalho"""
        if not self.is_paused:
            self._start_pause()
        else:
            self._end_pause()
    
    def _start_pause(self):
        """Inicia a pausa (apenas local e agente; não bate ponto no Bitrix)"""
        global AGENT_PAUSED
        # 1. Buscar dados de ponto do Bitrix24 (só leitura)
        print("[INFO] Buscando dados do Bitrix24...")
        self._fetch_bitrix_data()
        
        # 2. Atualizar estado local
        self.is_paused = True
        self.pause_start_time = datetime.now()
        self.current_pause_seconds = 0
        
        # 3. Pausar o agente de envio de informações
        print("[INFO] Pausando agente de envio de informações...")
        AGENT_PAUSED = True
        try:
            # Usar caminho absoluto para garantir consistência
            flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.agent_pause_flag')
            print(f"[DEBUG] Criando flag de pausa em: {flag_file}")
            with open(flag_file, 'w') as f:
                f.write('PAUSED')
            print("[INFO] ✓ Flag de pausa criada - agente pausará envio de informações")
        except Exception as e:
            print(f"[WARN] Não foi possível criar flag de pausa: {e}")
        
        # 4. Buscar dados do Bitrix novamente
        self._fetch_bitrix_data()
        
        # 5. Atualizar UI
        self._update_popup_ui()
        
        if self.on_pause_callback:
            self.on_pause_callback(True)
    
    def _end_pause(self):
        """Encerra a pausa (apenas local e agente; não bate ponto no Bitrix)"""
        global AGENT_PAUSED
        # 1. Buscar dados de ponto do Bitrix24 (só leitura)
        self._fetch_bitrix_data()
        
        # 2. Calcular duração da pausa local
        if self.pause_start_time:
            pause_duration = (datetime.now() - self.pause_start_time).total_seconds()
            self.total_pause_seconds += pause_duration
        
        # 3. Atualizar estado local
        self.is_paused = False
        self.pause_start_time = None
        self.current_pause_seconds = 0
        
        # 4. Retomar o agente de envio de informações
        print("[INFO] Retomando agente de envio de informações...")
        AGENT_PAUSED = False
        try:
            # Usar caminho absoluto para garantir que encontre a flag
            flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.agent_pause_flag')
            print(f"[DEBUG] Verificando flag de pausa em: {flag_file}")
            if os.path.exists(flag_file):
                os.remove(flag_file)
                print("[INFO] ✓ Flag de pausa removida - agente retomará envio de informações")
            else:
                print("[DEBUG] Flag de pausa não encontrada (pode já ter sido removida)")
        except Exception as e:
            print(f"[WARN] Não foi possível remover flag de pausa: {e}")
        
        # 5. Buscar dados do Bitrix novamente
        self._fetch_bitrix_data()
        
        # 6. Atualizar UI
        self._update_popup_ui()
        
        if self.on_pause_callback:
            self.on_pause_callback(False)
    
    def _end_workday(self):
        """Finaliza o expediente do dia"""
        # Buscar dados atualizados do Bitrix antes de mostrar confirmação
        print("[INFO] Buscando dados atualizados do Bitrix24 antes de finalizar...")
        self._fetch_bitrix_data(update_ui=False)
        
        # Mostrar confirmação
        confirm_popup = tk.Toplevel(self.root)
        confirm_popup.title("Finalizar Expediente")
        confirm_popup.overrideredirect(True)
        confirm_popup.attributes('-topmost', True)
        
        # Centralizar - popup maior para caber todos os elementos
        popup_width = 480
        popup_height = 420
        screen_width = confirm_popup.winfo_screenwidth()
        screen_height = confirm_popup.winfo_screenheight()
        x = (screen_width - popup_width) // 2
        y = (screen_height - popup_height) // 2
        
        confirm_popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        confirm_popup.configure(bg='#1a1a2e')
        
        # Frame principal com scroll se necessário
        main_frame = tk.Frame(confirm_popup, bg='#1a1a2e')
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Barra superior com botão Fechar (X)
        def close_popup():
            confirm_popup.destroy()
        top_bar = tk.Frame(main_frame, bg='#1a1a2e')
        top_bar.pack(fill='x', pady=(0, 5))
        close_btn = tk.Button(
            top_bar,
            text="Fechar",
            font=('Segoe UI', 10),
            bg='#3d3d5c',
            fg='#ffffff',
            activebackground='#4b5563',
            activeforeground='#ffffff',
            relief='flat',
            cursor='hand2',
            command=close_popup,
            padx=12,
            pady=4
        )
        close_btn.pack(side='right')
        close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#4b5563'))
        close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#3d3d5c'))
        
        # Título
        title_frame = tk.Frame(main_frame, bg='#1a1a2e')
        title_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(
            title_frame,
            text="Finalizar Expediente?",
            font=('Segoe UI', 16, 'bold'),
            fg='#ffffff',
            bg='#1a1a2e'
        ).pack(pady=(3, 0))
        
        # Separador
        tk.Frame(main_frame, height=1, bg='#3d3d5c').pack(fill='x', pady=12)
        
        # Informações de tempo
        info_frame = tk.Frame(main_frame, bg='#1a1a2e')
        info_frame.pack(fill='x', pady=(0, 15))
        
        # Usar tempo do Bitrix
        work_time_str = self.bitrix_duration
        pause_time_str = self.bitrix_pause_duration
        
        # Tempo trabalhado
        work_info = tk.Frame(info_frame, bg='#252542', padx=12, pady=8)
        work_info.pack(fill='x', pady=(0, 6))
        
        tk.Label(
            work_info,
            text="Tempo Trabalhado",
            font=('Segoe UI', 9),
            fg='#8b8b9e',
            bg='#252542'
        ).pack(anchor='w')
        
        tk.Label(
            work_info,
            text=work_time_str,
            font=('Segoe UI', 18, 'bold'),
            fg='#4ade80',
            bg='#252542'
        ).pack(anchor='w')
        
        # Tempo em pausa
        pause_info = tk.Frame(info_frame, bg='#252542', padx=12, pady=8)
        pause_info.pack(fill='x')
        
        tk.Label(
            pause_info,
            text="Tempo em Pausas",
            font=('Segoe UI', 9),
            fg='#8b8b9e',
            bg='#252542'
        ).pack(anchor='w')
        
        tk.Label(
            pause_info,
            text=pause_time_str,
            font=('Segoe UI', 18, 'bold'),
            fg='#fbbf24',
            bg='#252542'
        ).pack(anchor='w')
        
        # Separador
        tk.Frame(main_frame, height=1, bg='#3d3d5c').pack(fill='x', pady=12)
        
        # Botões - MAIORES E MAIS VISÍVEIS
        btn_frame = tk.Frame(main_frame, bg='#1a1a2e')
        btn_frame.pack(fill='x', pady=(10, 0))
        
        def confirm():
            confirm_popup.destroy()
            self._do_end_workday()
        
        def cancel():
            confirm_popup.destroy()
        
        # Botão Confirmar - GRANDE E DESTACADO
        print("[DEBUG] Criando botão de confirmar...")
        confirm_btn = tk.Button(
            btn_frame,
            text="CONFIRMAR FINALIZAÇÃO",
            font=('Segoe UI', 16, 'bold'),
            bg='#dc2626',
            fg='white',
            activebackground='#b91c1c',
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=confirm,
            pady=18,
            padx=20
        )
        confirm_btn.pack(fill='x', pady=(0, 10))
        print("[DEBUG] Botão confirmar criado e empacotado")
        
        # Hover effect para botão confirmar
        def on_enter_confirm(e):
            confirm_btn.config(bg='#b91c1c')
        def on_leave_confirm(e):
            confirm_btn.config(bg='#dc2626')
        confirm_btn.bind('<Enter>', on_enter_confirm)
        confirm_btn.bind('<Leave>', on_leave_confirm)
        
        # Botão Cancelar - menor mas visível
        print("[DEBUG] Criando botão de cancelar...")
        cancel_btn = tk.Button(
            btn_frame,
            text="Cancelar",
            font=('Segoe UI', 11),
            bg='#4b5563',
            fg='white',
            activebackground='#374151',
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=cancel,
            pady=10
        )
        cancel_btn.pack(fill='x', pady=(0, 0))
        print("[DEBUG] Botão cancelar criado e empacotado")
        
        # Hover effect para botão cancelar
        def on_enter_cancel(e):
            cancel_btn.config(bg='#374151')
        def on_leave_cancel(e):
            cancel_btn.config(bg='#4b5563')
        cancel_btn.bind('<Enter>', on_enter_cancel)
        cancel_btn.bind('<Leave>', on_leave_cancel)
        
        # Forçar atualização e foco no popup
        print("[DEBUG] Forçando atualização do popup...")
        confirm_popup.update_idletasks()
        confirm_popup.update()
        confirm_popup.focus_force()
        confirm_popup.lift()
        
        # Garantir que o popup está visível
        try:
            confirm_popup.deiconify()
        except:
            pass
        
        print("[DEBUG] Popup de confirmação criado e exibido")
    
    def _do_end_workday(self):
        """Executa o encerramento do expediente (não bate ponto no Bitrix; só para o agente)"""
        print("[INFO] Preparando para finalizar expediente...")
        
        # Marcar expediente como finalizado para esconder botões do popup
        self.workday_ended = True
        
        # Fechar popup atual para reabrir sem os botões
        if self.popup_visible and self.popup:
            try:
                self.popup.destroy()
                self.popup = None
                self.popup_visible = False
            except:
                pass
        
        # 1. Buscar dados de ponto do Bitrix24 (só leitura)
        print("[INFO] Buscando dados do Bitrix24...")
        self._fetch_bitrix_data(update_ui=False)
        
        # Verificar se o expediente já foi finalizado
        timeman_info = check_timeman_status(self.user_id)
        already_closed = timeman_info.get('status') == 'CLOSED' and timeman_info.get('worked_today', False)
        
        # 2. Obter horário atual
        current_time = datetime.now()
        current_time_str = current_time.strftime("%H:%M:%S")
        current_date_str = current_time.strftime("%Y-%m-%d")
        
        # 3. Usar tempos atualizados do Bitrix
        work_time_str = self.bitrix_duration
        pause_time_str = self.bitrix_pause_duration
        
        print(f"[INFO] Horário atual: {current_time_str}")
        print(f"[INFO] Tempo trabalhado: {work_time_str}")
        print(f"[INFO] Pausas: {pause_time_str}")
        print(f"[INFO] Expediente já finalizado: {already_closed}")
        
        # 4. Buscar coordenador
        manager_info = get_user_manager(self.user_id)
        if manager_info:
            manager_name = manager_info.get('manager_name', 'Coordenador')
            manager_id = manager_info.get('manager_id')
            print(f"[INFO] Coordenador encontrado: {manager_name} (ID: {manager_id})")
        else:
            manager_name = 'Coordenador'
            manager_id = None
            print("[WARN] Coordenador não encontrado. Usando 'Coordenador' como padrão.")
        
        # 5. Fechar popup do botão flutuante
        self._close_popup()
        
        # 6. Mostrar popup de finalização (estilo botão flutuante: sem barra de janela)
        countdown_popup = tk.Toplevel(self.root)
        countdown_popup.title("Expediente Finalizado" if not already_closed else "Solicitar Mais Tempo")
        countdown_popup.overrideredirect(True)
        countdown_popup.attributes('-topmost', True)
        countdown_popup.attributes('-alpha', 0.98)
        
        # Ajustar tamanho do popup baseado se já foi finalizado
        if already_closed:
            popup_width = 480
            popup_height = 600  # Menor para apenas o botão
        else:
            popup_width = 480
            popup_height = 600  # Maior para todos os elementos
        
        screen_width = countdown_popup.winfo_screenwidth()
        screen_height = countdown_popup.winfo_screenheight()
        x = (screen_width - popup_width) // 3
        y = (screen_height - popup_height) // 3
        
        countdown_popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        countdown_popup.configure(bg='#1a1a2e')
        
        # Frame principal
        main_frame = tk.Frame(countdown_popup, bg='#1a1a2e')
        main_frame.pack(fill='both', expand=True, padx=30, pady=40)
        
        # Barra superior com botão Fechar (estilo botão flutuante, sem modo janela)
        def _close_countdown():
            try:
                if hasattr(self, '_countdown_window') and self._countdown_window is countdown_popup:
                    self._countdown_window = None
                countdown_popup.destroy()
            except Exception:
                pass
        top_bar = tk.Frame(main_frame, bg='#1a1a2e')
        top_bar.pack(fill='x', pady=(0, 10))
        close_btn = tk.Button(
            top_bar,
            text="Fechar",
            font=('Segoe UI', 10),
            bg='#3d3d5c',
            fg='#ffffff',
            activebackground='#4b5563',
            activeforeground='#ffffff',
            relief='flat',
            cursor='hand2',
            command=_close_countdown,
            padx=12,
            pady=4
        )
        close_btn.pack(side='right')
        close_btn.bind('<Enter>', lambda e: close_btn.config(bg='#4b5563'))
        close_btn.bind('<Leave>', lambda e: close_btn.config(bg='#3d3d5c'))
        
        # Título - muda se já foi finalizado
        if already_closed:
            # Popup simplificado apenas com botão de solicitar mais tempo
            tk.Label(
                main_frame,
                text="⏰",
                font=('Segoe UI', 48),
                fg='#f59e0b',
                bg='#1a1a2e'
            ).pack(pady=(0, 15))
            
            tk.Label(
                main_frame,
                text="Expediente Já Finalizado",
                font=('Segoe UI', 20, 'bold'),
                fg='#ffffff',
                bg='#1a1a2e'
            ).pack(pady=(0, 10))
            
            tk.Label(
                main_frame,
                text="Solicite 30 minutos adicionais\nao coordenador",
                font=('Segoe UI', 13),
                fg='#8b8b9e',
                bg='#1a1a2e',
                justify='center'
            ).pack(pady=(0, 30))
            
            # Separador
            tk.Frame(main_frame, height=1, bg='#3d3d5c').pack(fill='x', pady=(0, 30))
            
            # Botão de solicitar mais tempo (único elemento)
            manager_id = manager_info.get('manager_id') if manager_info else None
            
            if manager_info and manager_id:
                button_text = f"📧 Informar {manager_name}\nsobre 30 minutos adicionais"
            else:
                button_text = "📧 Informar Coordenador\nsobre 30 minutos adicionais"
            
            def request_extension():
                if self.user_id:
                    if not manager_id:
                        print("[WARN] Coordenador não encontrado. Criando tarefa para o próprio usuário.")
                    
                    reason = f"Solicitação de 30 minutos adicionais após expediente finalizado. Usuário precisa de tempo adicional para concluir atividades. Solicitação enviada para {manager_name if manager_info else 'administrador'}"
                    
                    result = request_manager_approval(
                        user_id=self.user_id,
                        reason=reason,
                        manager_id=manager_id
                    )
                    if result and result.get('success'):
                        recipient = manager_name if manager_info else "administrador"
                        # Mostrar mensagem de sucesso
                        success_label = tk.Label(
                            main_frame,
                            text=f"✓ Solicitação enviada ao {recipient}!",
                            font=('Segoe UI', 12, 'bold'),
                            fg='#4ade80',
                            bg='#1a1a2e'
                        )
                        success_label.pack(pady=(10, 0))
                        # Fechar popup após 3 segundos
                        countdown_popup.after(3000, countdown_popup.destroy)
                    else:
                        error_label = tk.Label(
                            main_frame,
                            text="❌ Erro ao enviar solicitação",
                            font=('Segoe UI', 11),
                            fg='#f85149',
                            bg='#1a1a2e'
                        )
                        error_label.pack(pady=(10, 0))
            
            request_btn = tk.Button(
                main_frame,
                text=button_text,
                font=('Segoe UI', 14, 'bold'),
                bg='#f59e0b',
                fg='white',
                activebackground='#d97706',
                activeforeground='white',
                relief='flat',
                cursor='hand2',
                command=request_extension,
                pady=20,
                padx=30
            )
            request_btn.pack(fill='x')
            
            # Hover effect
            def on_enter_req(e):
                request_btn.config(bg='#d97706')
            def on_leave_req(e):
                request_btn.config(bg='#f59e0b')
            request_btn.bind('<Enter>', on_enter_req)
            request_btn.bind('<Leave>', on_leave_req)
            
            self._countdown_window = countdown_popup
            countdown_popup.update_idletasks()
            countdown_popup.update()
            countdown_popup.focus_force()
            countdown_popup.lift()
            try:
                countdown_popup.deiconify()
            except Exception:
                pass
            print("[DEBUG] Popup simplificado expediente já finalizado exibido")
            return  # Retornar aqui para não criar os outros elementos
        
        # Se não foi finalizado, mostrar popup completo
        else:
            tk.Label(
                main_frame,
                text="✅",
                font=('Segoe UI', 32),
                fg='#4ade80',
                bg='#1a1a2e'
            ).pack()
            
            tk.Label(
                main_frame,
                text="Expediente Finalizado!",
                font=('Segoe UI', 18, 'bold'),
                fg='#ffffff',
                bg='#1a1a2e'
            ).pack(pady=(5, 10))
        
        # Horário de finalização
        tk.Label(
            main_frame,
            text=f"Finalizado às {current_time_str}",
            font=('Segoe UI', 10),
            fg='#8b8b9e',
            bg='#1a1a2e'
        ).pack(pady=(0, 15))
        
        # Informações de tempo em cards
        info_frame = tk.Frame(main_frame, bg='#1a1a2e')
        info_frame.pack(fill='x', pady=(0, 15))
        
        # Tempo trabalhado
        work_card = tk.Frame(info_frame, bg='#252542', padx=15, pady=12)
        work_card.pack(fill='x', pady=(0, 8))
        
        tk.Label(
            work_card,
            text="⏱ Tempo Trabalhado",
            font=('Segoe UI', 10),
            fg='#8b8b9e',
            bg='#252542'
        ).pack(anchor='w')
        
        tk.Label(
            work_card,
            text=work_time_str,
            font=('Segoe UI', 18, 'bold'),
            fg='#4ade80',
            bg='#252542'
        ).pack(anchor='w')
        
        # Tempo em pausa
        pause_card = tk.Frame(info_frame, bg='#252542', padx=15, pady=12)
        pause_card.pack(fill='x')
        
        tk.Label(
            pause_card,
            text="☕ Tempo em Pausas",
            font=('Segoe UI', 10),
            fg='#8b8b9e',
            bg='#252542'
        ).pack(anchor='w')
        
        tk.Label(
            pause_card,
            text=pause_time_str,
            font=('Segoe UI', 18, 'bold'),
            fg='#fbbf24',
            bg='#252542'
        ).pack(anchor='w')
        
        # Separador
        tk.Frame(main_frame, height=1, bg='#3d3d5c').pack(fill='x', pady=12)
        
        # Contador de bloqueio
        countdown_frame = tk.Frame(main_frame, bg='#252542', padx=20, pady=12)
        countdown_frame.pack(fill='x', pady=(0, 12))
        
        tk.Label(
            countdown_frame,
            text="⏱ Bloqueio automático em:",
            font=('Segoe UI', 11),
            fg='#8b8b9e',
            bg='#252542'
        ).pack()
        
        countdown_label = tk.Label(
            countdown_frame,
            text="01:00:00",
            font=('Segoe UI', 28, 'bold'),
            fg='#fbbf24',
            bg='#252542'
        )
        countdown_label.pack()
        
        # Label de alerta que será atualizado
        alert_label = tk.Label(
            countdown_frame,
            text="⏰ 1 hora de acesso",
            font=('Segoe UI', 10),
            fg='#4ade80',
            bg='#252542'
        )
        alert_label.pack(pady=(5, 0))
        
        # Variável para controlar o contador e se já enviou a API
        countdown_seconds = [3600]  # 1 hora (3600 segundos)
        notifications_sent = set()  # Controle de notificações já enviadas
        api_sent = [False]  # Flag para garantir que API só seja enviada uma vez
        
        def send_close_api():
            """Não bate ponto no Bitrix; apenas marca que finalizou localmente."""
            if api_sent[0]:
                return
            api_sent[0] = True
            print("[INFO] Expediente finalizado localmente (ponto não é registrado no Bitrix).")
        
        # Parar o agente quando finalizar o expediente
        def stop_agent():
            """Para o agente de envio de informações (flags e thread locais)."""
            global AGENT_RUNNING
            print("[INFO] Parando agente de envio de informações...")
            AGENT_RUNNING = False
            agent_thread = AGENT_THREAD
            if agent_thread and agent_thread.is_alive():
                print("[INFO] Thread do agente encontrada e ativa. Aguardando finalização...")

            # Criar arquivo de flag para indicar que o agente deve parar
            try:
                flag_file = os.path.join(os.path.dirname(__file__), '.agent_stop_flag')
                with open(flag_file, 'w') as f:
                    f.write('STOP')
                print("[INFO] ✓ Flag de parada criada para o agente.")
            except Exception as e:
                print(f"[WARN] Não foi possível criar flag de parada: {e}")

            # Verificar se há agente rodando no shared_state (tela de bloqueio)
            if hasattr(self, 'shared_state') and self.shared_state:
                if self.shared_state.get('agent_running', False):
                    self.shared_state['agent_running'] = False
                    print("[INFO] ✓ Agente parado no shared_state!")

            print("[INFO] ✓ Agente parado! Nenhuma informação será enviada para a API.")
        
        # FINALIZAR EXPEDIENTE IMEDIATAMENTE ao mostrar o popup (apenas se não foi finalizado)
        if not already_closed:
            print("[INFO] Finalizando expediente imediatamente...")
            send_close_api()
            # Parar o agente
            stop_agent()
        else:
            print("[INFO] Expediente já finalizado. Mostrando popup para solicitar mais tempo.")
        
        def update_countdown():
            if countdown_seconds[0] > 0:
                total_seconds = countdown_seconds[0]
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                # Mostrar formato HH:MM:SS quando tiver horas, senão MM:SS
                if hours > 0:
                    countdown_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                else:
                    countdown_label.config(text=f"{minutes:02d}:{seconds:02d}")
                
                # Alertas conforme o tempo vai passando (30 minutos) com notificações Windows
                total_seconds = countdown_seconds[0]
                
                # Notificações em momentos específicos
                if total_seconds == 1500 and 'min25' not in notifications_sent:  # 25 min
                    notifications_sent.add('min25')
                    show_windows_notification("HiProd - Alerta", "Restam 25 minutos para bloqueio da máquina", 5)
                elif total_seconds == 1200 and 'min20' not in notifications_sent:  # 20 min
                    notifications_sent.add('min20')
                    show_windows_notification("HiProd - Alerta", "Restam 20 minutos para bloqueio da máquina", 5)
                elif total_seconds == 900 and 'min15' not in notifications_sent:  # 15 min
                    notifications_sent.add('min15')
                    show_windows_notification("HiProd - Atenção", "Restam 15 minutos para bloqueio da máquina", 5)
                    alert_label.config(text="⚠️ Restam 15 minutos", fg='#fbbf24')
                elif total_seconds == 600 and 'min10' not in notifications_sent:  # 10 min
                    notifications_sent.add('min10')
                    show_windows_notification("HiProd - Atenção", "Restam apenas 10 minutos!", 5)
                    alert_label.config(text="⚠️ Restam 10 minutos!", fg='#f59e0b')
                elif total_seconds == 300 and 'min5' not in notifications_sent:  # 5 min
                    notifications_sent.add('min5')
                    show_windows_notification("HiProd - URGENTE", "Restam apenas 5 minutos! Máquina será bloqueada.", 5)
                    alert_label.config(text="🔶 Restam 5 minutos!", fg='#f59e0b')
                    countdown_label.config(fg='#f59e0b')
                elif total_seconds == 120 and 'min2' not in notifications_sent:  # 2 min
                    notifications_sent.add('min2')
                    show_windows_notification("HiProd - URGENTE", "Restam apenas 2 minutos!", 5)
                    alert_label.config(text="🔴 Restam 2 minutos!", fg='#f85149')
                    countdown_label.config(fg='#f85149')
                elif total_seconds == 60 and 'min1' not in notifications_sent:  # 1 min
                    notifications_sent.add('min1')
                    show_windows_notification("HiProd - BLOQUEIO IMINENTE", "Restam apenas 60 segundos!", 5)
                    alert_label.config(text="🔴 Último minuto!", fg='#f85149')
                elif total_seconds <= 10:
                    alert_label.config(text="🔴 Bloqueio iminente!", fg='#f85149')
                elif total_seconds > 600:
                    alert_label.config(text="⏰ Máquina liberada por 30 minutos", fg='#4ade80')
                
                countdown_seconds[0] -= 1
                countdown_popup.after(1000, update_countdown)
            else:
                # Tempo esgotado - apenas fechar o popup (não bloquear a máquina)
                countdown_label.config(text="00:00:00", fg='#f85149')
                alert_label.config(
                    text="✅ Expediente finalizado",
                    fg='#4ade80',
                    font=('Segoe UI', 12, 'bold')
                )
                show_windows_notification("HiProd", "Expediente finalizado. Máquina permanece liberada.", 5)
                # Fechar o popup após 2 segundos (sem bloquear)
                def close_popup_only():
                    if hasattr(self, '_countdown_window') and self._countdown_window is countdown_popup:
                        self._countdown_window = None
                    try:
                        countdown_popup.destroy()
                    except Exception:
                        pass
                countdown_popup.after(2000, close_popup_only)
        
        # Iniciar contador
        update_countdown()
        
        # Separador
        tk.Frame(main_frame, height=1, bg='#3d3d5c').pack(fill='x', pady=8)
        
        # Botão de solicitar liberação
        manager_id = manager_info.get('manager_id') if manager_info else None
        
        # Ajustar texto do botão baseado se encontrou coordenador e se já foi finalizado
        if already_closed:
            if manager_info and manager_id:
                button_text = f"⏰ Solicitar Mais Tempo ao {manager_name}"
            else:
                button_text = "⏰ Solicitar Mais Tempo (Coordenador não encontrado)"
        else:
            if manager_info and manager_id:
                button_text = f"📧 Solicitar Liberação ao {manager_name}"
            else:
                button_text = "📧 Solicitar Liberação (Coordenador não encontrado)"
        
        def request_extension():
            if self.user_id:
                if not manager_id:
                    print("[WARN] Coordenador não encontrado. Criando tarefa para o próprio usuário.")
                
                # Ajustar motivo baseado se já foi finalizado
                if already_closed:
                    reason = f"Solicitação de mais tempo após expediente finalizado. Usuário precisa de tempo adicional para concluir atividades. Solicitação enviada para {manager_name if manager_info else 'administrador'}"
                else:
                    reason = f"Acesso adicional após expediente encerrado. Solicitação enviada para {manager_name if manager_info else 'administrador'}"
                
                result = request_manager_approval(
                    user_id=self.user_id,
                    reason=reason,
                    manager_id=manager_id
                )
                if result and result.get('success'):
                    # Resetar contador para mais 30 minutos
                    countdown_seconds[0] = 1800  # Resetar para 30 minutos (1800 segundos)
                    notifications_sent.clear()  # Limpar notificações já enviadas
                    countdown_label.config(fg='#fbbf24')  # Resetar cor do contador
                    alert_label.config(
                        text="⏰ Tempo resetado! Máquina liberada por mais 30 minutos",
                        fg='#4ade80',
                        font=('Segoe UI', 10)
                    )
                    # Notificação Windows
                    show_windows_notification(
                        "HiProd - Liberação Renovada",
                        f"Máquina liberada por mais 30 minutos. {manager_name} foi notificado.",
                        duration=10
                    )
                    recipient = manager_name if manager_info else "administrador"
                    tk.Label(
                        main_frame,
                        text=f"📧 Solicitação enviada ao {recipient}!",
                        font=('Segoe UI', 11),
                        fg='#58a6ff',
                        bg='#1a1a2e'
                    ).pack(pady=(5, 0))
                else:
                    tk.Label(
                        main_frame,
                        text="❌ Erro ao enviar solicitação",
                        font=('Segoe UI', 11),
                        fg='#f85149',
                        bg='#1a1a2e'
                    ).pack(pady=(5, 0))
        
        request_btn = tk.Button(
            main_frame,
            text=button_text,
            font=('Segoe UI', 12, 'bold'),
            bg='#f59e0b',
            fg='white',
            activebackground='#d97706',
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            command=request_extension,
            pady=12
        )
        request_btn.pack(fill='x', pady=(0, 10))
        
        # Hover effect
        def on_enter_req(e):
            request_btn.config(bg='#d97706')
        def on_leave_req(e):
            request_btn.config(bg='#f59e0b')
        request_btn.bind('<Enter>', on_enter_req)
        request_btn.bind('<Leave>', on_leave_req)
        
        self._countdown_window = countdown_popup
        countdown_popup.update_idletasks()
        countdown_popup.update()
        countdown_popup.focus_force()
        countdown_popup.lift()
        try:
            countdown_popup.deiconify()
        except Exception:
            pass
        print("[DEBUG] Popup de finalização (contador) exibido")
    
    def _lock_machine_after_countdown(self, popup=None):
        """Tempo esgotado: apenas fecha o popup (tela de bloqueio desativada)."""
        if hasattr(self, '_countdown_window') and self._countdown_window is not None:
            self._countdown_window = None
        if popup:
            try:
                popup.destroy()
            except Exception:
                pass
        print("[INFO] Contador finalizado. Tela de bloqueio desativada (nenhum bloqueio de máquina).")
    
    def _update_popup_ui(self):
        """Atualiza a UI do popup"""
        if not self.popup_visible or not self.popup:
            return
        
        # Atualizar status (conforme Bitrix)
        if self.status_label:
            status_map = {'OPENED': ('● Expediente ativo', Popup.ACCENT_GREEN), 'PAUSED': ('● Em pausa', Popup.ACCENT_YELLOW), 'CLOSED': ('● Dia finalizado', Popup.TEXT_SECONDARY)}
            st = status_map.get(self.bitrix_status, ('● Dia finalizado', Popup.TEXT_SECONDARY))
            status_text = st[0] if not self.is_paused else "● Em pausa (local)"
            status_color = Popup.ACCENT_YELLOW if self.is_paused else st[1]
            self.status_label.config(text=status_text, fg=status_color)
        
        # Atualizar botão de pausa
        if hasattr(self, 'pause_btn') and self.pause_btn:
            btn_text = "☕  INICIAR INTERVALO" if not self.is_paused else "▶  RETOMAR TRABALHO"
            btn_bg = Popup.ACCENT_ORANGE if not self.is_paused else Popup.ACCENT_GREEN
            self.pause_btn.config(text=btn_text, bg=btn_bg)
    
    def _update_timer(self):
        """Atualiza os cronômetros usando dados do Bitrix ou cálculo local"""
        try:
            # Calcular tempo trabalhado
            work_time_str = self.bitrix_duration
            pause_time_str = self.bitrix_pause_duration
            
            # Se temos work_start_time, calcular em tempo real (mesmo em pausa)
            if hasattr(self, 'work_start_time') and self.work_start_time:
                try:
                    current_dt = datetime.now()
                    total_seconds = (current_dt - self.work_start_time).total_seconds()
                    
                    # Subtrair pausas
                    base_pause = self._parse_time_to_seconds(self.bitrix_pause_duration)
                    pause_seconds = base_pause
                    
                    # Se estiver em pausa local, adicionar tempo da pausa atual
                    if self.is_paused and self.pause_start_time:
                        self.current_pause_seconds = (current_dt - self.pause_start_time).total_seconds()
                        pause_seconds += self.current_pause_seconds
                    
                    work_seconds = max(0, total_seconds - pause_seconds)
                    work_time_str = self._format_time(work_seconds)
                    pause_time_str = self._format_time(pause_seconds)
                except Exception as e:
                    # Se der erro, usar dados do Bitrix
                    pass
            
            # Se estiver em pausa local mas não temos work_start_time, atualizar apenas pausa
            elif self.is_paused and self.pause_start_time:
                self.current_pause_seconds = (datetime.now() - self.pause_start_time).total_seconds()
                base_pause = self._parse_time_to_seconds(self.bitrix_pause_duration)
                total_pause = base_pause + self.current_pause_seconds
                pause_time_str = self._format_time(total_pause)
            
            # Atualizar labels se popup está visível usando valores calculados
            # Formatar os valores calculados antes de atualizar
            if self.popup_visible:
                formatted_work = self._format_time_safe(work_time_str)
                formatted_pause = self._format_time_safe(pause_time_str)
                if self.work_time_label:
                    self.work_time_label.config(text=formatted_work)
                if self.pause_time_label:
                    self.pause_time_label.config(text=formatted_pause)
            
            # Atualizar cor do botão principal baseado no estado
            if self.is_paused:
                self.main_btn.config(bg='#f59e0b')  # Amarelo durante pausa
            else:
                self.main_btn.config(bg='#4361ee')  # Azul normal
            
            # Reagendar atualização a cada segundo
            self.root.after(1000, self._update_timer)
            
        except Exception as e:
            pass  # Janela pode ter sido destruída
    
    def _parse_time_to_seconds(self, time_str):
        """Converte string HH:MM:SS para segundos"""
        try:
            if not time_str:
                return 0
            parts = time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
        except:
            pass
        return 0
    
    def _format_time(self, seconds):
        """Formata segundos em HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def set_start_time(self, start_time):
        """Define o horário de início do expediente"""
        if isinstance(start_time, str):
            try:
                # Parse ISO format e converter para naive (sem timezone)
                parsed = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                # Remover timezone para comparação com datetime.now()
                if parsed.tzinfo is not None:
                    self.work_start_time = parsed.replace(tzinfo=None)
                else:
                    self.work_start_time = parsed
            except:
                self.work_start_time = datetime.now()
        elif isinstance(start_time, datetime):
            # Remover timezone se existir
            if start_time.tzinfo is not None:
                self.work_start_time = start_time.replace(tzinfo=None)
            else:
                self.work_start_time = start_time
    
    def destroy(self):
        """Destrói o botão flutuante"""
        if self.popup:
            self.popup.destroy()
        if self.root:
            self.root.destroy()




# Variável global para o botão flutuante
_floating_button = None


def create_floating_button(user_id=None, start_time=None):
    """Cria e retorna o botão flutuante (reutiliza se já existir)"""
    global _floating_button
    
    # Verificar se já existe um botão válido e reutilizá-lo
    if _floating_button:
        try:
            # Verificar se o botão ainda está válido (root existe e não foi destruído)
            if hasattr(_floating_button, 'root') and _floating_button.root:
                try:
                    # Tentar acessar uma propriedade do root para verificar se ainda está válido
                    _floating_button.root.winfo_exists()
                    print("[INFO] Botão flutuante já existe, reutilizando...")
                    
                    # Atualizar user_id se fornecido e diferente
                    if user_id and _floating_button.user_id != user_id:
                        _floating_button.user_id = user_id
                    
                    # Atualizar start_time se fornecido
                    if start_time:
                        _floating_button.set_start_time(start_time)
                    
                    return _floating_button
                except:
                    # Root foi destruído, criar novo
                    print("[INFO] Botão flutuante anterior foi destruído, criando novo...")
                    _floating_button = None
        except:
            # Erro ao verificar, criar novo
            _floating_button = None
    
    # Criar novo botão
    print("[INFO] Criando novo botao flutuante...")
    try:
        _floating_button = FloatingButton(user_id=user_id)
    except Exception as e:
        err_msg = "[ERROR] FloatingButton.__init__ falhou: %s %s" % (type(e).__name__, str(e)[:150])
        print(err_msg)
        try:
            import traceback
            with open(os.path.join(os.path.dirname(__file__), '.floating_button_error.log'), 'w', encoding='utf-8') as f:
                f.write(err_msg + "\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        _floating_button = None
        return None
    
    if start_time:
        _floating_button.set_start_time(start_time)
    
    return _floating_button
