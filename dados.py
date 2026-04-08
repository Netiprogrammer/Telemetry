import sqlite3
import pandas as pd
import random
import os
from datetime import datetime, timedelta

def obter_caminho_banco():
    return r'C:\Users\anace\Downloads\telemetria_oficial.db'

def extrair_telemetria_hardware(num_registros):
    dados = []
    tempo_atual = datetime.now()
    for i in range(num_registros):
        registro = {
            'timestamp': (tempo_atual - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S'),
            'cpu_usage_pct': round(random.uniform(10.0, 99.9), 2),
            'gpu_usage_pct': round(random.uniform(5.0, 100.0), 2),
            'ram_usage_gb': round(random.uniform(4.0, 32.0), 2),
            'cpu_temp_celsius': round(random.uniform(40.0, 95.0), 2)
        }
        dados.append(registro)
    return pd.DataFrame(dados)

def transformar_dados(df):
    df['cpu_usage_pct'] = pd.to_numeric(df['cpu_usage_pct'])
    df['cpu_temp_celsius'] = pd.to_numeric(df['cpu_temp_celsius'])
    df['thermal_throttling'] = df['cpu_temp_celsius'].apply(lambda x: 1 if x > 85.0 else 0)
    df['gargalo_cpu'] = df.apply(lambda row: 1 if row['cpu_usage_pct'] > 90.0 and row['gpu_usage_pct'] < 50.0 else 0, axis=1)
    df = df.sort_values(by='timestamp', ascending=True).reset_index(drop=True)
    return df

def carregar_dados_sqlite(df, caminho_banco, nome_tabela):
    conexao = sqlite3.connect(caminho_banco)
    cursor = conexao.cursor()
    
    cursor.execute(f"DROP TABLE IF EXISTS {nome_tabela}")
    
    query_criacao_tabela = f"""
    CREATE TABLE {nome_tabela} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        cpu_usage_pct REAL,
        gpu_usage_pct REAL,
        ram_usage_gb REAL,
        cpu_temp_celsius REAL,
        thermal_throttling INTEGER,
        gargalo_cpu INTEGER
    )
    """
    cursor.execute(query_criacao_tabela)
    
    for _, row in df.iterrows():
        query_insercao = f"""
        INSERT INTO {nome_tabela} (timestamp, cpu_usage_pct, gpu_usage_pct, ram_usage_gb, cpu_temp_celsius, thermal_throttling, gargalo_cpu)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query_insercao, (
            row['timestamp'], 
            row['cpu_usage_pct'], 
            row['gpu_usage_pct'], 
            row['ram_usage_gb'], 
            row['cpu_temp_celsius'], 
            row['thermal_throttling'], 
            row['gargalo_cpu']
        ))
        
    conexao.commit()
    conexao.close()

def extrair_dados_criticos(caminho_banco):
    conexao = sqlite3.connect(caminho_banco)
    query = """
    SELECT 
        timestamp, 
        cpu_usage_pct, 
        gpu_usage_pct, 
        cpu_temp_celsius, 
        thermal_throttling, 
        gargalo_cpu
    FROM metricas_hardware
    WHERE thermal_throttling = 1 OR gargalo_cpu = 1
    ORDER BY timestamp DESC
    """
    df_critico = pd.read_sql_query(query, conexao)
    conexao.close()
    return df_critico

def gerar_metricas_resumo(df_critico):
    total_alertas = len(df_critico)
    alertas_temperatura = int(df_critico['thermal_throttling'].sum())
    alertas_gargalo = int(df_critico['gargalo_cpu'].sum())
    temp_maxima = float(df_critico['cpu_temp_celsius'].max())
    
    resumo = pd.DataFrame([{
        'data_relatorio': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_eventos_criticos': total_alertas,
        'picos_superaquecimento': alertas_temperatura,
        'picos_gargalo_cpu': alertas_gargalo,
        'temperatura_maxima_registrada': temp_maxima
    }])
    return resumo

def exportar_relatorios(df_critico, df_resumo):
    diretorio_destino = r'C:\Users\anace\Downloads'
    nome_arquivo = f"relatorio_alertas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    caminho_completo = os.path.join(diretorio_destino, nome_arquivo)
    
    df_critico.to_csv(caminho_completo, index=False, sep=';')
    
    print("\n[!] PIPELINE EXECUTADO COM SUCESSO [!]\n")
    print("=== RESUMO EXECUTIVO DO HARDWARE ===")
    for coluna in df_resumo.columns:
        print(f"{coluna.upper()}: {df_resumo.iloc[0][coluna]}")
    
    print(f"\nBanco de dados atualizado em: {obter_caminho_banco()}")
    print(f"Arquivo CSV detalhado salvo em: {caminho_completo}\n")

def executar_pipeline_completo():
    caminho_bd = obter_caminho_banco()
    
    print("Iniciando extração e carga de dados...")
    dados_brutos = extrair_telemetria_hardware(1500)
    dados_tratados = transformar_dados(dados_brutos)
    carregar_dados_sqlite(dados_tratados, caminho_bd, 'metricas_hardware')
    
    print("Iniciando análise analítica...")
    df_alertas = extrair_dados_criticos(caminho_bd)
    
    if not df_alertas.empty:
        resumo_operacional = gerar_metricas_resumo(df_alertas)
        exportar_relatorios(df_alertas, resumo_operacional)
    else:
        print("\nNenhum evento crítico de hardware detectado neste ciclo.")

if __name__ == "__main__":
    executar_pipeline_completo()