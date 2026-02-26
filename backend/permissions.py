# -*- coding: utf-8 -*-
"""
Níveis de visualização e edição por perfil:

1. Colaborador: apenas visualização e edição do próprio perfil (página "Meu perfil").
2. Supervisor: acesso a todos do seu setor (departamento_id = mesmo do usuário).
3. Coordenador: acesso a uma seleção de setores (tabela usuario_departamentos_acesso).
4. Head: acesso a todos os setores + configuração de tags.
5. Admin: acesso a tudo + configurações do sistema (tags, departamentos, tokens, settings).

current_user: tupla (id, nome, email, ativo, departamento_id, perfil)
"""
from .database import DatabaseConnection

PERFIL_COLABORADOR = 'colaborador'
PERFIL_SUPERVISOR = 'supervisor'
PERFIL_COORDENADOR = 'coordenador'
PERFIL_HEAD = 'head'
PERFIL_ADMIN = 'admin'
PERFIL_CEO = 'ceo'
PERFIL_GERENTE = 'gerente'

# Quem pode editar tags (Head e Admin)
PERFIS_EDIT_TAGS = (PERFIL_ADMIN, PERFIL_HEAD, PERFIL_CEO, PERFIL_GERENTE)

# Quem pode gerenciar sistema (configurações, tokens, departamentos CRUD)
PERFIS_MANAGE_SYSTEM = (PERFIL_ADMIN,)

# Quem vê todos os setores (sem filtro por departamento)
PERFIS_SEE_ALL_DEPARTMENTS = (PERFIL_ADMIN, PERFIL_HEAD, PERFIL_CEO, PERFIL_GERENTE)


def _perfil(current_user):
    """Retorna perfil normalizado (minúsculo) ou colaborador."""
    if not current_user or len(current_user) < 6:
        return PERFIL_COLABORADOR
    return (current_user[5] or PERFIL_COLABORADOR).strip().lower()


def _user_id(current_user):
    if not current_user:
        return None
    return current_user[0]


def _departamento_id(current_user):
    if not current_user or len(current_user) < 5:
        return None
    return current_user[4]


def get_coordenador_departamento_ids(usuario_id):
    """
    Retorna lista de departamento_id que o coordenador tem permissão de acessar.
    Só faz sentido quando perfil é coordenador. Retorna lista vazia se não houver nenhum.
    """
    try:
        with DatabaseConnection() as db:
            db.cursor.execute('''
                SELECT departamento_id FROM usuario_departamentos_acesso
                WHERE usuario_id = %s
            ''', (usuario_id,))
            rows = db.cursor.fetchall()
            return [r[0] for r in rows] if rows else []
    except Exception:
        return []


def get_allowed_departamento_ids(current_user):
    """
    Retorna None = "todos os setores" ou lista de departamento_id que o usuário pode ver.
    Colaborador: retorna lista com apenas o departamento dele (para filtrar "próprio perfil" no front;
                 na prática colaborador não lista outros usuários).
    Supervisor: [departamento_id do usuário].
    Coordenador: lista da tabela usuario_departamentos_acesso.
    Head/CEO/Gerente/Admin: None (acesso total).
    """
    perfil = _perfil(current_user)
    if perfil in PERFIS_SEE_ALL_DEPARTMENTS:
        return None
    dept_id = _departamento_id(current_user)
    if perfil == PERFIL_SUPERVISOR:
        return [dept_id] if dept_id is not None else []
    if perfil == PERFIL_COORDENADOR:
        return get_coordenador_departamento_ids(_user_id(current_user))
    # Colaborador: só o próprio departamento (usado para esconder outros na listagem)
    return [dept_id] if dept_id is not None else []


def get_allowed_usuario_monitorado_ids(current_user):
    """
    Retorna None = "todos" ou lista de usuario_monitorado_id que o usuário pode ver.
    Usado para filtrar atividades e lista de usuários monitorados.
    Colaborador: apenas o seu próprio usuario_monitorado_id (se tiver vínculo).
    """
    perfil = _perfil(current_user)
    user_id = _user_id(current_user)
    try:
        with DatabaseConnection() as db:
            if perfil == PERFIL_COLABORADOR:
                db.cursor.execute(
                    'SELECT usuario_monitorado_id FROM usuarios WHERE id = %s',
                    (user_id,)
                )
                row = db.cursor.fetchone()
                um_id = row[0] if row and row[0] else None
                return [um_id] if um_id else []
            dept_ids = get_allowed_departamento_ids(current_user)
            if dept_ids is None:
                return None  # todos
            if not dept_ids:
                return []
            db.cursor.execute('''
                SELECT id FROM usuarios_monitorados
                WHERE ativo = TRUE AND departamento_id = ANY(%s)
            ''', (dept_ids,))
            rows = db.cursor.fetchall()
            return [r[0] for r in rows] if rows else []
    except Exception:
        return []


def can_edit_tags(current_user):
    """Head e Admin (e CEO/Gerente) podem configurar tags."""
    return _perfil(current_user) in PERFIS_EDIT_TAGS


def can_manage_system(current_user):
    """Apenas Admin: configurações do sistema, tokens, CRUD departamentos."""
    return _perfil(current_user) == PERFIL_ADMIN


def can_access_user(current_user, target_usuario_id, target_departamento_id=None):
    """
    Verifica se current_user pode acessar (ver/editar) o usuário target.
    Colaborador: só o próprio usuário (target_usuario_id == current_user.id).
    Supervisor: mesmo departamento.
    Coordenador: departamento do target na lista de setores permitidos.
    Head/Admin: sim.
    """
    perfil = _perfil(current_user)
    uid = _user_id(current_user)
    if perfil in PERFIS_SEE_ALL_DEPARTMENTS:
        return True
    if perfil == PERFIL_COLABORADOR:
        return str(target_usuario_id) == str(uid)
    if perfil == PERFIL_SUPERVISOR:
        return target_departamento_id is not None and target_departamento_id == _departamento_id(current_user)
    if perfil == PERFIL_COORDENADOR:
        allowed = get_allowed_departamento_ids(current_user)
        return target_departamento_id is not None and target_departamento_id in allowed
    return False


def can_edit_user(current_user, target_usuario_id, target_departamento_id=None):
    """Mesma regra de visualização: quem pode ver pode editar (exceto admin que edita qualquer um)."""
    return can_access_user(current_user, target_usuario_id, target_departamento_id)


def can_access_usuario_monitorado(current_user, um_id_or_departamento_id, by_departamento=False):
    """
    by_departamento=False: primeiro arg é usuario_monitorado_id.
    by_departamento=True: primeiro arg é departamento_id do usuário monitorado.
    """
    allowed_ids = get_allowed_usuario_monitorado_ids(current_user)
    if allowed_ids is None:
        return True
    if by_departamento:
        dept_ids = get_allowed_departamento_ids(current_user)
        if dept_ids is None:
            return True
        return um_id_or_departamento_id in dept_ids
    return um_id_or_departamento_id in allowed_ids
