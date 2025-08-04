from flask import Flask, render_template_string, request, jsonify, send_file, flash, redirect, url_for
import subprocess
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'secret-key'

# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Instagram Avatar İndirici</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Instagram Avatar İndirici</h1>
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
                <p style="color: red;">{{ message }}</p>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <form method="POST" action="/download">
        <p>
            <label>Instagram Kullanıcı Adı:</label><br>
            <input type="text" name="username" placeholder="kullanici_adi" required>
        </p>
        <p>
            <label>Cookies Dosya Yolu (isteğe bağlı):</label><br>
            <input type="text" name="cookies_path" placeholder="C:\\Users\\...\\cookies.txt">
        </p>
        <p>
            <button type="submit">Avatar İndir</button>
        </p>
    </form>
    
    {% if images %}
        <h2>{{ username }} - Avatar Resimleri</h2>
        {% for image in images %}
            <div style="margin: 10px; border: 1px solid #ccc; padding: 10px;">
                <h3>{{ image.filename }}</h3>
                <img src="/file/{{ username }}/{{ image.filename }}" width="200" 
                     style="cursor: pointer;" 
                     onclick="openImageBlob('{{ username }}', '{{ image.filename }}')">
                <br><br>
                <a href="/file/{{ username }}/{{ image.filename }}" download>
                    <button>İndir</button>
                </a>
                <button onclick="openImageBlob('{{ username }}', '{{ image.filename }}')">Yeni Sayfada Görüntüle</button>
            </div>
        {% endfor %}
    {% endif %}
    
    <script>
        function openImageBlob(username, filename) {
            fetch(`/file/${username}/${filename}`)
                .then(response => response.blob())
                .then(blob => {
                    const blobUrl = URL.createObjectURL(blob);
                    const newWindow = window.open();
                    newWindow.document.write(`
                        <html>
                            <head>
                                <title>${filename}</title>
                                <style>
                                    body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #000; }
                                    img { max-width: 100vw; max-height: 100vh; object-fit: contain; }
                                </style>
                            </head>
                            <body>
                                <img src="${blobUrl}" alt="${filename}">
                            </body>
                        </html>
                    `);
                })
                .catch(error => {
                    console.error('Resim yüklenirken hata:', error);
                    alert('Resim yüklenirken hata oluştu!');
                });
        }
    </script>
</body>
</html>
"""

def download_avatar(username, cookies_path=None):
    """Instagram avatar indir"""
    try:
        avatar_url = f"https://www.instagram.com/{username}/avatar"
        output_dir = os.path.join('downloads', username)
        os.makedirs(output_dir, exist_ok=True)
        
        cmd = ['gallery-dl', '-D', output_dir]
        
        if cookies_path and os.path.exists(cookies_path):
            cmd.extend(['--cookies', cookies_path])
        
        cmd.append(avatar_url)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_dir):
            files = list(Path(output_dir).glob('*'))
            if files:
                return True, [{'filename': f.name, 'path': str(f)} for f in files]
        
        return False, result.stderr
        
    except Exception as e:
        return False, str(e)

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    username = request.form.get('username', '').strip().lstrip('@')
    cookies_path = request.form.get('cookies_path', '').strip()
    
    if not username:
        flash('Kullanıcı adı gerekli!')
        return redirect(url_for('index'))
    
    success, result = download_avatar(username, cookies_path if cookies_path else None)
    
    if success:
        flash(f'{username} avatarı başarıyla indirildi!')
        return render_template_string(BASE_TEMPLATE, images=result, username=username)
    else:
        flash(f'Hata: {result}')
        return redirect(url_for('index'))

@app.route('/file/<username>/<filename>')
def serve_file(username, filename):
    file_path = os.path.join('downloads', username, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "Dosya bulunamadı", 404

if __name__ == '__main__':
    os.makedirs('downloads', exist_ok=True)
    print("Sunucu başlatılıyor: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)