import os
import psycopg2
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import asyncio
import time

app = FastAPI()

# Criando a estrutura de segurança (Schema) para receber os dados
class MetricaHardware(BaseModel):
    cpu_usage_pct: float
    gpu_usage_pct: float
    ram_usage_gb: float
    cpu_temp_celsius: float
    thermal_throttling: int
    gargalo_cpu: int

def conectar_banco():
    url_banco = os.getenv("DATABASE_URL", "postgresql://admin:adminpassword@db:5432/telemetria")
    while True:
        try:
            conexao = psycopg2.connect(url_banco)
            return conexao
        except psycopg2.OperationalError:
            time.sleep(2)

@app.on_event("startup")
def criar_tabela():
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metricas_hardware (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cpu_usage_pct REAL,
            gpu_usage_pct REAL,
            ram_usage_gb REAL,
            cpu_temp_celsius REAL,
            thermal_throttling INTEGER,
            gargalo_cpu INTEGER
        )
    """)
    conexao.commit()
    conexao.close()

# ROTA NOVA: É aqui que o seu notebook vai "bater" para entregar os dados
@app.post("/api/enviar-telemetria")
def receber_dados(metrica: MetricaHardware):
    try:
        from datetime import datetime
        timestamp_agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO metricas_hardware 
            (timestamp, cpu_usage_pct, gpu_usage_pct, ram_usage_gb, cpu_temp_celsius, thermal_throttling, gargalo_cpu)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (timestamp_agora, metrica.cpu_usage_pct, metrica.gpu_usage_pct, metrica.ram_usage_gb, 
              metrica.cpu_temp_celsius, metrica.thermal_throttling, metrica.gargalo_cpu))
        conexao.commit()
        conexao.close()
        return {"status": "sucesso", "mensagem": "Dado inserido no banco"}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
    
def obter_dados_dashboard():
    conexao = conectar_banco()
    query = "SELECT * FROM metricas_hardware ORDER BY timestamp DESC LIMIT 30"
    df = pd.read_sql_query(query, conexao)
    df['timestamp'] = df['timestamp'].astype(str)
    conexao.close()
    return df

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                df = obter_dados_dashboard()
                if not df.empty:
                    data = df.to_dict(orient="records")
                    await websocket.send_json(data)
            except Exception as e:
                print(f"ERRO NO WEBSOCKET: {e}")
                pass
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

@app.get("/", response_class=HTMLResponse)
def renderizar_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - Telemetria de Infraestrutura</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            body { background-color: #0b0f19; color: #e2e8f0; padding: 20px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #1e293b; padding-bottom: 15px; }
            .header h1 { color: #38bdf8; font-size: 24px; font-weight: 600; }
            .status-live { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #10b981; background: rgba(16, 185, 129, 0.1); padding: 6px 12px; border-radius: 20px; }
            .dot { height: 8px; width: 8px; background-color: #10b981; border-radius: 50%; animation: blink 1.5s infinite; }
            @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
            .kpi-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
            .kpi-card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #334155; }
            .kpi-title { font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
            .kpi-value { font-size: 28px; font-weight: bold; color: #f8fafc; }
            .kpi-alert { color: #ef4444; }
            .kpi-ok { color: #10b981; }
            .charts-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .chart-box { background: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; height: 400px; }
            .chart-title { font-size: 15px; color: #cbd5e1; margin-bottom: 15px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Monitoramento de Infraestrutura (WebSocket)</h1>
            <div class="status-live"><span class="dot"></span> TUNEL TCP ATIVO</div>
        </div>

        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-title">CPU Atual</div>
                <div class="kpi-value" id="kpi-cpu">--%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Memória RAM</div>
                <div class="kpi-value" id="kpi-temp">-- GB</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Status da Máquina</div>
                <div class="kpi-value" id="kpi-status-termico">--</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Gargalo Processamento</div>
                <div class="kpi-value" id="kpi-status-gargalo">--</div>
            </div>
        </div>

        <div class="charts-container">
            <div class="chart-box">
                <div class="chart-title">Carga de Processamento (CPU vs GPU)</div>
                <canvas id="chartCpuGpu"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Uso de Memória RAM (GB)</div>
                <canvas id="chartTemp"></canvas>
            </div>
        </div>

        <script>
            let graficoCpuGpu;
            let graficoTemp;

            function inicializarGraficos() {
                const ctxCpu = document.getElementById('chartCpuGpu').getContext('2d');
                graficoCpuGpu = new Chart(ctxCpu, {
                    type: 'line',
                    data: { labels: [], datasets: [
                        { label: 'CPU (%)', borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)', borderWidth: 2, pointRadius: 0, tension: 0.3, data: [], fill: true },
                        { label: 'GPU (%)', borderColor: '#a855f7', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 0, tension: 0.3, data: [] }
                    ]},
                    options: { responsive: true, maintainAspectRatio: false, animation: { duration: 0 }, scales: { 
                        y: { min: 0, max: 100, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', maxTicksLimit: 10 } }
                    }, plugins: { legend: { labels: { color: '#cbd5e1' } } } }
                });

                const ctxTemp = document.getElementById('chartTemp').getContext('2d');
                graficoTemp = new Chart(ctxTemp, {
                    type: 'line',
                    data: { labels: [], datasets: [
                        { label: 'RAM (GB)', borderColor: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderWidth: 2, pointRadius: 0, tension: 0.3, data: [], fill: true }
                    ]},
                    options: { responsive: true, maintainAspectRatio: false, animation: { duration: 0 }, scales: { 
                        y: { min: 0, max: 32, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', maxTicksLimit: 10 } }
                    }, plugins: { legend: { labels: { color: '#cbd5e1' } } } }
                });
            }

            function atualizarKPIs(dadoRecente) {
                document.getElementById('kpi-cpu').textContent = dadoRecente.cpu_usage_pct + '%';
                document.getElementById('kpi-temp').textContent = dadoRecente.ram_usage_gb + ' GB';

                const elTermico = document.getElementById('kpi-status-termico');
                if (dadoRecente.cpu_usage_pct > 85) {
                    elTermico.textContent = 'ESTRESSADA';
                    elTermico.className = 'kpi-value kpi-alert';
                } else {
                    elTermico.textContent = 'ESTÁVEL';
                    elTermico.className = 'kpi-value kpi-ok';
                }

                const elGargalo = document.getElementById('kpi-status-gargalo');
                if (dadoRecente.gargalo_cpu === 1) {
                    elGargalo.textContent = 'DETECTADO';
                    elGargalo.className = 'kpi-value kpi-alert';
                } else {
                    elGargalo.textContent = 'NORMAL';
                    elGargalo.className = 'kpi-value kpi-ok';
                }
            }

            inicializarGraficos();

            const protocolo = window.location.protocol === "https:" ? "wss://" : "ws://";
            const ws = new WebSocket(protocolo + window.location.host + "/ws");

            ws.onmessage = function(event) {
                let dados = JSON.parse(event.data);
                dados = dados.reverse();

                if (dados.length > 0) {
                    atualizarKPIs(dados[dados.length - 1]);

                    const labels = dados.map(d => d.timestamp.split(' ')[1]);
                    const cpuData = dados.map(d => d.cpu_usage_pct);
                    const gpuData = dados.map(d => d.gpu_usage_pct);
                    const ramData = dados.map(d => d.ram_usage_gb);

                    graficoCpuGpu.data.labels = labels;
                    graficoCpuGpu.data.datasets[0].data = cpuData;
                    graficoCpuGpu.data.datasets[1].data = gpuData;
                    graficoCpuGpu.update();

                    graficoTemp.data.labels = labels;
                    graficoTemp.data.datasets[0].data = ramData;
                    graficoTemp.update();
                }
            };
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)