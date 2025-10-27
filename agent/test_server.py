#!/usr/bin/env python3
"""
Script para testar se o servidor está recebendo dados corretamente
"""

import requests
import json
from datetime import datetime, timedelta

# Configurações da API
API_BASE_URL = 'http://192.241.155.236:8010'
LOGIN_URL = f"{API_BASE_URL}/login"
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
            print(f"[OK] Login realizado com sucesso")
            return token
        else:
            print(f"[ERROR] Erro no login: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Erro na conexao: {e}")
        return None

def get_recent_activities(token, limit=10):
    """Busca atividades recentes"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"limite": limit}
        
        response = requests.get(ATIVIDADES_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            activities = response.json()
            print(f"[OK] {len(activities)} atividades encontradas")
            return activities
        else:
            print(f"[ERROR] Erro ao buscar atividades: {response.status_code} {response.text}")
            return []
    except Exception as e:
        print(f"[ERROR] Erro na requisicao: {e}")
        return []

def analyze_activities(activities):
    """Analisa as atividades recebidas"""
    if not activities:
        print("[WARNING] Nenhuma atividade encontrada")
        return
    
    print(f"\n[ANALYSIS] Analise das {len(activities)} atividades mais recentes:")
    print("=" * 60)
    
    # Estatísticas gerais
    total_screenshots = sum(1 for a in activities if a.get('has_screenshot', False))
    total_with_url = sum(1 for a in activities if a.get('url'))
    total_with_page_title = sum(1 for a in activities if a.get('page_title'))
    total_with_domain = sum(1 for a in activities if a.get('domain'))
    
    print(f"[STATS] Estatisticas Gerais:")
    print(f"   - Total de atividades: {len(activities)}")
    print(f"   - Com screenshots: {total_screenshots} ({total_screenshots/len(activities)*100:.1f}%)")
    print(f"   - Com URL: {total_with_url} ({total_with_url/len(activities)*100:.1f}%)")
    print(f"   - Com titulo da pagina: {total_with_page_title} ({total_with_page_title/len(activities)*100:.1f}%)")
    print(f"   - Com dominio: {total_with_domain} ({total_with_domain/len(activities)*100:.1f}%)")
    
    # Mostrar algumas atividades detalhadas
    print(f"\n[DETAILS] Detalhes das ultimas 3 atividades:")
    for i, activity in enumerate(activities[:3]):
        print(f"\n   Atividade {i+1}:")
        print(f"   - ID: {activity.get('id')}")
        print(f"   - Usuario: {activity.get('usuario_monitorado_nome', 'N/A')}")
        print(f"   - Janela: {activity.get('active_window', 'N/A')}")
        print(f"   - Aplicacao: {activity.get('application', 'N/A')}")
        print(f"   - URL: {activity.get('url', 'N/A')}")
        print(f"   - Pagina: {activity.get('page_title', 'N/A')}")
        print(f"   - Dominio: {activity.get('domain', 'N/A')}")
        print(f"   - Screenshot: {'SIM' if activity.get('has_screenshot') else 'NAO'}")
        print(f"   - Horario: {activity.get('horario', 'N/A')}")
        print(f"   - Ociosidade: {activity.get('ociosidade', 0)}s")
    
    # Verificar se há atividades com os novos campos
    print(f"\n[CHECK] Verificacao dos Novos Campos:")
    activities_with_new_fields = []
    for activity in activities:
        has_new_fields = any([
            activity.get('url'),
            activity.get('page_title'),
            activity.get('domain')
        ])
        if has_new_fields:
            activities_with_new_fields.append(activity)
    
    if activities_with_new_fields:
        print(f"[OK] {len(activities_with_new_fields)} atividades com novos campos encontradas!")
        print("   Os novos campos (URL, pagina, dominio) estao sendo enviados corretamente.")
    else:
        print("[WARNING] Nenhuma atividade com novos campos encontrada.")
        print("   Pode indicar que o agente nao esta enviando os novos campos.")

def main():
    """Função principal"""
    print("HiProd - Verificacao do Servidor")
    print("=" * 50)
    
    # Fazer login
    token = login()
    if not token:
        print("[ERROR] Falha no login. Nao e possivel continuar.")
        return False
    
    # Buscar atividades
    activities = get_recent_activities(token)
    if not activities:
        print("[ERROR] Nao foi possivel buscar atividades.")
        return False
    
    # Analisar atividades
    analyze_activities(activities)
    
    print(f"\n[SUCCESS] Verificacao concluida!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Verificacao interrompida pelo usuario")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        exit(1)