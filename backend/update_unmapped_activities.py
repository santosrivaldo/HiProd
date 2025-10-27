#!/usr/bin/env python3
"""
Script para atualizar atividades existentes que não possuem tags,
marcando-as como "Não Mapeado"
"""

import psycopg2
import os
from datetime import datetime

# Configurações do banco de dados
DB_CONFIG = {
    'host': '192.241.155.236',
    'port': 5432,
    'database': 'hiprod',
    'user': 'postgres',
    'password': 'L@undry60'
}

def create_connection():
    """Cria conexão com o banco de dados"""
    return psycopg2.connect(**DB_CONFIG)

def create_unmapped_tag():
    """Cria a tag 'Não Mapeado' se não existir"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Verificar se a tag "Não Mapeado" existe
        cursor.execute('''
            SELECT id FROM tags WHERE nome = 'Não Mapeado' AND departamento_id IS NULL
        ''')
        tag_result = cursor.fetchone()
        
        if not tag_result:
            # Criar tag "Não Mapeado"
            print("Criando tag 'Nao Mapeado'...")
            cursor.execute('''
                INSERT INTO tags (nome, descricao, cor, produtividade, departamento_id, tier, ativo)
                VALUES ('Não Mapeado', 'Atividades que não possuem tags específicas', '#9CA3AF', 'neutral', NULL, 1, TRUE)
                RETURNING id
            ''')
            tag_id = cursor.fetchone()[0]
            
            # Adicionar palavra-chave genérica para a tag
            cursor.execute('''
                INSERT INTO tag_palavras_chave (tag_id, palavra_chave, peso)
                VALUES (%s, 'não mapeado', 1)
            ''', (tag_id,))
            
            conn.commit()
            print(f"Tag 'Nao Mapeado' criada com ID: {tag_id}")
        else:
            tag_id = tag_result[0]
            print(f"Tag 'Nao Mapeado' ja existe com ID: {tag_id}")
        
        cursor.close()
        conn.close()
        return tag_id
        
    except Exception as e:
        print(f"Erro ao criar tag 'Nao Mapeado': {e}")
        return None

def find_activities_without_tags():
    """Encontra atividades que não possuem tags associadas"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Buscar atividades que não têm tags associadas
        cursor.execute('''
            SELECT a.id, a.active_window, a.categoria, a.produtividade, a.horario
            FROM atividades a
            LEFT JOIN atividade_tags at ON a.id = at.atividade_id
            WHERE at.atividade_id IS NULL
            ORDER BY a.horario DESC
        ''')
        
        activities = cursor.fetchall()
        print(f"Encontradas {len(activities)} atividades sem tags")
        
        cursor.close()
        conn.close()
        return activities
        
    except Exception as e:
        print(f"Erro ao buscar atividades sem tags: {e}")
        return []

def update_activities_to_unmapped(activities, tag_id):
    """Atualiza atividades para categoria 'Não Mapeado' e associa com a tag"""
    if not activities or not tag_id:
        return 0
    
    updated_count = 0
    
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        for activity in activities:
            activity_id, active_window, categoria, produtividade, horario = activity
            
            # Atualizar categoria e produtividade
            cursor.execute('''
                UPDATE atividades 
                SET categoria = %s, produtividade = %s
                WHERE id = %s
            ''', ('Não Mapeado', 'neutral', activity_id))
            
            # Associar com a tag "Não Mapeado"
            cursor.execute('''
                INSERT INTO atividade_tags (atividade_id, tag_id, confidence)
                VALUES (%s, %s, %s)
                ON CONFLICT (atividade_id, tag_id) DO UPDATE SET confidence = EXCLUDED.confidence
            ''', (activity_id, tag_id, 100.0))
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"Atualizadas {updated_count} atividades...")
        
        conn.commit()
        print(f"{updated_count} atividades atualizadas para 'Nao Mapeado'")
        
        cursor.close()
        conn.close()
        return updated_count
        
    except Exception as e:
        print(f"Erro ao atualizar atividades: {e}")
        return 0

def get_statistics():
    """Mostra estatísticas das categorias após a atualização"""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Contar atividades por categoria
        cursor.execute('''
            SELECT categoria, COUNT(*) as total
            FROM atividades
            GROUP BY categoria
            ORDER BY total DESC
        ''')
        
        categories = cursor.fetchall()
        
        print("\nEstatisticas por categoria:")
        print("=" * 40)
        for categoria, total in categories:
            print(f"{categoria}: {total} atividades")
        
        # Contar atividades com tags
        cursor.execute('''
            SELECT COUNT(DISTINCT atividade_id) as total_with_tags
            FROM atividade_tags
        ''')
        
        with_tags = cursor.fetchone()[0]
        
        # Total de atividades
        cursor.execute('SELECT COUNT(*) FROM atividades')
        total_activities = cursor.fetchone()[0]
        
        print(f"\nResumo:")
        print(f"Total de atividades: {total_activities}")
        print(f"Com tags: {with_tags}")
        print(f"Sem tags: {total_activities - with_tags}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro ao obter estatisticas: {e}")

def main():
    """Função principal"""
    print("Atualizando atividades sem tags para 'Nao Mapeado'")
    print("=" * 60)
    
    # 1. Criar tag "Não Mapeado"
    tag_id = create_unmapped_tag()
    if not tag_id:
        print("Falha ao criar tag 'Nao Mapeado'. Abortando.")
        return False
    
    # 2. Encontrar atividades sem tags
    activities = find_activities_without_tags()
    if not activities:
        print("Nenhuma atividade sem tags encontrada.")
        return True
    
    # 3. Atualizar atividades
    print(f"\nEncontradas {len(activities)} atividades sem tags.")
    print("Atualizando para categoria 'Nao Mapeado'...")
    
    updated = update_activities_to_unmapped(activities, tag_id)
    
    if updated > 0:
        # 4. Mostrar estatísticas
        get_statistics()
        print(f"\nAtualizacao concluida! {updated} atividades marcadas como 'Nao Mapeado'")
        return True
    else:
        print("Nenhuma atividade foi atualizada.")
        return False

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