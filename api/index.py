from flask import Flask, render_template_string, request, jsonify, send_file, flash, redirect, url_for, Response
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import uuid
import base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'secret-key'

# Bellekte saklanan resimler için cache
image_cache = {}

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
        <p>Resimler geçici bellekte saklanıyor. Sunucu yeniden başlatılınca silinir.</p>
        {% for image in images %}
            <div style="margin: 10px; border: 1px solid #ccc; padding: 10px;">
                <h3>{{ image.filename }}</h3>
                <img src="/image/{{ image.id }}" width="200" 
                     style="cursor: pointer;" 
                     onclick="openImageBlob('{{ image.id }}')">
                <br><br>
                <button onclick="downloadImage('{{ image.id }}', '{{ image.filename }}')">İndir</button>
                <button onclick="openImageBlob('{{ image.id }}')">Yeni Sayfada Görüntüle</button>
            </div>
        {% endfor %}
    {% endif %}
    
    <script>
        function openImageBlob(imageId) {
            fetch(`/image/${imageId}`)
                .then(response => response.blob())
                .then(blob => {
                    const blobUrl = URL.createObjectURL(blob);
                    const newWindow = window.open();
                    newWindow.document.write(`
                        <html>
                            <head>
                                <title>Avatar Image</title>
                                <style>
                                    body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #000; }
                                    img { max-width: 100vw; max-height: 100vh; object-fit: contain; }
                                </style>
                            </head>
                            <body>
                                <img src="${blobUrl}" alt="Avatar">
                            </body>
                        </html>
                    `);
                })
                .catch(error => {
                    console.error('Resim yüklenirken hata:', error);
                    alert('Resim yüklenirken hata oluştu!');
                });
        }
        
        function downloadImage(imageId, filename) {
            fetch(`/image/${imageId}`)
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => {
                    console.error('İndirme hatası:', error);
                    alert('İndirme sırasında hata oluştu!');
                });
        }
    </script>
</body>
</html>
"""

def download_avatar(username, cookies_path=None):
    """Instagram avatar indir - geçici klasör kullan ve bellekte sakla"""
    try:
        avatar_url = f"https://www.instagram.com/{username}/avatar"
        
        # Geçici klasör oluştur
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = ['gallery-dl', '-D', temp_dir]
            
            if cookies_path and os.path.exists(cookies_path):
                cmd.extend(['--cookies', cookies_path])
            
            cmd.append(avatar_url)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # İndirilen dosyaları bul ve bellekte sakla
                files = list(Path(temp_dir).rglob('*'))
                image_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']]
                
                if image_files:
                    cached_images = []
                    for file_path in image_files:
                        # Dosyayı oku
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                        
                        # Benzersiz ID oluştur
                        image_id = str(uuid.uuid4())
                        
                        # Cache'e kaydet
                        image_cache[image_id] = {
                            'data': file_data,
                            'filename': file_path.name,
                            'content_type': 'image/jpeg' if file_path.suffix.lower() in ['.jpg', '.jpeg'] else f'image/{file_path.suffix[1:].lower()}'
                        }
                        
                        cached_images.append({
                            'id': image_id,
                            'filename': file_path.name
                        })
                    
                    return True, cached_images
            
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

@app.route('/image/<image_id>')
def serve_image(image_id):
    """Bellekten resim sun"""
    if image_id in image_cache:
        image_data = image_cache[image_id]
        return Response(
            image_data['data'],
            mimetype=image_data['content_type'],
            headers={
                'Content-Disposition': f'inline; filename="{image_data["filename"]}"',
                'Cache-Control': 'public, max-age=3600'
            }
        )
    return "Resim bulunamadı", 404

@app.route('/file/<username>/<filename>')
def serve_file(username, filename):
    """Eski uyumluluk için - artık kullanılmıyor"""
    return "Dosya sistemi kullanılamıyor, resimler bellekte saklanıyor", 404

if __name__ == '__main__':
    print("Sunucu başlatılıyor: http://localhost:5000")
    print("Not: Resimler bellekte saklanır, sunucu yeniden başlatılınca silinir.")
    app.run(debug=True, host='0.0.0.0', port=5000)
