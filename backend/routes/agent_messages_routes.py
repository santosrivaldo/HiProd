"""
Mensagens para o agente: a API deixa pendentes e o agente consulta a cada 10 min e exibe na tela.
Gestores (admin, head, coordenador, supervisor) podem criar/editar/excluir mensagens.
"""
from flask import Blueprint, request, jsonify
from ..auth import token_required, gestor_required
from ..database import DatabaseConnection
from ..utils import format_datetime_brasilia

agent_messages_bp = Blueprint('agent_messages', __name__)


def _resolve_usuario_monitorado(nome=None, usuario_monitorado_id=None):
    """Retorna (id, departamento_id) do usuário monitorado ou (None, None)."""
    if not nome and not usuario_monitorado_id:
        return None, None
    try:
        with DatabaseConnection() as db:
            if usuario_monitorado_id:
                db.cursor.execute(
                    'SELECT id, departamento_id FROM usuarios_monitorados WHERE id = %s;',
                    (int(usuario_monitorado_id),)
                )
            else:
                db.cursor.execute(
                    'SELECT id, departamento_id FROM usuarios_monitorados WHERE nome = %s LIMIT 1;',
                    (nome.strip(),)
                )
            row = db.cursor.fetchone()
            if row:
                return row[0], row[1]
    except Exception:
        pass
    return None, None


@agent_messages_bp.route('/agent-messages/pending', methods=['GET'])
def get_pending_messages():
    """
    Lista mensagens pendentes para o agente (chamado pelo agent a cada 10 min).
    Parâmetro: nome (nome do usuário Windows) ou usuario_monitorado_id.
    Retorna mensagens que ainda não foram entregues a esse usuário.
    """
    nome = request.args.get('nome')
    usuario_monitorado_id = request.args.get('usuario_monitorado_id', type=int)
    um_id, dept_id = _resolve_usuario_monitorado(nome=nome, usuario_monitorado_id=usuario_monitorado_id)
    if not um_id:
        return jsonify([]), 200
    try:
        with DatabaseConnection() as db:
            # Mensagens que se aplicam: todos OU usuario=um_id OU departamento=dept_id
            # E que ainda não foram entregues a este um_id
            db.cursor.execute('''
                SELECT m.id, m.titulo, m.mensagem, m.tipo, m.created_at, m.expires_at
                FROM agent_messages m
                WHERE (
                    m.destino_tipo = 'todos'
                    OR (m.destino_tipo = 'usuario' AND m.destino_id = %s)
                    OR (m.destino_tipo = 'departamento' AND m.destino_id = %s)
                )
                AND (m.expires_at IS NULL OR m.expires_at > CURRENT_TIMESTAMP)
                AND NOT EXISTS (
                    SELECT 1 FROM agent_message_deliveries d
                    WHERE d.message_id = m.id AND d.usuario_monitorado_id = %s
                )
                ORDER BY m.created_at ASC
            ''', (um_id, dept_id or 0, um_id))
            rows = db.cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'titulo': r[1],
                    'mensagem': r[2],
                    'tipo': r[3],
                    'created_at': format_datetime_brasilia(r[4]) if r[4] else None,
                    'expires_at': format_datetime_brasilia(r[5]) if r[5] else None,
                })
            return jsonify(result), 200
    except Exception as e:
        print(f"Erro ao listar mensagens pendentes: {e}")
        return jsonify([]), 200


@agent_messages_bp.route('/agent-messages/<int:message_id>/deliver', methods=['POST'])
def mark_delivered(message_id):
    """
    Marca uma mensagem como entregue para um usuário (chamado pelo agent após exibir).
    Body: nome ou usuario_monitorado_id.
    """
    data = request.get_json() or {}
    nome = data.get('nome') or request.args.get('nome')
    usuario_monitorado_id = data.get('usuario_monitorado_id') or request.args.get('usuario_monitorado_id', type=int)
    um_id, _ = _resolve_usuario_monitorado(nome=nome, usuario_monitorado_id=usuario_monitorado_id)
    if not um_id:
        return jsonify({'error': 'Nome ou usuario_monitorado_id obrigatório'}), 400
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                INSERT INTO agent_message_deliveries (message_id, usuario_monitorado_id)
                VALUES (%s, %s)
                ON CONFLICT (message_id, usuario_monitorado_id) DO NOTHING
            ''', (message_id, um_id))
            return jsonify({'ok': True}), 200
    except Exception as e:
        print(f"Erro ao marcar entrega: {e}")
        return jsonify({'error': str(e)}), 500


@agent_messages_bp.route('/agent-messages', methods=['GET'])
@token_required
@gestor_required
def list_messages(current_user):
    """Lista todas as mensagens (gestores)."""
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT m.id, m.titulo, m.mensagem, m.tipo, m.destino_tipo, m.destino_id,
                       m.created_by, m.created_at, m.expires_at,
                       u.nome as created_by_nome
                FROM agent_messages m
                LEFT JOIN usuarios u ON u.id = m.created_by
                ORDER BY m.created_at DESC
            ''')
            rows = db.cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'titulo': r[1],
                    'mensagem': r[2],
                    'tipo': r[3],
                    'destino_tipo': r[4],
                    'destino_id': r[5],
                    'created_by': str(r[6]) if r[6] else None,
                    'created_at': format_datetime_brasilia(r[7]) if r[7] else None,
                    'expires_at': format_datetime_brasilia(r[8]) if r[8] else None,
                    'created_by_nome': r[9],
                })
            return jsonify(result), 200
    except Exception as e:
        print(f"Erro ao listar mensagens: {e}")
        return jsonify({'error': str(e)}), 500


@agent_messages_bp.route('/agent-messages', methods=['POST'])
@token_required
@gestor_required
def create_message(current_user):
    """Cria uma nova mensagem (gestores). Body: titulo, mensagem, tipo, destino_tipo, destino_id (opcional)."""
    data = request.get_json() or {}
    titulo = (data.get('titulo') or '').strip()
    mensagem = (data.get('mensagem') or '').strip()
    if not titulo or not mensagem:
        return jsonify({'error': 'titulo e mensagem são obrigatórios'}), 400
    tipo = (data.get('tipo') or 'info').lower()
    if tipo not in ('info', 'alerta', 'urgente'):
        tipo = 'info'
    destino_tipo = (data.get('destino_tipo') or 'todos').lower()
    if destino_tipo not in ('todos', 'usuario', 'departamento'):
        destino_tipo = 'todos'
    destino_id = data.get('destino_id')
    if destino_tipo != 'todos' and destino_id is not None:
        destino_id = int(destino_id)
    else:
        destino_id = None
    expires_at = data.get('expires_at')  # opcional, ISO string
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                INSERT INTO agent_messages (titulo, mensagem, tipo, destino_tipo, destino_id, created_by, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, titulo, created_at
            ''', (titulo, mensagem, tipo, destino_tipo, destino_id, current_user[0], expires_at))
            row = db.cursor.fetchone()
            return jsonify({
                'id': row[0],
                'titulo': row[1],
                'created_at': format_datetime_brasilia(row[2]) if row[2] else None
            }), 201
    except Exception as e:
        print(f"Erro ao criar mensagem: {e}")
        return jsonify({'error': str(e)}), 500


@agent_messages_bp.route('/agent-messages/<int:message_id>', methods=['GET'])
@token_required
@gestor_required
def get_message(current_user, message_id):
    """Obtém uma mensagem por ID (gestores)."""
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT id, titulo, mensagem, tipo, destino_tipo, destino_id, created_by, created_at, expires_at
                FROM agent_messages WHERE id = %s
            ''', (message_id,))
            r = db.cursor.fetchone()
            if not r:
                return jsonify({'error': 'Mensagem não encontrada'}), 404
            return jsonify({
                'id': r[0],
                'titulo': r[1],
                'mensagem': r[2],
                'tipo': r[3],
                'destino_tipo': r[4],
                'destino_id': r[5],
                'created_by': str(r[6]) if r[6] else None,
                'created_at': format_datetime_brasilia(r[7]) if r[7] else None,
                'expires_at': format_datetime_brasilia(r[8]) if r[8] else None,
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_messages_bp.route('/agent-messages/<int:message_id>', methods=['PUT'])
@token_required
@gestor_required
def update_message(current_user, message_id):
    """Atualiza uma mensagem (gestores)."""
    data = request.get_json() or {}
    titulo = (data.get('titulo') or '').strip()
    mensagem = (data.get('mensagem') or '').strip()
    tipo = (data.get('tipo') or 'info').lower()
    if tipo not in ('info', 'alerta', 'urgente'):
        tipo = 'info'
    destino_tipo = (data.get('destino_tipo') or 'todos').lower()
    if destino_tipo not in ('todos', 'usuario', 'departamento'):
        destino_tipo = 'todos'
    destino_id = data.get('destino_id')
    if destino_tipo != 'todos' and destino_id is not None:
        destino_id = int(destino_id)
    else:
        destino_id = None
    expires_at = data.get('expires_at')
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                UPDATE agent_messages
                SET titulo = COALESCE(NULLIF(%s, ''), titulo),
                    mensagem = COALESCE(NULLIF(%s, ''), mensagem),
                    tipo = %s, destino_tipo = %s, destino_id = %s, expires_at = %s
                WHERE id = %s
            ''', (titulo or None, mensagem or None, tipo, destino_tipo, destino_id, expires_at, message_id))
            if db.cursor.rowcount == 0:
                return jsonify({'error': 'Mensagem não encontrada'}), 404
            return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_messages_bp.route('/agent-messages/<int:message_id>', methods=['DELETE'])
@token_required
@gestor_required
def delete_message(current_user, message_id):
    """Exclui uma mensagem (gestores)."""
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('DELETE FROM agent_messages WHERE id = %s', (message_id,))
            if db.cursor.rowcount == 0:
                return jsonify({'error': 'Mensagem não encontrada'}), 404
            return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
