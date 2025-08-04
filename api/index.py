from flask import Flask, render_template_string
from binance.client import Client
from dotenv import load_dotenv
import os
import requests
import json

# Load environment variables
load_dotenv()

# Get API keys from .env file
api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET')

app = Flask(__name__)

@app.route('/')
def index():
    total_value_in_usd = 0.0
    balances = []

    # Binance istemcisini oluşturun
    client = Client(api_key, api_secret)

    # Hesap bilgilerini alın
    account_info = client.get_account()

    for balance in account_info['balances']:
        asset = balance['asset']
        free_balance = float(balance['free'])
        
        if free_balance > 0:
            # Her bir kripto paranın USD cinsinden fiyatını alın
            try:
                if asset != 'USDT':
                    price = client.get_symbol_ticker(symbol=f"{asset}USDT")['price']
                    value_in_usd = free_balance * float(price)
                else:
                    value_in_usd = free_balance  # USDT cinsinden zaten
            except Exception as e:
                print(f"{asset} için fiyat alınamadı: {e}")
                continue
            
            balances.append({
                'coin': asset,
                'balance': free_balance,
                'value_in_usd': value_in_usd
            })
            total_value_in_usd += value_in_usd

    # USDT/TRY fiyatını Binance API üzerinden alın
    try:
        usdt_try_price = float(requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDTTRY").json()['price'])
        total_value_in_try = total_value_in_usd * usdt_try_price
        
        # Her coin için TRY değeri ve yüzde hesapla
        for balance in balances:
            balance['value_in_try'] = balance['value_in_usd'] * usdt_try_price
            balance['percentage'] = (balance['value_in_usd'] / total_value_in_usd) * 100 if total_value_in_usd > 0 else 0
            
    except Exception as e:
        print(f"USDT/TRY fiyatı alınamadı: {e}")
        total_value_in_try = None
        usdt_try_price = None

    # Pie chart için veri hazırla
    chart_data = []
    for balance in balances:
        chart_data.append({
            'label': balance['coin'],
            'value': balance['percentage']
        })

    # HTML içeriği
    html_content = '''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title> ${{ "%.2f"|format(total_value_in_usd) }} USD</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
        <style>
            * {
                box-sizing: border-box;
            }
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 10px;
                background-color: #f5f5f5;
                color: #333;
            }
            .main-container {
                max-width: 1400px;
                margin: 2% auto;
            }
            .container {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                margin-top: 20px;
            }
            .table-container {
                background: #ffffff;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .chart-container {
                background: #ffffff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                height: fit-content;
            }
            .chart-wrapper {
                position: relative;
                height: 300px;
                width: 100%;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
                font-size: 14px;
            }
            th {
                background-color: #f8f9fa;
                font-weight: bold;
                position: sticky;
                top: 0;
            }
            tr:hover {
                background-color: #f8f9fa;
            }
            .header {
                text-align: center;
                margin-bottom: 20px;
            }
            .header h1 {
                margin: 0;
                font-size: 24px;
            }
            .summary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .summary h2 {
                margin-top: 0;
                font-size: 20px;
            }
            .summary p {
                margin: 10px 0;
                font-size: 16px;
            }
            .refresh-btn, .time-range-select {
                background: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin-bottom: 20px;
                width: 100%;
                max-width: 200px;
            }
            .refresh-btn:hover, .time-range-select:hover {
                background: #0056b3;
            }
            .coin-name {
                font-weight: bold;
                color: #007bff;
                cursor: pointer;
                text-decoration: underline;
                transition: color 0.3s ease;
            }
            .coin-name:hover {
                color: #0056b3;
            }
            .price-modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }
            .modal-content {
                background-color: #fefefe;
                color: #333;
                margin: 5% auto;
                padding: 15px;
                border-radius: 10px;
                width: 90%;
                max-width: 500px;
                text-align: center;
                position: relative;
                max-height: 85vh;
           }
            .close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
                position: absolute;
                right: 15px;
                top: 10px;
            }
            .close:hover {
                color: #333;
            }
            .price-info {
                margin: 20px 0;
            }
            .current-price {
                font-size: 28px;
                font-weight: bold;
                color: #28a745;
                margin: 15px 0;
            }
            .price-change {
                font-size: 16px;
                margin: 10px 0;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            .price-up {
                background-color: #d4edda;
                color: #155724;
            }
            .price-down {
                background-color: #f8d7da;
                color: #721c24;
            }
            .loading {
                color: #007bff;
                font-style: italic;
                font-size: 18px;
            }
            .percentage {
                background: #e7f3ff;
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            .table-title {
                padding: 15px 20px;
                margin: 0;
                background: #f8f9fa;
                font-size: 18px;
            }
            .mini-chart {
                width: 100%;
                height: 200px;
                margin: 20px 0;
            }
            .coin-info {
                text-align: left;
                margin: 20px 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
            }
            .coin-info h4 {
                margin-top: 0;
            }
            .coin-info p {
                margin: 5px 0;
            }
            .websocket-status {
                position: absolute;
                top: 50px;
                right: 20px;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
            }
            .ws-connected {
                background-color: #d4edda;
                color: #155724;
            }
            .ws-disconnected {
                background-color: #f8d7da;
                color: #721c24;
            }

            /* Tablet için (768px - 1024px) */
            @media (max-width: 1024px) {
                .container {
                    grid-template-columns: 1fr;
                }
                .chart-container {
                    order: -1;
                }
                .chart-wrapper {
                    height: 250px;
                }
                th, td {
                    padding: 6px 4px;
                    font-size: 12px;
                }
            }

            /* Telefon için (max-width: 768px) */
            @media (max-width: 768px) {
                body {
                    padding: 5px;
                }
                .header h1 {
                    font-size: 20px;
                }
                .summary {
                    padding: 15px;
                }
                .summary h2 {
                    font-size: 18px;
                }
                .summary p {
                    font-size: 14px;
                }
                .chart-wrapper {
                    height: 200px;
                }
                .chart-container {
                    padding: 15px;
                }
                .table-title {
                    font-size: 16px;
                    padding: 12px 15px;
                }
                th, td {
                    padding: 4px 2px;
                    font-size: 11px;
                }
                .coin-name {
                    font-size: 12px;
                }
                .percentage {
                    font-size: 10px;
                    padding: 1px 4px;
                }
                .table-container {
                    overflow-x: auto;
                }
                table {
                    min-width: 500px;
                }
                .modal-content {
                    width: 95%;
                    margin: 5% auto;
                    max-height: 90vh;
                    padding: 10px;
                }
                .mini-chart {
                    height: 180px;
                }
            }

            /* Çok küçük telefonlar (max-width: 480px) */
            @media (max-width: 480px) {
                .header h1 {
                    font-size: 18px;
                }
                .chart-wrapper {
                    height: 180px;
                }
                .summary {
                    padding: 12px;
                }
                .summary h2 {
                    font-size: 16px;
                }
                .summary p {
                    font-size: 13px;
                }
                th, td {
                    padding: 3px 1px;
                    font-size: 10px;
                }
                .refresh-btn, .time-range-select {
                    font-size: 14px;
                    padding: 10px 20px;
                }
                .modal-content {
                    padding: 8px;
                }
                .mini-chart {
                    height: 160px;
                }
            }
        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="header">
                <h1>🚀 Binance Portföy Takipçisi</h1>
            </div>

            <form method="POST">
                <button type="submit" class="refresh-btn">🔄 Portföyü Yenile</button>
            </form>

            {% if balances %}
                <div class="summary">
                    <h2>💰 Portföy Özeti</h2>
                    <p><strong>Toplam Değer (USD):</strong> ${{ "%.2f"|format(total_value_in_usd) }}</p>
                    {% if total_value_in_try is not none %}
                        <p><strong>Toplam Değer (TRY):</strong> ₺{{ "%.2f"|format(total_value_in_try) }}</p>
                    {% endif %}
                </div>

                <div class="container">
                    <div class="table-container">
                        <h3 class="table-title">📊 Detaylı Bakiye Bilgileri</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Coin</th>
                                    <th>Bakiye</th>
                                    <th>USD</th>
                                    <th>TRY</th>
                                    <th>%</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for balance in balances %}
                                <tr>
                                    <td class="coin-name" onclick="openCoinModal('{{ balance.coin }}')">{{ balance.coin }}</td>
                                    <td>{{ "%.6f"|format(balance.balance) }}</td>
                                    <td>${{ "%.2f"|format(balance.value_in_usd) }}</td>
                                    <td>₺{{ "%.2f"|format(balance.value_in_try) }}</td>
                                    <td><span class="percentage">{{ "%.1f"|format(balance.percentage) }}%</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>

                    <div class="chart-container">
                        <h3 style="margin-top: 0;">📈 Portföy Dağılımı</h3>
                        <div class="chart-wrapper">
                            <canvas id="portfolioChart"></canvas>
                        </div>
                    </div>
                </div>
            {% else %}
                <div class="summary">
                    <p>Portföy bilgisi bulunamadı veya yüklenemedi.</p>
                </div>
            {% endif %}
        </div>

        <!-- Coin Modal -->
        <div id="coinModal" class="price-modal">
            <div class="modal-content">
                <span class="close" onclick="closeCoinModal()">&times;</span>
                <div class="websocket-status ws-disconnected" id="wsStatus">● Bağlanıyor...</div>
                
                <h3 id="coinTitle">Coin Bilgileri</h3>
                
                <div class="price-info">
                    <div class="current-price" id="currentPrice">
                        <span class="loading">Fiyat yükleniyor...</span>
                    </div>
                    <div class="price-change" id="priceChange"></div>
                </div>

                <div class="coin-info" id="coinInfo">
                    <h4>📊 24 Saat İstatistikleri</h4>
                    <p><strong>Yüksek:</strong> <span id="high24h">-</span></p>
                    <p><strong>Düşük:</strong> <span id="low24h">-</span></p>
                </div>

                <select class="time-range-select" onchange="loadChartData(currentCoin, this.value)">
                    <option value="31">Son 31 Gün</option>
                    <option value="14">Son 14 Gün</option>
                    <option value="3">Son 3 Gün</option>
                </select>

                <div class="mini-chart">
                    <canvas id="miniChart"></canvas>
                </div>
            </div>
        </div>

        <script>
            let currentSocket = null;
            let miniChart = null;
            let currentCoin = '';

            {% if balances %}
            // Pie chart için veri hazırla
            const chartData = {{ chart_data | tojson }};
            
            // Renk paleti
            const colors = [
                '#FF6384','#36A2EB','#FFCE56','#4BC0C0','#9966FF','#FF9F40',
                '#b02f21','#8DD17E','#D65DB1','#FF6F61','#6B5B95','#88B04B',
                '#F7CAC9','#92A8D1','#955251','#B565A7','#009B77','#DD4124','#45B8AC','#EFC050' 
            ];

            const ctx = document.getElementById('portfolioChart').getContext('2d');
            const portfolioChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: chartData.map(item => item.label),
                    datasets: [{
                        data: chartData.map(item => item.value),
                        backgroundColor: colors.slice(0, chartData.length),
                        borderColor: '#fff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 10,
                                usePointStyle: true,
                                font: {
                                    size: window.innerWidth < 768 ? 10 : 12
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.label + ': ' + context.parsed.toFixed(1) + '%';
                                }
                            }
                        }
                    },
                    layout: {
                        padding: {
                            top: 10,
                            bottom: 10
                        }
                    }
                }
            });
            {% endif %}

            // Modal fonksiyonları
            function openCoinModal(coin) {
                currentCoin = coin;
                document.getElementById('coinModal').style.display = 'block';
                document.getElementById('coinTitle').textContent = coin + ' Detay Bilgileri';
                document.querySelector('.time-range-select').value = '31'; // Varsayılan 31 gün
                
                // WebSocket bağlantısını başlat
                connectWebSocket(coin);
                
                // 31 günlük veri al (varsayılan)
                loadChartData(coin, 31);
                
                // 24 saat istatistiklerini al
                load24hStats(coin);
            }

            function closeCoinModal() {
                document.getElementById('coinModal').style.display = 'none';
                if (currentSocket) {
                    currentSocket.close();
                    currentSocket = null;
                }
                if (miniChart) {
                    miniChart.destroy();
                    miniChart = null;
                }
            }

            function connectWebSocket(coin) {
                if (currentSocket) {
                    currentSocket.close();
                }

                if (coin === 'USDT') {
                    document.getElementById('currentPrice').innerHTML = '<span style="color: #28a745;">$1.0000</span>';
                    document.getElementById('priceChange').textContent = 'USDT sabit değerli coin';
                    document.getElementById('wsStatus').textContent = '● Sabit Değer';
                    document.getElementById('wsStatus').className = 'websocket-status ws-connected';
                    return;
                }

                const wsUrl = `wss://stream.binance.com:9443/ws/${coin.toLowerCase()}usdt@ticker`;
                currentSocket = new WebSocket(wsUrl);

                currentSocket.onopen = function(event) {
                    document.getElementById('wsStatus').textContent = '● Bağlandı';
                    document.getElementById('wsStatus').className = 'websocket-status ws-connected';
                };

                currentSocket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    const price = parseFloat(data.c).toFixed(6);
                    const change = parseFloat(data.P).toFixed(2);
                    
                    document.getElementById('currentPrice').innerHTML = `<span style="color: #28a745;">$${price}</span>`;
                    
                    const changeClass = change >= 0 ? 'price-up' : 'price-down';
                    const changeSymbol = change >= 0 ? '+' : '';
                    document.getElementById('priceChange').innerHTML = 
                        `<span class="${changeClass}">24s Değişim: ${changeSymbol}${change}%</span>`;
                };

                currentSocket.onerror = function(error) {
                    document.getElementById('wsStatus').textContent = '● Bağlantı Hatası';
                    document.getElementById('wsStatus').className = 'websocket-status ws-disconnected';
                };

                currentSocket.onclose = function(event) {
                    document.getElementById('wsStatus').textContent = '● Bağlantı Kesildi';
                    document.getElementById('wsStatus').className = 'websocket-status ws-disconnected';
                };
            }

            async function load24hStats(coin) {
                if (coin === 'USDT') {
                    document.getElementById('high24h').textContent = '$1.0000';
                    document.getElementById('low24h').textContent = '$1.0000';
                    return;
                }

                try {
                    const response = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${coin}USDT`);
                    const data = await response.json();
                    
                    document.getElementById('high24h').textContent = '$' + parseFloat(data.highPrice).toFixed(6);
                    document.getElementById('low24h').textContent = '$' + parseFloat(data.lowPrice).toFixed(6);
                } catch (error) {
                    console.error('24h stats yüklenemedi:', error);
                }
            }

            async function loadChartData(coin, days) {
                if (coin === 'USDT') {
                    createFlatChart();
                    return;
                }

                try {
                    const limit = days == 31 ? 32 : days == 14 ? 15 : 10; // 31 gün için 32, 14 gün için 15, 3 gün için 10 veri noktası
                    const response = await fetch(`https://api.binance.com/api/v3/klines?symbol=${coin}USDT&interval=1d&limit=${limit}`);
                    const data = await response.json();
                    
                    const prices = data.map(kline => parseFloat(kline[4])); // Close price
                    const dates = data.map(kline => {
                        const date = new Date(kline[0]);
                        return date.toLocaleDateString('tr-TR', { month: 'short', day: 'numeric' });
                    });
                    
                    createMiniChart(dates.slice(-days), prices.slice(-days), coin, days);
                } catch (error) {
                    console.error(`${days} günlük veri yüklenemedi:`, error);
                    document.querySelector('.mini-chart').innerHTML = '<p style="text-align: center;">Grafik yüklenemedi</p>';
                }
            }

            function createFlatChart() {
                const ctx = document.getElementById('miniChart').getContext('2d');
                if (miniChart) {
                    miniChart.destroy();
                }

                miniChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'],
                        datasets: [{
                            label: 'USDT Fiyat',
                            data: [1, 1, 1, 1, 1, 1, 1],
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            borderWidth: 2,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                min: 0.99,
                                max: 1.01,
                                ticks: {
                                    font: {
                                        size: 10
                                    },
                                    padding: 5
                                }
                            },
                            x: {
                                ticks: {
                                    font: {
                                        size: 10
                                    }
                                }
                            }
                        }
                    }
                });
            }

            function createMiniChart(labels, data, coin, days) {
                const ctx = document.getElementById('miniChart').getContext('2d');
                if (miniChart) {
                    miniChart.destroy();
                }

                const firstPrice = data[0];
                const lastPrice = data[data.length - 1];
                const isUp = lastPrice > firstPrice;

                // Dinamik ondalık basamak sayısı
                const maxPrice = Math.max(...data);
                const decimalPlaces = maxPrice > 100 ? 2 : maxPrice > 1 ? 4 : 6;

                // Büyük sayılar için kısaltma (ör. 12000 -> 12K)
                function formatPrice(value) {
                    if (value >= 1000) {
                        return '$' + (value / 1000).toFixed(1) + 'K';
                    }
                    return '$' + value.toFixed(decimalPlaces);
                }

                miniChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: coin + ' Fiyat (' + (days == 31 ? '31 Gün' : days == 14 ? '14 Gün' : '3 Gün') + ')',
                            data: data,
                            borderColor: isUp ? '#28a745' : '#dc3545',
                            backgroundColor: isUp ? 'rgba(40, 167, 69, 0.1)' : 'rgba(220, 53, 69, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            pointBackgroundColor: isUp ? '#28a745' : '#dc3545',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                ticks: {
                                    callback: function(value) {
                                        return formatPrice(value);
                                    },
                                    font: {
                                        size: 10
                                    },
                                    padding: 5,
                                    maxTicksLimit: 6
                                },
                                grid: {
                                    drawBorder: false
                                }
                            },
                            x: {
                                ticks: {
                                    maxTicksLimit: days == 31 ? 10 : days == 14 ? 7 : 3,
                                    font: {
                                        size: 10
                                    }
                                },
                                grid: {
                                    drawBorder: false
                                }
                            }
                        },
                        layout: {
                            padding: {
                                left: 0,
                                right: 10,
                                top: 10,
                                bottom: 10
                            }
                        },
                        interaction: {
                            intersect: false,
                            mode: 'index'
                        }
                    }
                });
            }

            // Modal dış alanına tıklayınca kapat
            window.onclick = function(event) {
                const modal = document.getElementById('coinModal');
                if (event.target === modal) {
                    closeCoinModal();
                }
            }
        </script>
    </body>
    </html>
    '''

    return render_template_string(html_content, 
                                balances=balances, 
                                total_value_in_usd=total_value_in_usd, 
                                total_value_in_try=total_value_in_try,
                                chart_data=chart_data)

@app.route('/', methods=['POST'])
def refresh():
    return index()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)