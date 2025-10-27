#!/usr/bin/env python3
"""
Script para criar a tag "Não Mapeado" e atualizar atividades existentes
através da API do backend
"""

import requests
import json

# Configurações da API
API_BASE_URL = 'http://192.241.155.236:8010'
LOGIN_URL = f"{API_BASE_URL}/login"
TAGS_URL = f"{API_BASE_URL}/tags"
ATIVIDADES_URL = f"{API_BASE_URL}/atividades"

# Credenciais
USERNAME = "connect"
PASSWORD = "L@undry60"

def login():
    """Faz login e obtém token"""
    try:
        response = requests.post(LOGIN_URL, json={
            "nome": USERNAME,
            "senha": PASSWORD
        })
        
        if response.status_code == 200:
            token = response.json().get("token")
            print("Login realizado com sucesso")
            return token
        else:
            print(f"Erro no login: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"Erro na conexao: {e}")
        return None

def create_unmapped_tag(token):
    """Cria a tag 'Não Mapeado' se não existir"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Verificar se a tag já existe
        response = requests.get(TAGS_URL, headers=headers)
        if response.status_code == 200:
            tags = response.json()
            for tag in tags:
                if tag.get('nome') == 'Não Mapeado':
                    print(f"Tag 'Nao Mapeado' ja existe com ID: {tag.get('id')}")
                    return tag.get('id')
        
        # Criar nova tag
        tag_data = {
            "nome": "Não Mapeado",
            "descricao": "Atividades que não possuem tags específicas",
            "cor": "#9CA3AF",
            "produtividade": "neutral",
            "departamento_id": None,
            "tier": 1,
            "ativo": True
        }
        
        response = requests.post(TAGS_URL, json=tag_data, headers=headers)
        if response.status_code == 201:
            tag_id = response.json().get('id')
            print(f"Tag 'Nao Mapeado' criada com ID: {tag_id}")
            return tag_id
        else:
            print(f"Erro ao criar tag: {response.status_code} {response.text}")
            return None
            
    except Exception as e:
        print(f"Erro ao criar tag: {e}")
        return None

def get_activities_without_tags(token):
    """Busca atividades que não possuem tags"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Buscar todas as atividades
        response = requests.get(f"{ATIVIDADES_URL}?limite=1000", headers=headers)
        if response.status_code != 200:
            print(f"Erro ao buscar atividades: {response.status_code}")
            return []
        
        activities = response.json()
        
        # Filtrar atividades que não têm tags (assumindo que não há campo has_tags)
        # Por enquanto, vamos buscar atividades com categoria genérica
        unmapped_activities = []
        for activity in activities:
            categoria = activity.get('categoria', '')
            if categoria in ['unclassified', 'Não Classificado', 'pending']:
                unmapped_activities.append(activity)
        
        print(f"Encontradas {len(unmapped_activities)} atividades sem tags")
        return unmapped_activities
        
    except Exception as e:
        print(f"Erro ao buscar atividades: {e}")
        return []

def update_activity_category(activity_id, token):
    """Atualiza uma atividade para categoria 'Não Mapeado'"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Atualizar categoria da atividade
        update_data = {
            "categoria": "Não Mapeado",
            "produtividade": "neutral"
        }
        
        response = requests.patch(f"{ATIVIDADES_URL}/{activity_id}", json=update_data, headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f"Erro ao atualizar atividade {activity_id}: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Erro ao atualizar atividade {activity_id}: {e}")
        return False

def get_statistics(token):
    """Mostra estatísticas das categorias"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Buscar atividades para estatísticas
        response = requests.get(f"{ATIVIDADES_URL}?limite=1000", headers=headers)
        if response.status_code != 200:
            print("Erro ao buscar estatisticas")
            return
        
        activities = response.json()
        
        # Contar por categoria
        categories = {}
        for activity in activities:
            categoria = activity.get('categoria', 'N/A')
            categories[categoria] = categories.get(categoria, 0) + 1
        
        print("\nEstatisticas por categoria:")
        print("=" * 40)
        for categoria, total in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"{categoria}: {total} atividades")
        
        print(f"\nTotal de atividades: {len(activities)}")
        
    except Exception as e:
        print(f"Erro ao obter estatisticas: {e}")

def main():
    """Função principal"""
    print("Atualizando atividades sem tags para 'Nao Mapeado'")
    print("=" * 60)
    
    # 1. Fazer login
    token = login()
    if not token:
        print("Falha no login. Abortando.")
        return False
    
    # 2. Criar tag "Não Mapeado"
    tag_id = create_unmapped_tag(token)
    if not tag_id:
        print("Falha ao criar tag 'Nao Mapeado'. Abortando.")
        return False
    
    # 3. Buscar atividades sem tags
    activities = get_activities_without_tags(token)
    if not activities:
        print("Nenhuma atividade sem tags encontrada.")
        return True
    
    # 4. Atualizar atividades
    print(f"\nEncontradas {len(activities)} atividades sem tags.")
    print("Atualizando para categoria 'Nao Mapeado'...")
    
    updated_count = 0
    for activity in activities:
        activity_id = activity.get('id')
        if activity_id and update_activity_category(activity_id, token):
            updated_count += 1
        
        if updated_count % 50 == 0:
            print(f"Atualizadas {updated_count} atividades...")
    
    # 5. Mostrar estatísticas
    get_statistics(token)
    
    print(f"\nAtualizacao concluida! {updated_count} atividades marcadas como 'Nao Mapeado'")
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperacao interrompida pelo usuario")
        exit(1)
    except Exception as e:
        print(f"\nErro inesperado: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
