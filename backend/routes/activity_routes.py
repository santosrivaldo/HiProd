
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
from ..auth import token_required
from ..database import DatabaseConnection
from ..utils import classify_activity_with_tags
import re

activity_bp = Blueprint('activity', __name__)

def extract_domain_from_window(active_window):
    """Extrair domínio do título da janela ativa"""
    if not active_window:
        return None
    
    # Tentar encontrar URLs no título da janela
    url_match = re.search(r'https?://([^/\s]+)', active_window)
    if url_match:
        return url_match.group(1)
    
    # Procurar por padrões conhecidos de domínio
    domain_patterns = [
        r'- ([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
        r'\(([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\)',
        r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})'
    ]
    
    for pattern in domain_patterns:
        match = re.search(pattern, active_window)
        if match:
            return match.group(1)
    
    return None

def extract_application_from_window(active_window):
    """Extrair aplicação do título da janela ativa"""
    if not active_window:
        return None
    
    # Aplicações conhecidas
    known_apps = {
        'chrome': 'Google Chrome',
        'firefox': 'Firefox',
        'edge': 'Microsoft Edge',
        'code': 'VS Code',
        'visual studio': 'Visual Studio',
        'notepad': 'Notepad',
        'explorer': 'Windows Explorer',
        'teams': 'Microsoft Teams',
        'outlook': 'Outlook',
        'word': 'Microsoft Word',
        'excel': 'Microsoft Excel',
        'powerpoint': 'PowerPoint',
        'slack': 'Slack',
        'discord': 'Discord',
        'whatsapp': 'WhatsApp',
        'telegram': 'Telegram'
    }
    
    lower_window = active_window.lower()
    
    for key, value in known_apps.items():
        if key in lower_window:
            return value
    
    # Tentar extrair o nome da aplicação do início do título
    app_match = re.match(r'^([^-–]+)', active_window)
    if app_match:
        app_name = app_match.group(1).strip()
        if 0 < len(app_name) < 50:
            return app_name
    
    return None

@activity_bp.route('/atividade', methods=['POST'])
@token_required
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

            # Configurar timezone de São Paulo
            sao_paulo_tz = timezone(timedelta(hours=-3))
            horario_atual = datetime.now(sao_paulo_tz)

            # Salvar atividade temporariamente
            db.cursor.execute('''
                INSERT INTO atividades
                (usuario_monitorado_id, ociosidade, active_window, titulo_janela, categoria, produtividade,
                 horario, duracao, ip_address, user_agent, domain, application)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            ''', (
                usuario_monitorado_id, ociosidade, active_window, titulo_janela,
                'pending', 'neutral', horario_atual,
                duracao, ip_address, user_agent, domain, application
            ))

            activity_id = db.cursor.fetchone()[0]

            # Fazer commit da atividade antes de tentar classificar
            db.conn.commit()

            try:
                categoria, produtividade = classify_activity_with_tags(active_window, ociosidade, user_department_id, activity_id)
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
                'horario': horario_atual.isoformat()
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
                        DATE(a.horario) as data_atividade
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
                        a.application
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
                        'eventos_agrupados': row[10],
                        'duracao': row[11] or 10,
                        'domain': row[12] if len(row) > 12 else None,
                        'application': row[13] if len(row) > 13 else None,
                        'data_atividade': row[14].isoformat() if row[14] else None
                    })
                else:
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
                        'duracao': row[10] or 10,
                        'domain': row[11] if len(row) > 11 else None,
                        'application': row[12] if len(row) > 12 else None
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
