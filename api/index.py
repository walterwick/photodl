from flask import Flask, request, render_template_string, jsonify
import boto3
import os
from werkzeug.utils import secure_filename
import uuid

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

# HTML template with dark mode, no image thumbnails, and responsive buttons
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
        <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
          <i class="bi bi-upload"></i> Dosya Yükle
        </button>
        <input type="file" id="fileInput" multiple style="display:none;" onchange="handleFiles(this.files)">
      </div>
    </div>

    <!-- Click-to-select zone -->
    <div class="click-zone" id="clickZone" onclick="document.getElementById('fileInput').click()">
      <p class="mb-1">Dosya seçmek için buraya tıklayın veya Ctrl+V ile yapıştırın</p>
      <p class="text-muted small">Birden fazla dosya seçebilirsiniz</p>
      <div class="upload-status" id="uploadStatus"></div>
    </div>

    <!-- Upload Section -->
    <div class="upload-section" id="uploadSection">
      <h5>Dosya Yükleme</h5>
      <div id="fileList" class="mb-3"></div>
      <div class="mb-3">
        <label for="destinationFolder" class="form-label">Hedef Klasör (örn: se veya klasor1/klasor2, boş bırakılırsa ana dizin)</label>
        <input type="text" class="form-control" id="destinationFolder" placeholder="Klasör yolunu girin veya boş bırakın">
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
            <div class="text-center">
              <i class="bi {{ file.icon }} thumb-icon"></i>
            </div>
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
    {% else %}
      <div class="alert alert-info mt-4">
        Bu dizinde gösterilecek dosya yok.
      </div>
    {% endif %}
  </div>

  <!-- Rename/Move Modal -->
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
            <label for="renameDestination" class="form-label">Hedef Klasör (örn: se veya klasor1/klasor2, boş bırakılırsa ana dizin)</label>
            <input type="text" class="form-control" id="renameDestination" placeholder="Klasör yolunu girin veya boş bırakın">
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">İptal</button>
          <button type="button" class="btn btn-primary" id="confirmRenameBtn">Kaydet</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Delete Confirmation Modal -->
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
      let destination = document.getElementById('destinationFolder').value.trim().replace(/^\/+|\/+$/g, '');
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
          // Check if file exists
          const response = await fetch('/check_file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key })
          });
          const result = await response.json();
          if (result.exists) {
            statusEl.innerHTML += `<div class="text-warning">${newName} zaten var, atlanıyor.</div>`;
            progressDiv.style.display = 'none';
            continue;
          }

          // Ensure folder exists
          if (destination) {
            await fetch('/create_folder', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ folder: destination })
            });
          }

          // Upload file with progress
          const formData = new FormData();
          formData.append('file', file, newName);
          formData.append('destination', destination);

          const xhr = new XMLHttpRequest();
          xhr.open('POST', '/upload', true);
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
              const percent = (event.loaded / event.total) * 100;
              progressBar.style.width = `${percent}%`;
              progressBar.setAttribute('aria-valuenow', percent);
            }
          };
          xhr.onload = () => {
            const uploadResult = JSON.parse(xhr.responseText);
            progressDiv.style.display = 'none';
            if (xhr.status === 200 && uploadResult.success) {
              statusEl.innerHTML += `<div class="text-success">${newName} başarıyla yüklendi.</div>`;
            } else {
              statusEl.innerHTML += `<div class="text-danger">${newName} yüklenemedi: ${uploadResult.error || 'Hata'}</div>`;
            }
          };
          xhr.onerror = () => {
            progressDiv.style.display = 'none';
            statusEl.innerHTML += `<div class="text-danger">${newName} yüklenemedi: Bağlantı hatası</div>`;
          };
          xhr.send(formData);
        } catch (error) {
          progressDiv.style.display = 'none';
          statusEl.innerHTML += `<div class="text-danger">${newName} yüklenemedi: ${error.message}</div>`;
        }
      }

      setTimeout(() => {
        statusEl.className = 'upload-status';
        statusEl.innerHTML = '';
        fileListEl.innerHTML = '';
        selectedFiles = [];
        uploadSection.classList.remove('show');
        uploadButton.disabled = true;
        window.location.reload();
      }, 2000);
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
      let newDestination = document.getElementById('renameDestination').value.trim().replace(/^\/+|\/+$/g, '');
      if (newDestination === '') newDestination = '';
      const newKey = newDestination ? `${newDestination}/${newName}` : newName;
      const statusEl = document.getElementById('uploadStatus');
      statusEl.className = 'upload-status show';

      try {
        // Check if new path exists
        const response = await fetch('/check_file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: newKey })
        });
        const result = await response.json();
        if (result.exists) {
          statusEl.innerHTML = `<div class="text-warning">${newName} zaten var, işlem atlandı.</div>`;
          bsRenameModal.hide();
          return;
        }

        // Ensure new folder exists
        if (newDestination) {
          await fetch('/create_folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder: newDestination })
          });
        }

        // Copy to new key and delete old key
        await fetch('/rename_file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ old_key: renameKey, new_key: newKey })
        });

        statusEl.innerHTML = `<div class="text-success">${newName} başarıyla yeniden adlandırıldı/taşındı.</div>`;
        setTimeout(() => {
          statusEl.className = 'upload-status';
          statusEl.innerHTML = '';
          window.location.reload();
        }, 1500);
      } catch (error) {
        statusEl.innerHTML = `<div class="text-danger">İşlem başarısız: ${error.message}</div>`;
      }
      bsRenameModal.hide();
    }

    function confirmDelete(key, name) {
      deleteKey = key;
      document.getElementById('deleteFileName').textContent = name;
      document.getElementById('confirmDeleteBtn').onclick = () => deleteFile();
      bsDeleteModal.show();
    }

    async function deleteFile() {
      const statusEl = document.getElementById('uploadStatus');
      statusEl.className = 'upload-status show';
      try {
        const response = await fetch('/delete_file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: deleteKey })
        });
        const result = await response.json();
        if (result.success) {
          statusEl.innerHTML = `<div class="text-success">Dosya başarıyla silindi.</div>`;
          setTimeout(() => {
            statusEl.className = 'upload-status';
            statusEl.innerHTML = '';
            window.location.reload();
          }, 1500);
        } else {
          statusEl.innerHTML = `<div class="text-danger">Dosya silinemedi: ${result.error}</div>`;
        }
      } catch (error) {
        statusEl.innerHTML = `<div class="text-danger">Dosya silinemedi: ${error.message}</div>`;
      }
      bsDeleteModal.hide();
    }
  </script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif', '.heic', '.tiff'}

DOC_ICON_MAP = {
    '.pdf': 'bi-filetype-pdf', '.txt': 'bi-filetype-txt', '.md': 'bi-markdown', '.csv': 'bi-filetype-csv',
    '.xls': 'bi-filetype-xls', '.xlsx': 'bi-filetype-xlsx', '.doc': 'bi-filetype-doc', '.docx': 'bi-filetype-docx',
    '.ppt': 'bi-filetype-ppt', '.pptx': 'bi-filetype-pptx', '.zip': 'bi-file-zip', '.rar': 'bi-file-zip',
    '.7z':  'bi-file-zip', '.json': 'bi-filetype-json', '.js': 'bi-filetype-js', '.html': 'bi-filetype-html',
    '.css': 'bi-filetype-css',
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
    prefix = folder.rstrip('/') + '/'
    return list_objects(prefix=prefix, current_folder=folder)

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
            if key == prefix or key.endswith('/'): continue
            file_name = key[len(prefix):]
            if '/' in file_name: continue

            url = s3.generate_presigned_url(
                'get_object', Params={'Bucket': R2_BUCKET, 'Key': key}, ExpiresIn=3600
            )

            ext = get_ext(file_name)
            icon = DOC_ICON_MAP.get(ext, 'bi-file-earmark')

            files.append({
                'name': file_name,
                'key': key,
                'url': url,
                'size_h': human_size(obj['Size']),
                'icon': icon
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

@app.route('/check_file', methods=['POST'])
def check_file():
    data = request.get_json()
    key = data.get('key')
    try:
        s3.head_object(Bucket=R2_BUCKET, Key=key)
        return jsonify({'exists': True})
    except s3.exceptions.ClientError:
        return jsonify({'exists': False})

@app.route('/create_folder', methods=['POST'])
def create_folder():
    data = request.get_json()
    folder = data.get('folder')
    if not folder:
        return jsonify({'success': True})
    try:
        placeholder_key = f"{folder}/.placeholder"
        s3.put_object(Bucket=R2_BUCKET, Key=placeholder_key, Body=b'')
        s3.delete_object(Bucket=R2_BUCKET, Key=placeholder_key)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    destination = request.form.get('destination', '')
    if not file:
        return jsonify({'success': False, 'error': 'Dosya bulunamadı'})

    filename = secure_filename(file.filename)
    key = f"{destination}/{filename}" if destination else filename
    try:
        s3.upload_fileobj(file, R2_BUCKET, key)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/rename_file', methods=['POST'])
def rename_file():
    data = request.get_json()
    old_key = data.get('old_key')
    new_key = data.get('new_key')
    try:
        s3.copy_object(Bucket=R2_BUCKET, CopySource={'Bucket': R2_BUCKET, 'Key': old_key}, Key=new_key)
        s3.delete_object(Bucket=R2_BUCKET, Key=old_key)
        old_folder = '/'.join(old_key.split('/')[:-1])
        if old_folder:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=f"{old_folder}/")
            if 'Contents' not in response or not response['Contents']:
                try:
                    s3.delete_object(Bucket=R2_BUCKET, Key=f"{old_folder}/.placeholder")
                except:
                    pass
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.get_json()
    key = data.get('key')
    try:
        s3.delete_object(Bucket=R2_BUCKET, Key=key)
        folder = '/'.join(key.split('/')[:-1])
        if folder:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=f"{folder}/")
            if 'Contents' not in response or not response['Contents']:
                try:
                    s3.delete_object(Bucket=R2_BUCKET, Key=f"{folder}/.placeholder")
                except:
                    pass
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
