
from datetime import datetime, timezone, timedelta
from .database import DatabaseConnection

def classify_activity_with_tags(active_window, ociosidade, user_department_id=None, activity_id=None):
    """Função para classificar atividade automaticamente usando tags"""
    try:
        print(f"🏷️ Classificando com tags - window: {active_window}, dept_id: {user_department_id}")

        with DatabaseConnection() as db:
            # Buscar tags ativas - primeiro do departamento específico, depois globais
            if user_department_id:
                db.cursor.execute('''
                SELECT t.id, t.nome, t.produtividade, tk.palavra_chave, tk.peso
                FROM tags t
                JOIN tag_palavras_chave tk ON t.id = tk.tag_id
                WHERE t.ativo = TRUE AND (t.departamento_id = %s OR t.departamento_id IS NULL)
                ORDER BY t.departamento_id NULLS LAST, tk.peso DESC;
                ''', (user_department_id,))
            else:
                # Buscar apenas tags globais
                db.cursor.execute('''
                SELECT t.id, t.nome, t.produtividade, tk.palavra_chave, tk.peso
                FROM tags t
                JOIN tag_palavras_chave tk ON t.id = tk.tag_id
                WHERE t.ativo = TRUE AND t.departamento_id IS NULL
                ORDER BY tk.peso DESC;
                ''')

            tag_matches = db.cursor.fetchall()
            matched_tags = []

            for tag_match in tag_matches:
                # Verificar se temos todos os campos necessários
                if len(tag_match) < 5:
                    continue
                tag_id, tag_nome, tag_produtividade, palavra_chave, peso = tag_match
                # Verificar se a palavra-chave está presente no título da janela (case insensitive)
                if palavra_chave.lower() in active_window.lower():
                    # Calcular confidence baseado no peso e na proporção da palavra-chave
                    confidence = peso * (len(palavra_chave) / len(active_window)) * 100
                    matched_tags.append({
                        'tag_id': tag_id,
                        'nome': tag_nome,
                        'produtividade': tag_produtividade,
                        'confidence': confidence,
                        'palavra_chave': palavra_chave,
                        'peso': peso
                    })

                    print(f"🎯 Match encontrado: '{palavra_chave}' -> Tag '{tag_nome}' (confidence: {confidence:.2f}, peso: {peso})")

            # Se temos múltiplas tags, escolher a de maior peso (menor tier/maior prioridade)
            if matched_tags:
                # Ordenar por peso DESC (maior peso = maior prioridade)
                best_match = max(matched_tags, key=lambda x: x['peso'])
                print(f"🏷️ Melhor match por peso: '{best_match['nome']}' (peso: {best_match['peso']}, produtividade: {best_match['produtividade']})")

                # Se temos um ID da atividade, salvar apenas a melhor associação
                if activity_id:
                    with DatabaseConnection() as db_save:
                        db_save.cursor.execute('''
                        INSERT INTO atividade_tags (atividade_id, tag_id, confidence)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (atividade_id, tag_id) DO UPDATE SET confidence = EXCLUDED.confidence;
                        ''', (activity_id, best_match['tag_id'], best_match['confidence']))

                # A categoria agora será o nome da tag
                return best_match['nome'], best_match['produtividade']

    except Exception as e:
        print(f"❌ Erro na classificação com tags: {e}")
        # Retornar fallback em caso de erro
        if ociosidade >= 600:
            return 'Ocioso', 'nonproductive'
        elif ociosidade >= 300:
            return 'Ausente', 'nonproductive'
        else:
            return 'Não Classificado', 'neutral'

    # Fallback para classificação por ociosidade se nenhuma tag foi encontrada
    print(f"🔍 Nenhuma tag encontrada, usando classificação por ociosidade: {ociosidade}")
    if ociosidade >= 600:  # 10 minutos
        return 'Ocioso', 'nonproductive'
    elif ociosidade >= 300:  # 5 minutos
        return 'Ausente', 'nonproductive'
    else:
        return 'Não Classificado', 'neutral'

# Manter função antiga para compatibilidade
def classify_activity(active_window, ociosidade, user_department_id=None):
    return classify_activity_with_tags(active_window, ociosidade, user_department_id)
