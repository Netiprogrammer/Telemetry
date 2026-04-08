import psutil
import requests
import time
import random

# A URL da sua nuvem na Render
URL_DA_API = "https://telemetrys.onrender.com/api/enviar-telemetria"

print("Iniciando Agente de Telemetria Local...")
print("Lendo dados físicos de CPU e RAM. Pressione Ctrl+C para parar.")

while True:
    try:
        # Lendo os dados REAIS do seu notebook usando psutil
        cpu_real = psutil.cpu_percent(interval=1)
        
        # Lendo a RAM real e convertendo bytes para Gigabytes
        ram_info = psutil.virtual_memory()
        ram_real_gb = round(ram_info.used / (1024 ** 3), 2)
        
        # GPU e Temperatura são complexos de ler no Windows sem instalar drivers extras, 
        # então mantemos simulados para o painel não quebrar na apresentação
        gpu_simulada = round(random.uniform(5.0, 40.0), 2)
        temp_simulada = round(random.uniform(40.0, 60.0), 2)
        
        gargalo = 1 if cpu_real > 90.0 else 0

        # O Pacote de dados que será enviado pela internet
        payload = {
            "cpu_usage_pct": cpu_real,
            "gpu_usage_pct": gpu_simulada,
            "ram_usage_gb": ram_real_gb,
            "cpu_temp_celsius": temp_simulada,
            "thermal_throttling": 0,
            "gargalo_cpu": gargalo
        }

        # Enviando para a Render
        resposta = requests.post(URL_DA_API, json=payload)
        
        print(f"Enviado! CPU: {cpu_real}% | RAM: {ram_real_gb}GB -> Resposta Nuvem: {resposta.status_code}")
        
    except Exception as e:
        print(f"Erro ao enviar dados: {e}")
        
    time.sleep(1) # Aguarda 1 segundo e manda de novo