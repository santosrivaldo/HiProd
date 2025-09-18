
from datetime import datetime, timezone, timedelta
from .database import DatabaseConnection

# Timezone de Brasília (UTC-3)
BRASILIA_TZ = timezone(timedelta(hours=-3))

def get_brasilia_now():
    """Retorna o datetime atual no timezone de Brasília"""
    return datetime.now(BRASILIA_TZ)

def format_datetime_brasilia(dt):
    """Formata datetime para string no timezone de Brasília"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Se não tem timezone, assume que é UTC e converte para Brasília
        dt = dt.replace(tzinfo=timezone.utc).astimezone(BRASILIA_TZ)
    elif dt.tzinfo != BRASILIA_TZ:
        # Converte para Brasília se não estiver no timezone correto
        dt = dt.astimezone(BRASILIA_TZ)
    return dt.isoformat()

def classify_activity_with_tags(active_window, ociosidade, user_department_id=None, activity_id=None, domain=None):
    """Função para classificar atividade automaticamente usando tags com prioridade para domínio"""
    try:
        print(f"🏷️ Classificando com tags - window: {active_window}, domain: {domain}, dept_id: {user_department_id}")

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
                
                # Verificar matches em domínio e título
                domain_match = False
                title_match = False
                match_source = ""
                
                # PRIORIDADE 1: Verificar match no domínio (maior prioridade)
                if domain and palavra_chave.lower() in domain.lower():
                    domain_match = True
                    match_source = "domain"
                    # Domínio tem peso multiplicador de 2x para dar prioridade
                    confidence = peso * 2 * (len(palavra_chave) / len(domain)) * 100
                    print(f"🌐 Match no DOMÍNIO: '{palavra_chave}' -> Tag '{tag_nome}' (confidence: {confidence:.2f}, peso: {peso})")
                
                # PRIORIDADE 2: Verificar match no título da janela (menor prioridade)
                elif palavra_chave.lower() in active_window.lower():
                    title_match = True
                    match_source = "title"
                    confidence = peso * (len(palavra_chave) / len(active_window)) * 100
                    print(f"📝 Match no TÍTULO: '{palavra_chave}' -> Tag '{tag_nome}' (confidence: {confidence:.2f}, peso: {peso})")
                
                # Se encontrou match em qualquer fonte, adicionar à lista
                if domain_match or title_match:
                    matched_tags.append({
                        'tag_id': tag_id,
                        'nome': tag_nome,
                        'produtividade': tag_produtividade,
                        'confidence': confidence,
                        'palavra_chave': palavra_chave,
                        'peso': peso,
                        'match_source': match_source,
                        'domain_match': domain_match,
                        'title_match': title_match
                    })

            # Se temos múltiplas tags, escolher a melhor baseada em prioridade
            if matched_tags:
                # PRIORIDADE DE SELEÇÃO:
                # 1. Domínio + maior peso
                # 2. Título + maior peso
                # 3. Maior confidence geral
                
                # Primeiro, tentar encontrar matches de domínio
                domain_matches = [tag for tag in matched_tags if tag['domain_match']]
                if domain_matches:
                    # Entre matches de domínio, escolher o de maior peso
                    best_match = max(domain_matches, key=lambda x: x['peso'])
                    print(f"🌐 Melhor match por DOMÍNIO: '{best_match['nome']}' (peso: {best_match['peso']}, confidence: {best_match['confidence']:.2f}, produtividade: {best_match['produtividade']})")
                else:
                    # Se não há matches de domínio, escolher o melhor do título
                    best_match = max(matched_tags, key=lambda x: x['peso'])
                    print(f"📝 Melhor match por TÍTULO: '{best_match['nome']}' (peso: {best_match['peso']}, confidence: {best_match['confidence']:.2f}, produtividade: {best_match['produtividade']})")

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
