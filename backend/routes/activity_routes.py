
from flask import Blueprint, request, jsonify, Response, send_file
from datetime import datetime, timezone, timedelta
from ..auth import token_required, agent_required, api_token_required
from ..database import DatabaseConnection
from ..utils import classify_activity_with_tags, get_brasilia_now, format_datetime_brasilia
from ..config import Config
import re
import base64
import os
import uuid

activity_bp = Blueprint('activity', __name__)

def extract_domain_from_window(active_window):
    """Extrair domínio do título da janela ativa com melhor precisão"""
    if not active_window:
        return None
    
    # Tentar encontrar URLs completas no título da janela
    url_match = re.search(r'https?://([^/\s]+)', active_window)
    if url_match:
        domain = url_match.group(1)
        # Limpar porta se presente
        domain = re.sub(r':\d+$', '', domain)
        return domain
    
    # Procurar por padrões conhecidos de domínio (mais específicos)
    domain_patterns = [
        r'- ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)',  # domínio após hífen
        r'\(([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\)',  # domínio entre parênteses
        r'([a-zA-Z0-9-]+\.(?:com|org|net|edu|gov|br|co\.uk|de|fr|es|it|ru|cn|jp)(?:\.br)?)',  # domínios conhecidos
    ]
    
    for pattern in domain_patterns:
        match = re.search(pattern, active_window)
        if match:
            domain = match.group(1)
            # Validar se é um domínio real
            if '.' in domain and len(domain.split('.')) >= 2:
                # Remover porta se presente
                domain = re.sub(r':\d+$', '', domain)
                return domain
    
    return None

def extract_application_from_window(active_window):
    """Extrair aplicação do título da janela ativa com melhor precisão"""
    if not active_window:
        return None
    
    # Aplicações conhecidas com padrões mais específicos
    known_apps = {
        'google chrome': 'Google Chrome',
        'chrome': 'Google Chrome',
        'firefox': 'Firefox',
        'mozilla firefox': 'Firefox',
        'microsoft edge': 'Microsoft Edge',
        'edge': 'Microsoft Edge',
        'visual studio code': 'VS Code',
        'vscode': 'VS Code',
        'code': 'VS Code',
        'visual studio': 'Visual Studio',
        'notepad++': 'Notepad++',
        'notepad': 'Notepad',
        'windows explorer': 'Windows Explorer',
        'explorer': 'Windows Explorer',
        'microsoft teams': 'Microsoft Teams',
        'teams': 'Microsoft Teams',
        'microsoft outlook': 'Outlook',
        'outlook': 'Outlook',
        'microsoft word': 'Microsoft Word',
        'word': 'Microsoft Word',
        'microsoft excel': 'Microsoft Excel',
        'excel': 'Microsoft Excel',
        'microsoft powerpoint': 'PowerPoint',
        'powerpoint': 'PowerPoint',
        'slack': 'Slack',
        'discord': 'Discord',
        'whatsapp': 'WhatsApp',
        'telegram': 'Telegram',
        'sublime text': 'Sublime Text',
        'atom': 'Atom',
        'photoshop': 'Adobe Photoshop',
        'illustrator': 'Adobe Illustrator'
    }
    
    lower_window = active_window.lower()
    
    # Verificar aplicações conhecidas (ordem por especificidade)
    sorted_apps = sorted(known_apps.items(), key=lambda x: len(x[0]), reverse=True)
    
    for key, value in sorted_apps:
        if key in lower_window:
            return value
    
    # Tentar extrair o nome da aplicação do final do título (após último hífen)
    app_match = re.search(r'[–-]\s*([^–-]+)\s*$', active_window)
    if app_match:
        app_name = app_match.group(1).strip()
        if 5 <= len(app_name) <= 30 and not any(char.isdigit() for char in app_name):
            return app_name
    
    # Tentar extrair do início do título
    app_match = re.match(r'^([^-–()]+)', active_window)
    if app_match:
        app_name = app_match.group(1).strip()
        if 3 <= len(app_name) <= 25:
            return app_name
    
    return 'Sistema Local'

@activity_bp.route('/atividade', methods=['POST'])
@agent_required  # Aceita token OU nome do usuário no header X-User-Name
def add_activity(current_user):
    try:
        data = request.json
        print(f"📥 Recebendo atividade: {data}")

        # Valida se os dados necessários estão presentes
        if not data:
            print("❌ Nenhum dado JSON recebido")
            return jsonify({'message': 'Dados JSON não fornecidos!'}), 400

        required_fields = ['ociosidade', 'active_window', 'usuario_monitorado_id']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            print(f"❌ Campos obrigatórios ausentes: {missing_fields}")
            return jsonify({
                'message': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}',
                'required_fields': required_fields,
                'received_data': list(data.keys()) if data else []
            }), 400

        # Classificação (categoria/produtividade) é sempre feita pelo servidor e pode ser editada no frontend.
        # Ignorar qualquer valor enviado pelo agent para evitar que a aplicação seja marcada como útil/não útil no cliente.
        data.pop('categoria', None)
        data.pop('produtividade', None)

        usuario_monitorado_id = data['usuario_monitorado_id']

        with DatabaseConnection() as db:
            # Verificar se o usuário monitorado existe
            db.cursor.execute("""
                SELECT id, nome, departamento_id, cargo, ativo, created_at, updated_at
                FROM usuarios_monitorados
                WHERE id = %s AND ativo = TRUE;
            """, (usuario_monitorado_id,))
            usuario_monitorado = db.cursor.fetchone()

            if not usuario_monitorado:
                print(f"❌ Usuário monitorado não encontrado: ID {usuario_monitorado_id}")
                return jsonify({
                    'message': f'Usuário monitorado não encontrado ou inativo! ID: {usuario_monitorado_id}',
                    'suggestion': 'Verifique se o usuário existe ou recrie-o através do endpoint /usuarios-monitorados'
                }), 404

            print(f"✅ Usuário monitorado encontrado: {usuario_monitorado[1]} (ID: {usuario_monitorado[0]})")

            # Obter departamento do usuário monitorado (índice 2 é departamento_id)
            user_department_id = usuario_monitorado[2] if usuario_monitorado and len(usuario_monitorado) > 2 else None

            # Classificar atividade automaticamente
            ociosidade = int(data.get('ociosidade', 0))
            active_window = data['active_window']

            # Extrair informações adicionais
            titulo_janela = data.get('titulo_janela', active_window)
            duracao = data.get('duracao', 0)
            
            # Extrair domínio e aplicação do active_window se não fornecidos
            domain = data.get('domain')
            if not domain:
                domain = extract_domain_from_window(active_window)
            
            application = data.get('application')
            if not application:
                application = extract_application_from_window(active_window)

            # Obter IP real do agente (considerando proxies)
            ip_address = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP', request.remote_addr))
            if ',' in str(ip_address):
                ip_address = ip_address.split(',')[0].strip()

            user_agent = request.headers.get('User-Agent', '')

            # Usar timezone de Brasília
            horario_atual = get_brasilia_now()
            
            # Processar screenshot se fornecido
            screenshot_data = None
            screenshot_size = None
            screenshot_format = 'JPEG'
            screenshot = data.get('screenshot')
            
            if screenshot:
                try:
                    # Decodificar base64 para bytes
                    screenshot_bytes = base64.b64decode(screenshot)
                    # Impor limite de tamanho (ex.: 200 KB)
                    if len(screenshot_bytes) > 200 * 1024:
                        print(f"⚠️ Screenshot muito grande ({len(screenshot_bytes)} bytes). Ignorando armazenamento.")
                        screenshot = None
                        screenshot_data = None
                        screenshot_size = None
                    else:
                        screenshot_data = screenshot_bytes
                        screenshot_size = len(screenshot_bytes)
                        print(f"📸 Screenshot processado: {screenshot_size} bytes")
                except Exception as e:
                    print(f"⚠️ Erro ao processar screenshot: {e}")
                    screenshot = None

            # Sanitizar/limitar campos de texto conforme schema
            if titulo_janela:
                titulo_janela = titulo_janela[:500]
            if domain:
                domain = domain[:255]
            if application:
                application = application[:100]

            # Obter tempo de presença facial se fornecido
            face_presence_time = data.get('face_presence_time')
            if face_presence_time is not None:
                try:
                    face_presence_time = int(face_presence_time)
                except (ValueError, TypeError):
                    face_presence_time = None
            
            # Salvar atividade temporariamente
            db.cursor.execute('''
                INSERT INTO atividades
                (usuario_monitorado_id, ociosidade, active_window, titulo_janela, categoria, produtividade,
                 horario, duracao, ip_address, user_agent, domain, application, face_presence_time,
                 screenshot, screenshot_data, screenshot_size, screenshot_format)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            ''', (
                usuario_monitorado_id, ociosidade, active_window, titulo_janela,
                'pending', 'neutral', horario_atual,
                duracao, ip_address, user_agent, domain, application, face_presence_time,
                screenshot, screenshot_data, screenshot_size, screenshot_format
            ))

            activity_id = db.cursor.fetchone()[0]

            # Fazer commit da atividade antes de tentar classificar
            db.conn.commit()

            try:
                categoria, produtividade = classify_activity_with_tags(active_window, ociosidade, user_department_id, activity_id, domain)
                print(f"🏷️ Classificação concluída: {categoria} ({produtividade})")
            except Exception as classify_error:
                print(f"❌ Erro na classificação: {classify_error}")
                # Fallback para classificação básica
                if ociosidade >= 600:
                    categoria, produtividade = 'idle', 'nonproductive'
                elif ociosidade >= 300:
                    categoria, produtividade = 'away', 'nonproductive'
                else:
                    categoria, produtividade = 'unclassified', 'neutral'

            # Atualizar atividade com classificação final
            db.cursor.execute('''
                UPDATE atividades
                SET categoria = %s, produtividade = %s
                WHERE id = %s;
            ''', (categoria, produtividade, activity_id))

            response_data = {
                'message': 'Atividade salva com sucesso!',
                'id': activity_id,
                'categoria': categoria,
                'produtividade': produtividade,
                'usuario_monitorado': usuario_monitorado[1],
                'usuario_monitorado_id': usuario_monitorado_id,
                'horario': format_datetime_brasilia(horario_atual)
            }

            print(f"✅ Atividade salva: ID {activity_id}")
            return jsonify(response_data), 201

    except Exception as e:
        print(f"❌ Erro inesperado ao salvar atividade: {e}")
        return jsonify({
            'message': 'Erro interno do servidor',
            'error': str(e)
        }), 500

@activity_bp.route('/atividades', methods=['GET'])
@activity_bp.route('/atividade', methods=['GET'])
@token_required
def get_atividades(current_user):
    """Buscar todas as atividades com filtros opcionais"""
    try:
        limite = min(request.args.get('limite', 50, type=int), 100)  # Limitar a 100
        pagina = request.args.get('pagina', 1, type=int)
        offset = (pagina - 1) * limite
        agrupar = request.args.get('agrupar', 'false').lower() == 'true'
        categoria_filter = request.args.get('categoria')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        usuario_monitorado_id = request.args.get('usuario_monitorado_id')

        with DatabaseConnection() as db:
            # Construir a parte WHERE da query
            query_parts = []
            params = []

            if categoria_filter:
                query_parts.append('a.categoria = %s')
                params.append(categoria_filter)

            if data_inicio:
                query_parts.append('a.horario >= %s')
                params.append(data_inicio)

            if data_fim:
                query_parts.append('a.horario <= %s')
                params.append(data_fim)

            if usuario_monitorado_id:
                query_parts.append('a.usuario_monitorado_id = %s')
                params.append(usuario_monitorado_id)

            where_clause = ""
            if query_parts:
                where_clause = "WHERE " + " AND ".join(query_parts)

            # Primeiro, contar o total de registros que atendem aos filtros
            if agrupar:
                count_query = f"""
                    SELECT COUNT(*) FROM (
                        SELECT 1
                        FROM atividades a
                        LEFT JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
                        {where_clause}
                        GROUP BY a.usuario_monitorado_id, a.active_window, DATE(a.horario)
                    ) as grouped;
                """
            else:
                count_query = f"SELECT COUNT(*) FROM atividades a {where_clause};"

            db.cursor.execute(count_query, params)
            total_count = db.cursor.fetchone()[0]

            if agrupar:
                # Query com agrupamento melhorado por dia, usuário e janela
                query = f"""
                    SELECT
                        MIN(a.id) as id,
                        a.usuario_monitorado_id,
                        MAX(um.nome) as usuario_monitorado_nome,
                        MAX(um.cargo) as cargo,
                        a.active_window,
                        MAX(a.categoria) as categoria,
                        MAX(a.produtividade) as produtividade,
                        MIN(a.horario) as primeiro_horario,
                        MAX(a.horario) as ultimo_horario,
                        MIN(a.ociosidade) as ociosidade,
                        COUNT(*) as eventos_agrupados,
                        SUM(COALESCE(a.duracao, 10)) as duracao_total,
                        MAX(a.domain) as domain,
                        MAX(a.application) as application,
                        DATE(a.horario) as data_atividade,
                        MAX(CASE WHEN a.screenshot IS NOT NULL THEN 1 ELSE 0 END)::boolean as has_screenshot,
                        MAX(a.screenshot_size) as screenshot_size,
                        MAX(a.face_presence_time) as face_presence_time
                    FROM atividades a
                    LEFT JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
                    {where_clause}
                    GROUP BY a.usuario_monitorado_id, a.active_window, DATE(a.horario)
                    ORDER BY MAX(a.horario) DESC, MIN(a.horario) DESC
                    LIMIT %s OFFSET %s;
                """
            else:
                # Query simples sem agrupamento
                query = f"""
                    SELECT
                        a.id,
                        a.usuario_monitorado_id,
                        um.nome as usuario_monitorado_nome,
                        um.cargo,
                        a.active_window,
                        a.categoria,
                        a.produtividade,
                        a.horario,
                        a.ociosidade,
                        1 as eventos_agrupados,
                        COALESCE(a.duracao, 10) as duracao_total,
                        a.domain,
                        a.application,
                        CASE WHEN a.screenshot IS NOT NULL THEN 1 ELSE 0 END::boolean as has_screenshot,
                        a.screenshot_size,
                        a.face_presence_time
                    FROM atividades a
                    LEFT JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
                    {where_clause}
                    ORDER BY a.horario DESC
                    LIMIT %s OFFSET %s;
                """

            params.extend([limite, offset])
            db.cursor.execute(query, params)
            rows = db.cursor.fetchall()

            result = []
            for row in rows:
                if agrupar:
                    # Quando agrupa, row[11] contém duracao_total (soma de todas as durações)
                    duracao_total = row[11] if row[11] is not None else 0
                    result.append({
                        'id': row[0],
                        'usuario_monitorado_id': row[1],
                        'usuario_monitorado_nome': row[2],
                        'cargo': row[3],
                        'active_window': row[4],
                        'categoria': row[5] or 'unclassified',
                        'produtividade': row[6] or 'neutral',
                        'horario': row[7].isoformat() if row[7] else None,  # primeiro_horario
                        'ultimo_horario': row[8].isoformat() if row[8] else None,
                        'ociosidade': row[9] or 0,
                        'eventos_agrupados': row[10] or 1,
                        'duracao': duracao_total,  # Para compatibilidade
                        'duracao_total': duracao_total,  # Campo correto com a soma total
                        'domain': row[12] if len(row) > 12 else None,
                        'application': row[13] if len(row) > 13 else None,
                        'data_atividade': row[14].isoformat() if row[14] else None,
                        'has_screenshot': row[15] if len(row) > 15 else False,
                        'screenshot_size': row[16] if len(row) > 16 else None,
                        'face_presence_time': row[17] if len(row) > 17 else None
                    })
                else:
                    # Quando não agrupa, row[10] contém duracao_total (duracao individual)
                    duracao_total = row[10] if row[10] is not None else 10
                    result.append({
                        'id': row[0],
                        'usuario_monitorado_id': row[1],
                        'usuario_monitorado_nome': row[2],
                        'cargo': row[3],
                        'active_window': row[4],
                        'categoria': row[5] or 'unclassified',
                        'produtividade': row[6] or 'neutral',
                        'horario': row[7].isoformat() if row[7] else None,
                        'ociosidade': row[8] or 0,
                        'eventos_agrupados': 1,
                        'duracao': duracao_total,  # Para compatibilidade
                        'duracao_total': duracao_total,
                        'domain': row[11] if len(row) > 11 else None,
                        'application': row[12] if len(row) > 12 else None,
                        'has_screenshot': row[13] if len(row) > 13 else False,
                        'screenshot_size': row[14] if len(row) > 14 else None,
                        'face_presence_time': row[15] if len(row) > 15 else None
                    })

            # Criar resposta com headers de paginação
            response = jsonify(result)
            response.headers['X-Total-Count'] = str(total_count)
            response.headers['X-Page'] = str(pagina)
            response.headers['X-Per-Page'] = str(limite)
            response.headers['X-Total-Pages'] = str((total_count + limite - 1) // limite)

            return response

    except Exception as e:
        print(f"Erro ao buscar atividades: {e}")
        return jsonify([]), 200

@activity_bp.route('/atividades/<int:activity_id>', methods=['PATCH'])
@token_required
def update_activity(current_user, activity_id):
    data = request.json

    if not data:
        return jsonify({'message': 'Dados não fornecidos!'}), 400

    try:
        with DatabaseConnection() as db:
            # Verificar se a atividade existe
            db.cursor.execute('''
                SELECT id FROM atividades
                WHERE id = %s;
            ''', (activity_id,))

            if not db.cursor.fetchone():
                return jsonify({'message': 'Atividade não encontrada!'}), 404

            # Campos que podem ser atualizados
            update_fields = []
            update_values = []

            if 'produtividade' in data:
                if data['produtividade'] not in ['productive', 'nonproductive', 'neutral', 'unclassified']:
                    return jsonify({'message': 'Valor de produtividade inválido!'}), 400
                update_fields.append('produtividade = %s')
                update_values.append(data['produtividade'])

            if 'categoria' in data:
                update_fields.append('categoria = %s')
                update_values.append(data['categoria'])

            if not update_fields:
                return jsonify({'message': 'Nenhum campo para atualizar!'}), 400

            # Atualizar a atividade
            query = f'''
                UPDATE atividades
                SET {', '.join(update_fields)}
                WHERE id = %s;
            '''
            update_values.append(activity_id)

            db.cursor.execute(query, update_values)
            return jsonify({'message': 'Atividade atualizada com sucesso!'}), 200

    except Exception as e:
        print(f"Erro ao atualizar atividade: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@activity_bp.route('/atividades/<int:activity_id>', methods=['DELETE'])
@token_required
def delete_activity(current_user, activity_id):
    try:
        with DatabaseConnection() as db:
            # Verificar se a atividade existe
            db.cursor.execute('''
                SELECT id FROM atividades
                WHERE id = %s;
            ''', (activity_id,))

            if not db.cursor.fetchone():
                return jsonify({'message': 'Atividade não encontrada!'}), 404

            # Excluir a atividade
            db.cursor.execute('''
                DELETE FROM atividades
                WHERE id = %s;
            ''', (activity_id,))

            return jsonify({'message': 'Atividade excluída com sucesso!'}), 200
    except Exception as e:
        print(f"Erro ao excluir atividade: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@activity_bp.route('/atividades/<int:activity_id>/tags', methods=['GET'])
@token_required
def get_activity_tags(current_user, activity_id):
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT t.id, t.nome, t.descricao, t.cor, t.produtividade,
                       at.confidence, d.nome as departamento_nome
                FROM atividade_tags at
                JOIN tags t ON at.tag_id = t.id
                LEFT JOIN departamentos d ON t.departamento_id = d.id
                WHERE at.atividade_id = %s
                ORDER BY at.confidence DESC;
            ''', (activity_id,))

            tags = db.cursor.fetchall()
            result = []

            for tag in tags:
                result.append({
                    'id': tag[0],
                    'nome': tag[1],
                    'descricao': tag[2],
                    'cor': tag[3],
                    'produtividade': tag[4],
                    'confidence': float(tag[5]) if tag[5] else 0.0,
                    'departamento_nome': tag[6]
                })

            return jsonify(result)
    except Exception as e:
        print(f"Erro ao buscar tags da atividade: {e}")
        return jsonify([]), 200

@activity_bp.route('/estatisticas', methods=['GET'])
@token_required
def get_statistics(current_user):
    usuario_monitorado_id = request.args.get('usuario_monitorado_id')

    if not usuario_monitorado_id:
        return jsonify({'message': 'usuario_monitorado_id é obrigatório!'}), 400

    try:
        with DatabaseConnection() as db:
            # Estatísticas por categoria
            db.cursor.execute('''
                SELECT categoria, COUNT(*) as total, AVG(ociosidade) as media_ociosidade,
                       SUM(duracao) as tempo_total
                FROM atividades
                WHERE usuario_monitorado_id = %s
                GROUP BY categoria
                ORDER BY total DESC;
            ''', (usuario_monitorado_id,))

            stats_por_categoria = db.cursor.fetchall()

            # Produtividade por dia da semana
            db.cursor.execute('''
                SELECT EXTRACT(DOW FROM horario) as dia_semana,
                       produtividade,
                       COUNT(*) as total
                FROM atividades
                WHERE usuario_monitorado_id = %s
                GROUP BY EXTRACT(DOW FROM horario), produtividade
                ORDER BY dia_semana;
            ''', (usuario_monitorado_id,))

            produtividade_semanal = db.cursor.fetchall()

            # Total de atividades hoje
            db.cursor.execute('''
                SELECT COUNT(*)
                FROM atividades
                WHERE usuario_monitorado_id = %s
                AND DATE(horario) = CURRENT_DATE;
            ''', (usuario_monitorado_id,))

            atividades_hoje = db.cursor.fetchone()[0]

            return jsonify({
                'categorias': [{
                    'categoria': stat[0],
                    'total_atividades': stat[1],
                    'media_ociosidade': float(stat[2]) if stat[2] else 0,
                    'tempo_total': stat[3] if stat[3] else 0
                } for stat in stats_por_categoria],
                'produtividade_semanal': [{
                    'dia_semana': int(stat[0]),
                    'produtividade': stat[1],
                    'total': stat[2]
                } for stat in produtividade_semanal],
                'atividades_hoje': atividades_hoje
            })
    except Exception as e:
        print(f"Erro ao obter estatísticas: {e}")
        return jsonify({}), 200

@activity_bp.route('/screenshot/<int:activity_id>', methods=['GET'])
@token_required
def get_screenshot(current_user, activity_id):
    """Retorna o screenshot de uma atividade específica"""
    try:
        with DatabaseConnection() as db:
            # Buscar screenshot da atividade
            db.cursor.execute('''
                SELECT screenshot_data, screenshot_format, screenshot_size, screenshot
                FROM atividades 
                WHERE id = %s AND (screenshot_data IS NOT NULL OR screenshot IS NOT NULL)
            ''', (activity_id,))
            
            result = db.cursor.fetchone()
            
            if not result:
                return jsonify({'error': 'Screenshot não encontrado'}), 404
            
            screenshot_data, screenshot_format, screenshot_size, screenshot_b64 = result
            
            # Se temos dados binários, usar eles
            if screenshot_data:
                return Response(
                    screenshot_data,
                    mimetype=f'image/{screenshot_format.lower() if screenshot_format else "jpeg"}',
                    headers={
                        'Content-Length': str(screenshot_size) if screenshot_size else '0',
                        'Cache-Control': 'public, max-age=3600'
                    }
                )
            # Se não, usar base64
            elif screenshot_b64:
                import base64
                screenshot_bytes = base64.b64decode(screenshot_b64)
                return Response(
                    screenshot_bytes,
                    mimetype='image/jpeg',
                    headers={
                        'Content-Length': str(len(screenshot_bytes)),
                        'Cache-Control': 'public, max-age=3600'
                    }
                )
            else:
                return jsonify({'error': 'Screenshot não encontrado'}), 404
            
    except Exception as e:
        print(f"Erro ao obter screenshot: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@activity_bp.route('/screenshots/batch', methods=['POST'])
@token_required
def get_screenshots_batch(current_user):
    """Retorna múltiplos screenshots em base64"""
    try:
        data = request.get_json()
        activity_ids = data.get('activity_ids', [])
        
        if not activity_ids:
            return jsonify({'error': 'IDs de atividades não fornecidos'}), 400
        
        with DatabaseConnection() as db:
            # Buscar screenshots das atividades
            placeholders = ','.join(['%s'] * len(activity_ids))
            db.cursor.execute(f'''
                SELECT id, screenshot, screenshot_format, screenshot_size
                FROM atividades 
                WHERE id IN ({placeholders}) AND screenshot IS NOT NULL
            ''', activity_ids)
            
            results = db.cursor.fetchall()
            
            screenshots = []
            for result in results:
                activity_id, screenshot_b64, screenshot_format, screenshot_size = result
                screenshots.append({
                    'activity_id': activity_id,
                    'screenshot': screenshot_b64,
                    'format': screenshot_format,
                    'size': screenshot_size
                })
            
            return jsonify({
                'screenshots': screenshots,
                'count': len(screenshots)
            })
            
    except Exception as e:
        print(f"Erro ao obter screenshots em lote: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500


# ========== Screen Frames (Timeline - frames por segundo, múltiplos monitores) ==========
# Imagens armazenadas no banco (BYTEA) para evitar milhares de arquivos no disco (Docker/ENOSPC).

def _mimetype_from_filename(filename):
    ext = (os.path.splitext(filename or '')[-1] or '').lower()
    return {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}.get(ext, 'image/jpeg')


def _ensure_screen_frames_dir():
    """Garante que o diretório de upload existe (apenas para leitura de registros legados com file_path)."""
    upload_dir = getattr(Config, 'UPLOAD_FOLDER', None) or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'uploads', 'screen_frames'
    )
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


@activity_bp.route('/screen-frames', methods=['POST'])
@agent_required
def add_screen_frames(current_user):
    """
    Recebe frames de tela (screenshots) do agente.
    Armazena no banco (BYTEA); não grava mais em disco.
    multipart/form-data: usuario_monitorado_id (opcional se X-User-Name), captured_at (opcional), arquivos em 'frames' ou 'frames[]'.
    """
    try:
        usuario_monitorado_id = request.form.get('usuario_monitorado_id', type=int)
        if usuario_monitorado_id is None and current_user and len(current_user) > 0:
            usuario_monitorado_id = current_user[0]
        if not usuario_monitorado_id:
            return jsonify({'message': 'usuario_monitorado_id é obrigatório!'}), 400

        captured_at_str = request.form.get('captured_at')
        if captured_at_str:
            try:
                captured_at = datetime.fromisoformat(captured_at_str.replace('Z', '+00:00'))
                if captured_at.tzinfo is None:
                    captured_at = captured_at.replace(tzinfo=timezone.utc)
                else:
                    captured_at = captured_at.astimezone(timezone.utc)
            except Exception:
                captured_at = get_brasilia_now().astimezone(timezone.utc)
        else:
            captured_at = get_brasilia_now().astimezone(timezone.utc)
        # Armazenar sempre em UTC (naive) no DB para consistência
        captured_at_utc = captured_at.replace(tzinfo=None) if captured_at.tzinfo else captured_at

        files = request.files.getlist('frames') or request.files.getlist('frames[]')
        if not files or not any(f and f.filename for f in files):
            return jsonify({'message': 'Envie pelo menos um frame em "frames" ou "frames[]"!'}), 400

        saved = []
        with DatabaseConnection() as db:
            for monitor_index, f in enumerate(files):
                if not f or not f.filename:
                    continue
                image_bytes = f.read()
                if not image_bytes:
                    continue
                content_type = _mimetype_from_filename(f.filename)

                db.cursor.execute('''
                    INSERT INTO screen_frames (usuario_monitorado_id, captured_at, monitor_index, image_data, content_type)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                ''', (usuario_monitorado_id, captured_at_utc, monitor_index, image_bytes, content_type))
                row_id = db.cursor.fetchone()[0]
                saved.append({'id': row_id, 'monitor_index': monitor_index})
        print(f"📥 Screen frames: {len(saved)} frames salvos (DB) para usuario_monitorado_id={usuario_monitorado_id} em {captured_at}")
        return jsonify({
            'message': 'Frames recebidos com sucesso!',
            'count': len(saved),
            'captured_at': captured_at.isoformat(),
            'ids': [s['id'] for s in saved]
        }), 201
    except Exception as e:
        print(f"❌ Erro ao salvar screen frames: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!'}), 500


@activity_bp.route('/screen-frames', methods=['GET'])
@token_required
def list_screen_frames(current_user):
    """
    Lista frames de tela para timeline.
    Query: usuario_monitorado_id (obrigatório), date (YYYY-MM-DD, opcional), limit (opcional).
    Retorna lista ordenada por captured_at para exibição frame a frame.
    """
    try:
        usuario_monitorado_id = request.args.get('usuario_monitorado_id', type=int)
        date = request.args.get('date')  # YYYY-MM-DD
        limit = request.args.get('limit', type=int) or 500
        order = (request.args.get('order') or 'asc').lower()  # 'asc' (timeline) ou 'desc' (DVR/latest)
        start_time = request.args.get('start_time', '').strip()  # HH:MM ou HH:MM:SS (Brasília)
        end_time = request.args.get('end_time', '').strip()

        if not usuario_monitorado_id:
            return jsonify({'message': 'usuario_monitorado_id é obrigatório!'}), 400

        order_clause = "ORDER BY captured_at DESC, monitor_index ASC LIMIT %s" if order == 'desc' else "ORDER BY captured_at ASC, monitor_index ASC LIMIT %s"

        with DatabaseConnection() as db:
            # Filtro por data no fuso de São Paulo (evita diferença de 11h com UTC)
            where = "WHERE usuario_monitorado_id = %s"
            params = [usuario_monitorado_id]
            if date:
                # captured_at no DB está em UTC (naive); filtrar por data em Brasília
                where += " AND ((captured_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date = %s::date"
                params.append(date)
            # Filtro opcional por faixa de horário (Brasília) para preview por tarefa
            if start_time and end_time and re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', start_time) and re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', end_time):
                where += " AND ((captured_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::time >= %s::time AND ((captured_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::time <= %s::time"
                params.append(start_time)
                params.append(end_time)
            params.append(limit)
            db.cursor.execute(f'''
                SELECT id, captured_at, monitor_index, file_path
                FROM screen_frames
                {where}
                {order_clause};
            ''', params)
            rows = db.cursor.fetchall()

        # Retornar captured_at sempre em Brasília, ISO com -03:00 (DB guarda UTC)
        frames = []
        for r in rows:
            frame_id, captured_at, monitor_index, file_path = r
            captured_at_brasilia = format_datetime_brasilia(captured_at) if captured_at else None
            frames.append({
                'id': frame_id,
                'captured_at': captured_at_brasilia or (captured_at.isoformat() if hasattr(captured_at, 'isoformat') else str(captured_at)),
                'monitor_index': monitor_index,
                'url': f"/api/screen-frames/{frame_id}/image"
            })
        return jsonify({'frames': frames, 'count': len(frames)})
    except Exception as e:
        print(f"❌ Erro ao listar screen frames: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!'}), 500


@activity_bp.route('/screen-frames/<int:frame_id>/image', methods=['GET'])
@token_required
def get_screen_frame_image(current_user, frame_id):
    """Serve a imagem de um frame (do banco ou do disco para registros legados)."""
    try:
        with DatabaseConnection() as db:
            db.cursor.execute(
                'SELECT image_data, content_type, file_path FROM screen_frames WHERE id = %s;',
                (frame_id,)
            )
            row = db.cursor.fetchone()
        if not row:
            return jsonify({'message': 'Frame não encontrado!'}), 404
        image_data, content_type, file_path = row
        if image_data:
            from io import BytesIO
            mimetype = (content_type or 'image/jpeg').strip() or 'image/jpeg'
            return send_file(BytesIO(image_data), mimetype=mimetype, max_age=3600)
        if file_path:
            upload_base = _ensure_screen_frames_dir()
            full_path = os.path.join(upload_base, file_path)
            if os.path.isfile(full_path):
                return send_file(full_path, mimetype='image/jpeg', max_age=3600)
        return jsonify({'message': 'Arquivo de frame não encontrado!'}), 404
    except Exception as e:
        print(f"❌ Erro ao servir frame {frame_id}: {e}")
        return jsonify({'message': 'Erro interno do servidor!'}), 500


# ========== Keylog (texto digitado - busca e alinhamento com timeline/screen) ==========

@activity_bp.route('/keylog', methods=['POST'])
@agent_required
def add_keylog(current_user):
    """
    Recebe entradas de keylog do agente.
    Body: { "usuario_monitorado_id": int, "entries": [ { "captured_at": "ISO", "text_content": "...", "window_title": "", "domain": "", "application": "" } ] }
    """
    try:
        data = request.json or {}
        usuario_monitorado_id = data.get('usuario_monitorado_id')
        if usuario_monitorado_id is None and current_user and len(current_user) > 0:
            usuario_monitorado_id = current_user[0]
        if not usuario_monitorado_id:
            return jsonify({'message': 'usuario_monitorado_id é obrigatório!'}), 400
        entries = data.get('entries', [])
        if not entries:
            return jsonify({'message': 'Envie pelo menos um item em "entries"!'}), 400

        captured_at_utc = None
        with DatabaseConnection() as db:
            for e in entries:
                captured_at_str = e.get('captured_at')
                if captured_at_str:
                    try:
                        captured_at = datetime.fromisoformat(captured_at_str.replace('Z', '+00:00'))
                        if captured_at.tzinfo:
                            captured_at = captured_at.astimezone(timezone.utc)
                        captured_at_utc = captured_at.replace(tzinfo=None)
                    except Exception:
                        captured_at_utc = get_brasilia_now().astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    captured_at_utc = get_brasilia_now().astimezone(timezone.utc).replace(tzinfo=None)
                text_content = (e.get('text_content') or '').strip()
                if not text_content:
                    continue
                window_title = (e.get('window_title') or '')[:500]
                domain = (e.get('domain') or '')[:255]
                application = (e.get('application') or '')[:100]
                db.cursor.execute('''
                    INSERT INTO keylog_entries (usuario_monitorado_id, captured_at, text_content, window_title, domain, application)
                    VALUES (%s, %s, %s, %s, %s, %s);
                ''', (usuario_monitorado_id, captured_at_utc, text_content, window_title, domain, application))
        return jsonify({'message': 'Keylog recebido!', 'count': len(entries)}), 201
    except Exception as ex:
        print(f"Erro ao salvar keylog: {ex}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!'}), 500


@activity_bp.route('/keylog/search', methods=['GET'])
@token_required
def search_keylog(current_user):
    """
    Busca keylog por palavra, usuário, departamento e período.
    Query: q=, usuario_monitorado_id=, departamento_id=, date_from=, date_to=, limit=
    Para janela por minuto (timeline): at= (ISO datetime) e window_seconds=60 → retorna keylog entre at-30s e at+30s.
    """
    try:
        q = (request.args.get('q') or '').strip()
        usuario_monitorado_id = request.args.get('usuario_monitorado_id', type=int)
        departamento_id = request.args.get('departamento_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        at_iso = request.args.get('at')
        window_seconds = request.args.get('window_seconds', type=int) or 60
        limit = min(request.args.get('limit', type=int) or 50, 200)

        with DatabaseConnection() as db:
            where_parts = ['1=1']
            params = []
            if q:
                where_parts.append("to_tsvector('portuguese', k.text_content) @@ plainto_tsquery('portuguese', %s)")
                params.append(q)
            if usuario_monitorado_id:
                where_parts.append('k.usuario_monitorado_id = %s')
                params.append(usuario_monitorado_id)
            if departamento_id:
                where_parts.append('um.departamento_id = %s')
                params.append(departamento_id)
            if at_iso and usuario_monitorado_id:
                try:
                    at_dt = datetime.fromisoformat(at_iso.replace('Z', '+00:00'))
                    if at_dt.tzinfo:
                        at_dt = at_dt.astimezone(timezone.utc)
                    at_utc = at_dt.replace(tzinfo=None)
                    half = window_seconds // 2
                    start_utc = at_utc - timedelta(seconds=half)
                    end_utc = at_utc + timedelta(seconds=half)
                    where_parts.append('k.captured_at >= %s AND k.captured_at <= %s')
                    params.extend([start_utc, end_utc])
                except Exception:
                    pass
            if date_from and not at_iso:
                where_parts.append("(k.captured_at AT TIME ZONE 'UTC')::date >= %s::date")
                params.append(date_from)
            if date_to and not at_iso:
                where_parts.append("(k.captured_at AT TIME ZONE 'UTC')::date <= %s::date")
                params.append(date_to)
            params.append(limit)
            sql = f'''
                SELECT k.id, k.usuario_monitorado_id, um.nome AS usuario_monitorado_nome, k.captured_at,
                       k.text_content, k.window_title, k.domain, k.application
                FROM keylog_entries k
                JOIN usuarios_monitorados um ON um.id = k.usuario_monitorado_id
                WHERE {' AND '.join(where_parts)}
                ORDER BY k.captured_at DESC
                LIMIT %s;
            '''
            db.cursor.execute(sql, params)
            rows = db.cursor.fetchall()

        results = []
        for r in rows:
            kid, umid, nome, captured_at, text_content, window_title, domain, application = r
            captured_br = format_datetime_brasilia(captured_at) if captured_at else None
            date_iso = captured_at.date().isoformat() if hasattr(captured_at, 'date') else None
            results.append({
                'id': kid,
                'usuario_monitorado_id': umid,
                'usuario_monitorado_nome': nome,
                'captured_at': captured_br,
                'captured_at_iso': captured_at.isoformat() if hasattr(captured_at, 'isoformat') else str(captured_at),
                'date': date_iso,
                'text_content': (text_content or '')[:500],
                'window_title': window_title or '',
                'domain': domain or '',
                'application': application or '',
                'timeline_params': {'userId': umid, 'date': date_iso, 'at': captured_br}
            })
        return jsonify({'results': results, 'count': len(results)})
    except Exception as ex:
        print(f"Erro ao buscar keylog: {ex}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!'}), 500


@activity_bp.route('/atividades-by-window', methods=['GET'])
@token_required
def get_atividades_by_window(current_user):
    """
    Lista atividades por usuario_monitorado_id e intervalo de tempo (para alinhar com timeline de screen).
    Query: usuario_monitorado_id=, date= (YYYY-MM-DD), limit=
    Retorna atividades com horario em Brasília e referência para abrir a screen naquele momento.
    """
    try:
        usuario_monitorado_id = request.args.get('usuario_monitorado_id', type=int)
        date = request.args.get('date')
        limit = min(request.args.get('limit', type=int) or 200, 500)
        if not usuario_monitorado_id:
            return jsonify({'message': 'usuario_monitorado_id é obrigatório!'}), 400
        where = "a.usuario_monitorado_id = %s"
        params = [usuario_monitorado_id]
        if date:
            where += " AND ((a.horario AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo')::date = %s::date"
            params.append(date)
        params.append(limit)
        with DatabaseConnection() as db:
            db.cursor.execute(f'''
                SELECT a.id, a.usuario_monitorado_id, a.horario, a.active_window, a.categoria, a.produtividade, a.domain, a.application
                FROM atividades a
                WHERE {where}
                ORDER BY a.horario ASC
                LIMIT %s;
            ''', params)
            rows = db.cursor.fetchall()
        atividades = []
        for r in rows:
            aid, umid, horario, active_window, categoria, produtividade, domain, application = r
            horario_br = format_datetime_brasilia(horario) if horario else None
            date_iso = horario.date().isoformat() if hasattr(horario, 'date') else None
            atividades.append({
                'id': aid,
                'usuario_monitorado_id': umid,
                'horario': horario_br,
                'horario_iso': horario.isoformat() if hasattr(horario, 'isoformat') else str(horario),
                'date': date_iso,
                'active_window': active_window or '',
                'categoria': categoria or '',
                'produtividade': produtividade or '',
                'domain': domain or '',
                'application': application or '',
                'timeline_params': {'userId': umid, 'date': date_iso, 'at': horario_br}
            })
        return jsonify({'atividades': atividades, 'count': len(atividades)})
    except Exception as ex:
        print(f"Erro ao listar atividades por janela: {ex}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!'}), 500


@activity_bp.route('/face-presence-check', methods=['POST'])
@agent_required  # Aceita token OU nome do usuário no header X-User-Name
def add_face_presence_check(current_user):
    """
    Endpoint para receber pontos de verificação facial a cada 1 minuto.
    Armazena cada verificação individualmente para análise detalhada.
    """
    try:
        data = request.json
        print(f"📥 Recebendo verificação facial: {data}")

        if not data:
            return jsonify({'message': 'Dados JSON não fornecidos!'}), 400

        required_fields = ['usuario_monitorado_id', 'face_detected']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({
                'message': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'
            }), 400

        usuario_monitorado_id = data['usuario_monitorado_id']
        face_detected = bool(data['face_detected'])
        presence_time = int(data.get('presence_time', 0))  # Tempo acumulado em segundos

        with DatabaseConnection() as db:
            # Verificar se o usuário monitorado existe
            db.cursor.execute("""
                SELECT id FROM usuarios_monitorados
                WHERE id = %s AND ativo = TRUE;
            """, (usuario_monitorado_id,))
            
            if not db.cursor.fetchone():
                return jsonify({
                    'message': f'Usuário monitorado não encontrado ou inativo! ID: {usuario_monitorado_id}'
                }), 404

            # Usar timezone de Brasília
            check_time = get_brasilia_now()

            # Salvar ponto de verificação
            db.cursor.execute('''
                INSERT INTO face_presence_checks
                (usuario_monitorado_id, face_detected, presence_time, check_time)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            ''', (usuario_monitorado_id, face_detected, presence_time, check_time))

            check_id = db.cursor.fetchone()[0]
            print(f"✅ Ponto de verificação facial salvo: ID {check_id}")

            return jsonify({
                'message': 'Ponto de verificação facial registrado com sucesso!',
                'id': check_id
            }), 201

    except Exception as e:
        print(f"❌ Erro ao registrar verificação facial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@activity_bp.route('/face-presence-stats', methods=['GET'])
@token_required
def get_face_presence_stats(current_user):
    """
    Retorna estatísticas de presença facial por usuário e período.
    """
    try:
        usuario_monitorado_id = request.args.get('usuario_monitorado_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        group_by = request.args.get('group_by', 'day')  # day, hour, week

        with DatabaseConnection() as db:
            where_clause = "WHERE 1=1"
            params = []

            if usuario_monitorado_id:
                where_clause += " AND fpc.usuario_monitorado_id = %s"
                params.append(usuario_monitorado_id)

            if start_date:
                where_clause += " AND DATE(fpc.check_time) >= %s"
                params.append(start_date)

            if end_date:
                where_clause += " AND DATE(fpc.check_time) <= %s"
                params.append(end_date)

            # Query para obter estatísticas agregadas
            if group_by == 'day':
                query = f"""
                    SELECT 
                        DATE(fpc.check_time) as data,
                        um.id as usuario_id,
                        um.nome as usuario_nome,
                        COUNT(*) FILTER (WHERE fpc.face_detected = TRUE) as deteccoes,
                        COUNT(*) FILTER (WHERE fpc.face_detected = FALSE) as ausencias,
                        COUNT(*) as total_verificacoes,
                        MAX(fpc.presence_time) as tempo_max_presenca,
                        COUNT(*) FILTER (WHERE fpc.face_detected = TRUE) as minutos_presente
                    FROM face_presence_checks fpc
                    LEFT JOIN usuarios_monitorados um ON fpc.usuario_monitorado_id = um.id
                    {where_clause}
                    GROUP BY DATE(fpc.check_time), um.id, um.nome
                    ORDER BY data DESC, um.nome;
                """
            elif group_by == 'hour':
                query = f"""
                    SELECT 
                        DATE(fpc.check_time) as data,
                        EXTRACT(HOUR FROM fpc.check_time) as hora,
                        um.id as usuario_id,
                        um.nome as usuario_nome,
                        COUNT(*) FILTER (WHERE fpc.face_detected = TRUE) as deteccoes,
                        COUNT(*) FILTER (WHERE fpc.face_detected = FALSE) as ausencias,
                        COUNT(*) as total_verificacoes,
                        MAX(fpc.presence_time) as tempo_max_presenca
                    FROM face_presence_checks fpc
                    LEFT JOIN usuarios_monitorados um ON fpc.usuario_monitorado_id = um.id
                    {where_clause}
                    GROUP BY DATE(fpc.check_time), EXTRACT(HOUR FROM fpc.check_time), um.id, um.nome
                    ORDER BY data DESC, hora DESC, um.nome;
                """
            else:  # week
                query = f"""
                    SELECT 
                        DATE_TRUNC('week', fpc.check_time)::date as semana,
                        um.id as usuario_id,
                        um.nome as usuario_nome,
                        COUNT(*) FILTER (WHERE fpc.face_detected = TRUE) as deteccoes,
                        COUNT(*) FILTER (WHERE fpc.face_detected = FALSE) as ausencias,
                        COUNT(*) as total_verificacoes,
                        MAX(fpc.presence_time) as tempo_max_presenca,
                        SUM(CASE WHEN fpc.face_detected = TRUE THEN 60 ELSE 0 END) as minutos_presente
                    FROM face_presence_checks fpc
                    LEFT JOIN usuarios_monitorados um ON fpc.usuario_monitorado_id = um.id
                    {where_clause}
                    GROUP BY DATE_TRUNC('week', fpc.check_time), um.id, um.nome
                    ORDER BY semana DESC, um.nome;
                """

            try:
                db.cursor.execute(query, params)
                rows = db.cursor.fetchall()
            except Exception as db_error:
                # Verificar se a tabela não existe
                error_msg = str(db_error)
                if 'does not exist' in error_msg.lower() or 'relation' in error_msg.lower():
                    print(f"⚠️ Tabela face_presence_checks ainda não foi criada. Execute a inicialização do banco.")
                    return jsonify({
                        'message': 'Tabela de verificação facial ainda não foi criada. Aguarde a inicialização do banco.',
                        'data': []
                    }), 200
                else:
                    raise db_error

            result = []
            for row in rows:
                if group_by == 'day':
                    result.append({
                        'data': row[0].isoformat() if row[0] else None,
                        'usuario_id': row[1],
                        'usuario_nome': row[2],
                        'deteccoes': row[3] or 0,
                        'ausencias': row[4] or 0,
                        'total_verificacoes': row[5] or 0,
                        'tempo_max_presenca': row[6] or 0,
                        'minutos_presente': row[7] or 0,
                        'horas_presente': (row[7] or 0)  # Na verdade são minutos (verificações com face detectada)
                    })
                elif group_by == 'hour':
                    result.append({
                        'data': row[0].isoformat() if row[0] else None,
                        'hora': int(row[1]) if row[1] else None,
                        'usuario_id': row[2],
                        'usuario_nome': row[3],
                        'deteccoes': row[4] or 0,
                        'ausencias': row[5] or 0,
                        'total_verificacoes': row[6] or 0,
                        'tempo_max_presenca': row[7] or 0
                    })
                else:  # week
                    result.append({
                        'semana': row[0].isoformat() if row[0] else None,
                        'usuario_id': row[1],
                        'usuario_nome': row[2],
                        'deteccoes': row[3] or 0,
                        'ausencias': row[4] or 0,
                        'total_verificacoes': row[5] or 0,
                        'tempo_max_presenca': row[6] or 0,
                        'minutos_presente': row[7] or 0,
                        'horas_presente': (row[7] or 0)  # Na verdade são minutos (verificações com face detectada)
                    })

            return jsonify(result), 200

    except Exception as e:
        print(f"❌ Erro ao obter estatísticas de presença facial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!'}), 500

@activity_bp.route('/api/atividades', methods=['POST', 'OPTIONS'])
def get_atividades_by_token():
    """
    Endpoint para buscar atividades por usuário e período usando token de API.
    Aceita: { usuario: nome ou id, time: { inicio, fim } }
    Retorna: lista de atividades do usuário no período especificado
    """
    # Tratar requisições OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Token')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
    
    # Verificar método
    if request.method != 'POST':
        return jsonify({'message': f'Método {request.method} não permitido. Use POST.'}), 405
    
    # Validar token de API
    token = request.headers.get('Authorization') or request.headers.get('X-API-Token')
    
    if not token:
        return jsonify({'message': 'Token de API não fornecido!'}), 401

    # Remover 'Bearer ' se presente
    try:
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
    except (IndexError, AttributeError):
        return jsonify({'message': 'Formato de token inválido!'}), 401

    try:
        with DatabaseConnection() as db:
            # Buscar token no banco
            db.cursor.execute('''
                SELECT id, nome, ativo, expires_at, created_by
                FROM api_tokens
                WHERE token = %s
            ''', (token,))
            
            token_data = db.cursor.fetchone()
            
            if not token_data:
                return jsonify({'message': 'Token de API inválido!'}), 401
            
            token_id, token_nome, ativo, expires_at, created_by = token_data
            
            # Verificar se token está ativo
            if not ativo:
                return jsonify({'message': 'Token de API desativado!'}), 403
            
            # Verificar expiração
            if expires_at:
                expires_at_utc = expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at
                if datetime.now(timezone.utc) > expires_at_utc:
                    return jsonify({'message': 'Token de API expirado!'}), 403
            
            # Verificar permissões
            endpoint = request.path
            method = request.method
            
            db.cursor.execute('''
                SELECT endpoint, method
                FROM api_token_permissions
                WHERE token_id = %s
            ''', (token_id,))
            
            permissions = db.cursor.fetchall()
            
            if not permissions:
                return jsonify({'message': 'Token sem permissões configuradas!'}), 403
            
            has_permission = False
            for perm_endpoint, perm_method in permissions:
                if perm_endpoint.endswith('*'):
                    base_path = perm_endpoint[:-1]
                    if endpoint.startswith(base_path) and (perm_method == '*' or perm_method == method):
                        has_permission = True
                        break
                elif perm_endpoint == endpoint and (perm_method == '*' or perm_method == method):
                    has_permission = True
                    break
            
            if not has_permission:
                return jsonify({
                    'message': 'Token sem permissão para este endpoint!',
                    'endpoint': endpoint,
                    'method': method
                }), 403
            
            # Atualizar último uso
            db.cursor.execute('''
                UPDATE api_tokens
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (token_id,))
            
            # Processar requisição
            data = request.get_json()
            
            if not data:
                return jsonify({'message': 'Dados não fornecidos!'}), 400
            
            usuario = data.get('usuario')
            time_data = data.get('time', {})
            inicio = time_data.get('inicio')
            fim = time_data.get('fim')
            
            if not usuario:
                return jsonify({'message': 'Campo "usuario" é obrigatório!'}), 400
            
            if not inicio or not fim:
                return jsonify({'message': 'Campos "time.inicio" e "time.fim" são obrigatórios!'}), 400
            
            # Validar formato das datas
            try:
                inicio_dt = datetime.fromisoformat(inicio.replace('Z', '+00:00'))
                fim_dt = datetime.fromisoformat(fim.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                return jsonify({'message': f'Formato de data inválido: {str(e)}'}), 400
            # Buscar usuário monitorado por nome ou ID
            usuario_monitorado_id = None
            
            # Tentar como ID primeiro
            try:
                usuario_id_int = int(usuario)
                db.cursor.execute('''
                    SELECT id FROM usuarios_monitorados WHERE id = %s
                ''', (usuario_id_int,))
                result = db.cursor.fetchone()
                if result:
                    usuario_monitorado_id = result[0]
            except (ValueError, TypeError):
                pass
            
            # Se não encontrou como ID, tentar como nome
            if not usuario_monitorado_id:
                db.cursor.execute('''
                    SELECT id FROM usuarios_monitorados WHERE nome = %s
                ''', (usuario,))
                result = db.cursor.fetchone()
                if result:
                    usuario_monitorado_id = result[0]
            
            if not usuario_monitorado_id:
                return jsonify({'message': f'Usuário "{usuario}" não encontrado!'}), 404
            
            # Buscar atividades no período
            db.cursor.execute('''
                SELECT
                    a.id,
                    a.usuario_monitorado_id,
                    um.nome as usuario_monitorado_nome,
                    um.cargo,
                    a.active_window,
                    a.titulo_janela,
                    a.categoria,
                    a.produtividade,
                    a.horario,
                    a.ociosidade,
                    COALESCE(a.duracao, 10) as duracao,
                    a.domain,
                    a.application,
                    a.ip_address,
                    a.user_agent,
                    CASE WHEN a.screenshot IS NOT NULL THEN 1 ELSE 0 END::boolean as has_screenshot,
                    a.screenshot_size,
                    a.face_presence_time,
                    a.created_at,
                    a.updated_at
                FROM atividades a
                LEFT JOIN usuarios_monitorados um ON a.usuario_monitorado_id = um.id
                WHERE a.usuario_monitorado_id = %s
                AND a.horario >= %s
                AND a.horario <= %s
                ORDER BY a.horario DESC
            ''', (usuario_monitorado_id, inicio_dt, fim_dt))
            
            rows = db.cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'usuario_monitorado_id': row[1],
                    'usuario_monitorado_nome': row[2],
                    'cargo': row[3],
                    'active_window': row[4],
                    'titulo_janela': row[5],
                    'categoria': row[6] or 'unclassified',
                    'produtividade': row[7] or 'neutral',
                    'horario': row[8].isoformat() if row[8] else None,
                    'ociosidade': row[9] or 0,
                    'duracao': row[10] or 10,
                    'domain': row[11],
                    'application': row[12],
                    'ip_address': row[13],
                    'user_agent': row[14],
                    'has_screenshot': row[15] if row[15] else False,
                    'screenshot_size': row[16],
                    'face_presence_time': row[17],
                    'created_at': row[18].isoformat() if row[18] else None,
                    'updated_at': row[19].isoformat() if row[19] else None
                })
            
            return jsonify({
                'usuario': usuario,
                'periodo': {
                    'inicio': inicio,
                    'fim': fim
                },
                'total_atividades': len(result),
                'atividades': result
            }), 200
            
    except Exception as e:
        print(f"❌ Erro ao buscar atividades por token: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!', 'error': str(e)}), 500
