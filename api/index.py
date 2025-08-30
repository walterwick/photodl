from flask import Flask, request, render_template_string, jsonify
import boto3
import os
from werkzeug.utils import secure_filename
import uuid
from urllib.parse import unquote # Türkçe karakter sorunu için eklendi

# R2 access credentials
AWS_ACCESS_KEY_ID = '112b183cdd116461df8ee2d8a647a58c'
AWS_SECRET_ACCESS_KEY = 'dd104010783bf0278926182bb9a1d0496c6f62907241d5f196918d7089fe005d'
R2_BUCKET = 'walter'
ACCOUNT_ID = '238a54d3f39bc03c25b5550bbd2683ed'

# R2 endpoint URL
R2_ENDPOINT = f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com'
app = Flask(__name__)

s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name='auto'
)

# Resim dosyası uzantıları (Önizleme için)
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif', '.heic', '.tiff'}

# HTML şablonu güncellendi: Yeni Klasör butonu, Resim Önizleme ve ilgili JS eklendi
HTML = """<!DOCTYPE html>
<html lang="tr" data-bs-theme="dark">
<head>
  <meta charset="UTF-8" />
  <title>R2 Dosya Yöneticisi</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    body { background: #1a1a1a; }
    .container-narrow { max-width: 1100px; }
    .folder-card { transition: transform .15s ease, box-shadow .15s ease; background: #2a2a2a; border: 1px solid rgba(255,255,255,.1); }
    .folder-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.3); }
    .file-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 16px;
    }
    .file-card {
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 16px;
      background: #2a2a2a;
      overflow: hidden;
      box-shadow: 0 2px 12px rgba(0,0,0,.2);
      transition: transform .15s ease, box-shadow .15s ease;
    }
    .file-card:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(0,0,0,.3); }
    .thumb-wrap {
      width: 100%;
      aspect-ratio: 16/10;
      background: #333;
      display: flex; align-items: center; justify-content: center;
      overflow: hidden;
    }
    /* Resim önizlemeleri için stil */
    .thumb-wrap img { width: 100%; height: 100%; object-fit: cover; }
    .file-meta { font-size: .9rem; color: #adb5bd; }
    .badge-size { background: #3b3b3b; color: #a5b4fc; }
    .file-title {
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      font-weight: 600;
      color: #e9ecef;
    }
    .thumb-icon { font-size: 2.25rem; color: #6c757d; }
    .crumb a { text-decoration: none; color: #a5b4fc; }
    .crumb a:hover { color: #fff; }
    .btn-wrap {
      display: flex;
      gap: .5rem;
      flex-wrap: wrap;
      justify-content: flex-end;
      flex-direction: row;
    }
    @media (max-width: 576px) {
      .btn-wrap {
        flex-direction: column;
        align-items: stretch;
      }
      .btn-wrap .btn {
        width: 100%;
        text-align: center;
      }
    }
    .click-zone {
      border: 2px dashed #444;
      border-radius: 12px;
      padding: 2rem;
      text-align: center;
      background: #2a2a2a;
      margin-bottom: 1.5rem;
      cursor: pointer;
      transition: all 0.2s ease;
      color: #adb5bd;
    }
    .click-zone:hover {
      border-color: #0d6efd;
      background: #3a3a3a;
    }
    .upload-status { display: none; margin-top: 1rem; }
    .upload-status.show { display: block; }
    .upload-section {
      display: none;
      background: #2a2a2a;
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }
    .upload-section.show { display: block; }
    .progress {
      height: 8px;
      margin-top: 0.5rem;
      background: #333;
    }
    .form-control { background: #333; color: #e9ecef; border-color: #444; }
    .form-control:focus { background: #333; color: #e9ecef; border-color: #0d6efd; }
    .input-group-text { background: #3b3b3b; color: #adb5bd; border-color: #444; }
    .modal-content { background: #2a2a2a; border: 1px solid rgba(255,255,255,.1); }
    .modal-header, .modal-footer { border-color: rgba(255,255,255,.1); }
  </style>
</head>
<body>
  <div class="container container-narrow py-4">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-cloud-fill fs-3 text-primary"></i>
        <h1 class="h3 mb-0">Cloudflare R2 Dosya Yöneticisi</h1>
      </div>
      <div class="d-flex gap-2">
        {% if current_folder %}
          <a href="{{ url_for('home') }}" class="btn btn-outline-secondary">
            <i class="bi bi-house"></i> Ana Dizin
          </a>
        {% endif %}
        <button class="btn btn-outline-warning" onclick="createNewFolder()">
            <i class="bi bi-folder-plus"></i> Yeni Klasör
        </button>
        <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
          <i class="bi bi-upload"></i> Dosya Yükle
        </button>
        <input type="file" id="fileInput" multiple style="display:none;" onchange="handleFiles(this.files)">
      </div>
    </div>

    <div class="click-zone" id="clickZone" onclick="document.getElementById('fileInput').click()">
      <p class="mb-1">Dosya seçmek için buraya tıklayın veya Ctrl+V ile yapıştırın</p>
      <p class="text-muted small">Birden fazla dosya seçebilirsiniz</p>
      <div class="upload-status" id="uploadStatus"></div>
    </div>

    <div class="upload-section" id="uploadSection">
      <h5>Dosya Yükleme</h5>
      <div id="fileList" class="mb-3"></div>
      <div class="mb-3">
        <label for="destinationFolder" class="form-label">Hedef Klasör (boş bırakılırsa mevcut dizin)</label>
        <input type="text" class="form-control" id="destinationFolder" value="{{ current_folder or '' }}">
      </div>
      <button type="button" class="btn btn-primary" onclick="uploadFiles()" id="uploadButton" disabled>Yükle</button>
    </div>

    {% if breadcrumb and breadcrumb|length %}
      <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
          <li class="breadcrumb-item"><a href="{{ url_for('home') }}">Ana Dizin</a></li>
          {% for name, path in breadcrumb %}
            {% if loop.last %}
              <li class="breadcrumb-item active" aria-current="page">{{ name }}</li>
            {% else %}
              <li class="breadcrumb-item"><a href="{{ url_for('browse_folder', folder=path) }}">{{ name }}</a></li>
            {% endif %}
          {% endfor %}
        </ol>
      </nav>
    {% endif %}

    {% if folders %}
      <h4 class="mt-2 mb-2">Klasörler</h4>
      <div class="row g-3 mb-4">
        {% for folder in folders %}
        <div class="col-12 col-md-6 col-lg-4">
          <a href="{{ url_for('browse_folder', folder=(current_folder ~ '/' if current_folder else '') ~ folder) }}" class="text-reset text-decoration-none">
            <div class="p-3 border rounded-4 folder-card d-flex align-items-center gap-3">
              <i class="bi bi-folder-fill text-warning fs-2"></i>
              <div class="flex-grow-1">
                <div class="fw-semibold">{{ folder }}</div>
                <div class="text-muted small">Klasöre git</div>
              </div>
              <i class="bi bi-chevron-right text-muted"></i>
            </div>
          </a>
        </div>
        {% endfor %}
      </div>
    {% endif %}

    {% if files %}
      <h4 class="mt-2 mb-3">Dosyalar</h4>
      <div class="file-grid">
        {% for file in files %}
        <div class="file-card">
          <div class="thumb-wrap">
            {% if file.is_image %}
                <img src="{{ file.url }}" alt="{{ file.name }}" loading="lazy">
            {% else %}
                <div class="text-center">
                  <i class="bi {{ file.icon }} thumb-icon"></i>
                </div>
            {% endif %}
          </div>
          <div class="p-3">
            <div class="file-title mb-1" title="{{ file.name }}">{{ file.name }}</div>
            <div class="d-flex align-items-center justify-content-between">
              <span class="badge badge-size">{{ file.size_h }}</span>
              <div class="btn-wrap">
                <a class="btn btn-sm btn-outline-primary" href="{{ file.url }}" target="_blank" rel="noopener">
                  Aç
                </a>
                <button class="btn btn-sm btn-warning" onclick="openRenameModal('{{ file.key }}', '{{ file.name }}')">
                  Yeniden Adlandır/Taşı
                </button>
                <button class="btn btn-sm btn-danger" onclick="confirmDelete('{{ file.key }}', '{{ file.name }}')">
                  Sil
                </button>
              </div>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
    {% elif not folders %}
      <div class="alert alert-info mt-4">
        Bu dizinde gösterilecek dosya veya klasör yok.
      </div>
    {% endif %}
  </div>

  <div class="modal fade" id="renameModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Dosya Yeniden Adlandır/Taşı</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Kapat"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label for="renameFileName" class="form-label">Yeni Dosya Adı</label>
            <input type="text" class="form-control" id="renameFileName">
          </div>
          <div class="mb-3">
            <label for="renameDestination" class="form-label">Hedef Klasör (boş bırakılırsa ana dizin)</label>
            <input type="text" class="form-control" id="renameDestination" placeholder="örn: se veya klasor1/klasor2">
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
          <button type="button" class="btn btn-primary" id="confirmRenameBtn">Kaydet</button>
        </div>
      </div>
    </div>
  </div>

  <div class="modal fade" id="deleteModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Dosya Silme Onayı</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Kapat"></button>
        </div>
        <div class="modal-body">
          <p><strong id="deleteFileName"></strong> dosyasını silmek istediğinizden emin misiniz?</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
          <button type="button" class="btn btn-danger" id="confirmDeleteBtn">Sil</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const files = {{ files|tojson }};
    const currentFolder = '{{ current_folder or '' }}';
    const renameModalEl = document.getElementById('renameModal');
    const deleteModalEl = document.getElementById('deleteModal');
    const fileListEl = document.getElementById('fileList');
    const uploadSection = document.getElementById('uploadSection');
    const uploadButton = document.getElementById('uploadButton');
    let bsRenameModal, bsDeleteModal;
    let selectedFiles = [];
    let deleteKey = '';
    let renameKey = '';

    document.addEventListener('DOMContentLoaded', function() {
      bsRenameModal = new bootstrap.Modal(renameModalEl);
      bsDeleteModal = new bootstrap.Modal(deleteModalEl);

      // Paste handler
      document.addEventListener('paste', (e) => {
        const files = e.clipboardData.files;
        if (files.length) {
          handleFiles(files);
        }
      });
    });
    
    // YENİ KLASÖR OLUŞTURMA FONKSİYONU
    async function createNewFolder() {
        const folderName = prompt("Oluşturulacak klasörün adını girin:", "Yeni Klasör");
        if (!folderName || folderName.trim() === "") {
            return; // Kullanıcı iptal etti veya boş isim girdi
        }
        
        const path = currentFolder ? `${currentFolder}/${folderName}` : folderName;

        const statusEl = document.getElementById('uploadStatus');
        statusEl.className = 'upload-status show';
        statusEl.innerHTML = `<div class="text-info">'${folderName}' klasörü oluşturuluyor...</div>`;
        
        try {
            const response = await fetch('/create_new_folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            const result = await response.json();
            if (result.success) {
                statusEl.innerHTML = `<div class="text-success">'${folderName}' başarıyla oluşturuldu. Sayfa yenileniyor...</div>`;
                setTimeout(() => window.location.reload(), 1500);
            } else {
                statusEl.innerHTML = `<div class="text-danger">Klasör oluşturulamadı: ${result.error}</div>`;
            }
        } catch (error) {
            statusEl.innerHTML = `<div class="text-danger">Klasör oluşturulamadı: ${error.message}</div>`;
        }
    }

    function handleFiles(files) {
      selectedFiles = Array.from(files);
      fileListEl.innerHTML = '';
      selectedFiles.forEach((file, idx) => {
        const div = document.createElement('div');
        div.className = 'mb-2';
        div.innerHTML = `
          <div class="input-group">
            <input type="text" class="form-control" value="${file.name}" id="fileName${idx}">
            <button class="btn btn-outline-secondary" onclick="randomizeName(${idx})">
              <i class="bi bi-shuffle"></i>
            </button>
            <span class="input-group-text">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
          </div>
          <div class="progress" id="progress${idx}" style="display: none;">
            <div class="progress-bar" role="progressbar" style="width: 0%;" id="progressBar${idx}"></div>
          </div>
        `;
        fileListEl.appendChild(div);
      });
      uploadSection.classList.add('show');
      uploadButton.disabled = selectedFiles.length === 0;
    }

    function randomizeName(idx) {
      const input = document.getElementById(`fileName${idx}`);
      const ext = input.value.split('.').pop();
      const randomName = `${crypto.randomUUID()}.${ext}`;
      input.value = randomName;
    }

    async function uploadFiles() {
      let destination = document.getElementById('destinationFolder').value.trim().replace(/^\\/+|\/+$/g, '');
      if (destination === '') destination = '';
      const statusEl = document.getElementById('uploadStatus');
      statusEl.className = 'upload-status show';
      statusEl.innerHTML = 'Yükleniyor...';
      uploadButton.disabled = true;

      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const newName = document.getElementById(`fileName${i}`).value;
        const key = destination ? `${destination}/${newName}` : newName;
        const progressBar = document.getElementById(`progressBar${i}`);
        const progressDiv = document.getElementById(`progress${i}`);
        progressDiv.style.display = 'block';

        try {
          const formData = new FormData();
          formData.append('file', file, newName);
          formData.append('destination', destination);

          const xhr = new XMLHttpRequest();
          xhr.open('POST', '/upload', true);
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
              const percent = (event.loaded / event.total) * 100;
              progressBar.style.width = `${percent}%`;
            }
          };
          xhr.onload = () => {
            if (xhr.status === 200) {
              statusEl.innerHTML += `<div class="text-success">${newName} başarıyla yüklendi.</div>`;
            } else {
              const errorResult = JSON.parse(xhr.responseText);
              statusEl.innerHTML += `<div class="text-danger">${newName} yüklenemedi: ${errorResult.error || 'Bilinmeyen Hata'}</div>`;
            }
            if (i === selectedFiles.length - 1) { // Son dosya ise
                 setTimeout(() => window.location.reload(), 2000);
            }
          };
          xhr.send(formData);
        } catch (error) {
          progressDiv.style.display = 'none';
          statusEl.innerHTML += `<div class="text-danger">${newName} yüklenemedi: ${error.message}</div>`;
        }
      }
    }

    function openRenameModal(key, name) {
      renameKey = key;
      document.getElementById('renameFileName').value = name;
      document.getElementById('renameDestination').value = key.split('/').slice(0, -1).join('/');
      document.getElementById('confirmRenameBtn').onclick = () => renameFile();
      bsRenameModal.show();
    }

    async function renameFile() {
      const newName = document.getElementById('renameFileName').value;
      let newDestination = document.getElementById('renameDestination').value.trim().replace(/^\\/+|\/+$/g, '');
      const newKey = newDestination ? `${newDestination}/${newName}` : newName;
      
      const response = await fetch('/rename_file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_key: renameKey, new_key: newKey })
      });
      bsRenameModal.hide();
      window.location.reload();
    }

    function confirmDelete(key, name) {
      deleteKey = key;
      document.getElementById('deleteFileName').textContent = name;
      document.getElementById('confirmDeleteBtn').onclick = () => deleteFile();
      bsDeleteModal.show();
    }

    async function deleteFile() {
      const response = await fetch('/delete_file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: deleteKey })
      });
      bsDeleteModal.hide();
      window.location.reload();
    }
  </script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

DOC_ICON_MAP = {
    '.pdf': 'bi-filetype-pdf', '.txt': 'bi-filetype-txt', '.md': 'bi-markdown', '.csv': 'bi-filetype-csv',
    '.xls': 'bi-filetype-xls', '.xlsx': 'bi-filetype-xlsx', '.doc': 'bi-filetype-doc', '.docx': 'bi-filetype-docx',
    '.ppt': 'bi-filetype-ppt', '.pptx': 'bi-filetype-pptx', '.zip': 'bi-file-zip', '.rar': 'bi-file-zip',
    '.7z':  'bi-file-zip', '.json': 'bi-filetype-json', '.js': 'bi-filetype-js', '.html': 'bi-filetype-html',
    '.css': 'bi-filetype-css', '.mp3': 'bi-filetype-mp3', '.wav': 'bi-file-music', '.mp4': 'bi-filetype-mp4',
    '.mov': 'bi-film', '.avi': 'bi-film',
}

def human_size(n):
    step = 1024.0
    if n < step: return f"{n} B"
    n /= step
    if n < step: return f"{n:.1f} KB"
    n /= step
    if n < step: return f"{n:.1f} MB"
    n /= step
    return f"{n:.1f} GB"

def get_ext(name):
    name_low = name.lower()
    dot = name_low.rfind('.')
    return name_low[dot:] if dot != -1 else ''

def build_breadcrumb(current_folder):
    if not current_folder:
        return []
    parts = [p for p in current_folder.strip('/').split('/') if p]
    crumb = []
    accum = []
    for p in parts:
        accum.append(p)
        crumb.append((p, '/'.join(accum)))
    return crumb

@app.route('/')
def home():
    return list_objects(prefix='')

@app.route('/folder/<path:folder>')
def browse_folder(folder):
    # TÜRKÇE KARAKTER SORUNU ÇÖZÜMÜ
    # Gelen 'folder' yolunu URL kodlamasından tamamen arındır
    decoded_folder = unquote(folder)
    prefix = decoded_folder.rstrip('/') + '/'
    return list_objects(prefix=prefix, current_folder=decoded_folder)

def list_objects(prefix, current_folder=None):
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=R2_BUCKET, Prefix=prefix, Delimiter='/')

    folders = []
    files = []

    for page in page_iterator:
        for common_prefix in page.get('CommonPrefixes', []):
            folder_name = common_prefix['Prefix'][len(prefix):].rstrip('/')
            if folder_name:
                folders.append(folder_name)

        for obj in page.get('Contents', []):
            key = obj['Key']
            # .placeholder dosyalarını ve mevcut klasörün kendisini gösterme
            if key == prefix or key.endswith('/.placeholder') or key.endswith('/'): continue
            
            file_name = key[len(prefix):]
            if '/' in file_name: continue

            url = s3.generate_presigned_url(
                'get_object', Params={'Bucket': R2_BUCKET, 'Key': key}, ExpiresIn=3600
            )

            ext = get_ext(file_name)
            icon = DOC_ICON_MAP.get(ext, 'bi-file-earmark')
            is_image = ext in IMAGE_EXTS # RESİM ÖNİZLEME İÇİN KONTROL

            files.append({
                'name': file_name,
                'key': key,
                'url': url,
                'size_h': human_size(obj['Size']),
                'icon': icon,
                'is_image': is_image # Şablona gönderilecek veri
            })

    folders.sort(key=lambda x: x.lower())
    files.sort(key=lambda x: x['name'].lower())

    return render_template_string(
        HTML,
        folders=folders,
        files=files,
        current_folder=current_folder,
        breadcrumb=build_breadcrumb(current_folder)
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    destination = request.form.get('destination', '')
    if not file:
        return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 400

    filename = secure_filename(file.filename)
    key = f"{destination}/{filename}" if destination else filename
    
    # Dosyanın zaten var olup olmadığını kontrol et
    try:
        s3.head_object(Bucket=R2_BUCKET, Key=key)
        return jsonify({'success': False, 'error': f"'{filename}' adında bir dosya zaten var."}), 409 # 409 Conflict
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
             # Dosya yok, yüklemeye devam et
            pass
        else:
            # Başka bir client hatası
            return jsonify({'success': False, 'error': str(e)}), 500
            
    try:
        s3.upload_fileobj(file, R2_BUCKET, key)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/rename_file', methods=['POST'])
def rename_file():
    data = request.get_json()
    old_key = data.get('old_key')
    new_key = data.get('new_key')
    try:
        s3.copy_object(Bucket=R2_BUCKET, CopySource={'Bucket': R2_BUCKET, 'Key': old_key}, Key=new_key)
        s3.delete_object(Bucket=R2_BUCKET, Key=old_key)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    key = data.get('key')
    try:
        s3.delete_object(Bucket=R2_BUCKET, Key=key)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# YENİ KLASÖR OLUŞTURMA ENDPOINT'İ
@app.route('/create_new_folder', methods=['POST'])
def create_new_folder():
    data = request.get_json()
    path = data.get('path', '').strip()
    if not path:
        return jsonify({'success': False, 'error': 'Klasör adı geçersiz.'}), 400

    # S3/R2'de klasörler, içinde nesne olunca var olur.
    # Boş bir klasör oluşturmak için sonuna .placeholder gibi bir nesne ekleriz.
    placeholder_key = f"{path.rstrip('/')}/.placeholder"
    
    try:
        # Önce bu placeholder'ın var olup olmadığını kontrol etmeye gerek yok,
        # üzerine yazmak bir sorun teşkil etmez.
        s3.put_object(Bucket=R2_BUCKET, Key=placeholder_key, Body=b'')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
