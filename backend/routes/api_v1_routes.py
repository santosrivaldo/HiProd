from flask import Blueprint, request, jsonify
from ..database import DatabaseConnection
from ..auth import api_token_required
from datetime import datetime, timezone

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

@api_v1_bp.route('/atividades', methods=['POST', 'OPTIONS'])
def buscar_atividades_wrapper():
    """
    Endpoint V1 - Buscar atividades por usuário e período
    Requer: Token de API com permissão para /api/v1/atividades (POST)
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
    
    # Chamar função protegida pelo decorator
    return buscar_atividades_impl()

@api_token_required
def buscar_atividades_impl(token_data):
    """Implementação do endpoint de atividades (protegida por token)"""
    try:
        with DatabaseConnection() as db:
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
                'version': 'v1',
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

@api_v1_bp.route('/usuarios', methods=['GET', 'OPTIONS'])
def listar_usuarios_wrapper():
    """
    Endpoint V1 - Listar usuários monitorados
    Requer: Token de API com permissão para /api/v1/usuarios (GET)
    """
    # Tratar requisições OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Token')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
    
    # Chamar função protegida pelo decorator
    return listar_usuarios_impl()

@api_token_required
def listar_usuarios_impl(token_data):
    """Implementação do endpoint de listar usuários (protegida por token)"""
    try:
        with DatabaseConnection() as db:
            # Buscar usuários monitorados
            db.cursor.execute('''
                SELECT 
                    id,
                    nome,
                    cargo,
                    departamento_id,
                    ativo,
                    created_at,
                    updated_at
                FROM usuarios_monitorados
                WHERE ativo = TRUE
                ORDER BY nome
            ''')
            
            rows = db.cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'nome': row[1],
                    'cargo': row[2],
                    'departamento_id': row[3],
                    'ativo': row[4],
                    'created_at': row[5].isoformat() if row[5] else None,
                    'updated_at': row[6].isoformat() if row[6] else None
                })
            
            return jsonify({
                'version': 'v1',
                'total_usuarios': len(result),
                'usuarios': result
            }), 200
            
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!', 'error': str(e)}), 500

@api_v1_bp.route('/estatisticas', methods=['POST', 'OPTIONS'])
def obter_estatisticas_wrapper():
    """
    Endpoint V1 - Obter estatísticas de um usuário
    Requer: Token de API com permissão para /api/v1/estatisticas (POST)
    """
    # Tratar requisições OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Token')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
    
    if request.method != 'POST':
        return jsonify({'message': f'Método {request.method} não permitido. Use POST.'}), 405
    
    # Chamar função protegida pelo decorator
    return obter_estatisticas_impl()

@api_token_required
def obter_estatisticas_impl(token_data):
    """Implementação do endpoint de estatísticas (protegida por token)"""
    try:
        with DatabaseConnection() as db:
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
            
            # Buscar usuário monitorado
            usuario_monitorado_id = None
            
            try:
                usuario_id_int = int(usuario)
                db.cursor.execute('SELECT id FROM usuarios_monitorados WHERE id = %s', (usuario_id_int,))
                result = db.cursor.fetchone()
                if result:
                    usuario_monitorado_id = result[0]
            except (ValueError, TypeError):
                pass
            
            if not usuario_monitorado_id:
                db.cursor.execute('SELECT id FROM usuarios_monitorados WHERE nome = %s', (usuario,))
                result = db.cursor.fetchone()
                if result:
                    usuario_monitorado_id = result[0]
            
            if not usuario_monitorado_id:
                return jsonify({'message': f'Usuário "{usuario}" não encontrado!'}), 404
            
            # Estatísticas por categoria
            if inicio and fim:
                try:
                    inicio_dt = datetime.fromisoformat(inicio.replace('Z', '+00:00'))
                    fim_dt = datetime.fromisoformat(fim.replace('Z', '+00:00'))
                    db.cursor.execute('''
                        SELECT categoria, COUNT(*) as total, AVG(ociosidade) as media_ociosidade,
                               SUM(duracao) as tempo_total
                        FROM atividades
                        WHERE usuario_monitorado_id = %s
                        AND horario >= %s
                        AND horario <= %s
                        GROUP BY categoria
                        ORDER BY total DESC
                    ''', (usuario_monitorado_id, inicio_dt, fim_dt))
                except (ValueError, AttributeError):
                    db.cursor.execute('''
                        SELECT categoria, COUNT(*) as total, AVG(ociosidade) as media_ociosidade,
                               SUM(duracao) as tempo_total
                        FROM atividades
                        WHERE usuario_monitorado_id = %s
                        GROUP BY categoria
                        ORDER BY total DESC
                    ''', (usuario_monitorado_id,))
            else:
                db.cursor.execute('''
                    SELECT categoria, COUNT(*) as total, AVG(ociosidade) as media_ociosidade,
                           SUM(duracao) as tempo_total
                    FROM atividades
                    WHERE usuario_monitorado_id = %s
                    GROUP BY categoria
                    ORDER BY total DESC
                ''', (usuario_monitorado_id,))
            
            stats_categoria = db.cursor.fetchall()
            
            # Total de atividades
            if inicio and fim:
                try:
                    inicio_dt = datetime.fromisoformat(inicio.replace('Z', '+00:00'))
                    fim_dt = datetime.fromisoformat(fim.replace('Z', '+00:00'))
                    db.cursor.execute('''
                        SELECT COUNT(*) FROM atividades
                        WHERE usuario_monitorado_id = %s
                        AND horario >= %s
                        AND horario <= %s
                    ''', (usuario_monitorado_id, inicio_dt, fim_dt))
                except (ValueError, AttributeError):
                    db.cursor.execute('''
                        SELECT COUNT(*) FROM atividades
                        WHERE usuario_monitorado_id = %s
                    ''', (usuario_monitorado_id,))
            else:
                db.cursor.execute('''
                    SELECT COUNT(*) FROM atividades
                    WHERE usuario_monitorado_id = %s
                ''', (usuario_monitorado_id,))
            
            total_atividades = db.cursor.fetchone()[0]
            
            categorias = []
            for row in stats_categoria:
                categorias.append({
                    'categoria': row[0] or 'unclassified',
                    'total': row[1],
                    'media_ociosidade': float(row[2]) if row[2] else 0,
                    'tempo_total': row[3] or 0
                })
            
            return jsonify({
                'version': 'v1',
                'usuario': usuario,
                'periodo': {
                    'inicio': inicio,
                    'fim': fim
                } if inicio and fim else None,
                'total_atividades': total_atividades,
                'categorias': categorias
            }), 200
            
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Erro interno do servidor!', 'error': str(e)}), 500

@api_v1_bp.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """
    Endpoint V1 - Health check (não requer autenticação)
    """
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Token')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
    
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('SELECT 1')
            db.cursor.fetchone()
        
        return jsonify({
            'version': 'v1',
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'version': 'v1',
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503

