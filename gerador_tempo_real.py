import psycopg2
import random
import time
from datetime import datetime

def conectar_banco():
    while True:
        try:
            conexao = psycopg2.connect(
                dbname="telemetria",
                user="admin",
                password="adminpassword",
                host="db",
                port="5432"
            )
            return conexao
        except psycopg2.OperationalError:
            time.sleep(2)

def inicializar_tabela(conexao):
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metricas_hardware (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            cpu_usage_pct REAL,
            gpu_usage_pct REAL,
            ram_usage_gb REAL,
            cpu_temp_celsius REAL,
            thermal_throttling INTEGER,
            gargalo_cpu INTEGER
        )
    """)
    conexao.commit()

def gerar_dado_continuo():
    conexao = conectar_banco()
    inicializar_tabela(conexao)
    cursor = conexao.cursor()

    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cpu = round(random.uniform(10.0, 99.9), 2)
        gpu = round(random.uniform(5.0, 100.0), 2)
        ram = round(random.uniform(4.0, 32.0), 2)
        temp = round(random.uniform(40.0, 95.0), 2)
        termico = 1 if temp > 85.0 else 0
        gargalo = 1 if cpu > 90.0 and gpu < 50.0 else 0

        cursor.execute("""
            INSERT INTO metricas_hardware 
            (timestamp, cpu_usage_pct, gpu_usage_pct, ram_usage_gb, cpu_temp_celsius, thermal_throttling, gargalo_cpu)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (timestamp, cpu, gpu, ram, temp, termico, gargalo))
        
        conexao.commit()
        time.sleep(2)

if __name__ == "__main__":
    gerar_dado_continuo()