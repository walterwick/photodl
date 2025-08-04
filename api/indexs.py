from flask import Flask, render_template_string
from binance.client import Client
from dotenv import load_dotenv
import os
import requests

# .env dosyasını yükle
load_dotenv()

# API anahtarlarını .env dosyasından al
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
    except Exception as e:
        print(f"USDT/TRY fiyatı alınamadı: {e}")
        total_value_in_try = None

    # HTML içeriği
    html_content = '''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>"{{ total_value_in_usd }}"</title>
    </head>
    <body>
        <h1>Binance Bakiye Kontrol</h1>
        <form method="POST">
            <input type="submit" value="Bakiye Kontrol Et">
        </form>

        {% if balances %}
            <h2>Bakiye Bilgileri</h2>
            <table border="1">
                <tr>
                    <th>Coin</th>
                    <th>Bakiye</th>
                    <th>Değer (USD)</th>
                </tr>
                {% for balance in balances %}
                <tr>
                    <td>{{ balance.coin }}</td>
                    <td>{{ balance.balance }}</td>
                    <td>{{ balance.value_in_usd }}</td>
                </tr>
                {% endfor %}
            </table>
            <h3>Toplam Değer (USD): {{ total_value_in_usd }}</h3>
            {% if total_value_in_try is not none %}
                <h3>Toplam Değer: (TRY): {{ total_value_in_try }}</h3>
            {% endif %}
        {% endif %}
    </body>
    </html>
    '''

    return render_template_string(html_content, balances=balances, total_value_in_usd=total_value_in_usd, total_value_in_try=total_value_in_try)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
