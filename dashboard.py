import psycopg2
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import time

app = FastAPI()

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
                data = df.to_dict(orient="records")
                await websocket.send_json(data)
            except Exception:
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
                <div class="kpi-title">Temperatura Atual</div>
                <div class="kpi-value" id="kpi-temp">--°C</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Status Térmico</div>
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
                <div class="chart-title">Evolução Térmica (°C)</div>
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
                        { label: 'Temperatura (°C)', borderColor: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderWidth: 2, pointRadius: 0, tension: 0.3, data: [], fill: true }
                    ]},
                    options: { responsive: true, maintainAspectRatio: false, animation: { duration: 0 }, scales: { 
                        y: { min: 30, max: 100, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', maxTicksLimit: 10 } }
                    }, plugins: { legend: { labels: { color: '#cbd5e1' } } } }
                });
            }

            function atualizarKPIs(dadoRecente) {
                document.getElementById('kpi-cpu').textContent = dadoRecente.cpu_usage_pct + '%';
                document.getElementById('kpi-temp').textContent = dadoRecente.cpu_temp_celsius + '°C';

                const elTermico = document.getElementById('kpi-status-termico');
                if (dadoRecente.thermal_throttling === 1) {
                    elTermico.textContent = 'ALERTA';
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
            const ws = new WebSocket(protocol + window.location.host + "/ws");

            ws.onmessage = function(event) {
                let dados = JSON.parse(event.data);
                dados = dados.reverse();

                if (dados.length > 0) {
                    atualizarKPIs(dados[dados.length - 1]);

                    const labels = dados.map(d => d.timestamp.split(' ')[1]);
                    const cpuData = dados.map(d => d.cpu_usage_pct);
                    const gpuData = dados.map(d => d.gpu_usage_pct);
                    const tempData = dados.map(d => d.cpu_temp_celsius);

                    graficoCpuGpu.data.labels = labels;
                    graficoCpuGpu.data.datasets[0].data = cpuData;
                    graficoCpuGpu.data.datasets[1].data = gpuData;
                    graficoCpuGpu.update();

                    graficoTemp.data.labels = labels;
                    graficoTemp.data.datasets[0].data = tempData;
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