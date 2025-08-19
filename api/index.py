from flask import Flask, request, render_template_string
import boto3
from urllib.parse import unquote

# R2 erişim bilgileri
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

# --- HTML Template ---
HTML = """<!DOCTYPE html>
<html lang="tr" data-bs-theme="light">
<head>
  <meta charset="UTF-8" />
  <title>R2 Dosya Yöneticisi</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    body { background: #f7f7fb; }
    .container-narrow { max-width: 1100px; }
    .folder-card { transition: transform .15s ease, box-shadow .15s ease; }
    .folder-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    .file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
    .file-card { border: 1px solid rgba(0,0,0,.06); border-radius: 16px; background: #fff; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.04); transition: transform .15s ease, box-shadow .15s ease; }
    .file-card:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(0,0,0,.08); }
    .thumb-wrap { width: 100%; aspect-ratio: 16/10; background: #f0f2f5; display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .thumb-wrap img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .file-meta { font-size: .9rem; color: #6b7280; }
    .badge-size { background: #eef2ff; color: #3730a3; }
    .file-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 600; }
    .thumb-icon { font-size: 2.25rem; color: #94a3b8; }
    .crumb a { text-decoration: none; }
    .btn-wrap { display:flex; gap:.5rem; flex-wrap:wrap; }
  </style>
</head>
<body>
  <div class="container container-narrow py-4">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-cloud-fill fs-3 text-primary"></i>
        <h1 class="h3 mb-0">Cloudflare R2 Dosya Yöneticisi</h1>
      </div>
      {% if current_folder %}
        <a href="{{ url_for('home') }}" class="btn btn-outline-secondary">
          <i class="bi bi-house"></i> Ana Dizin
        </a>
      {% endif %}
    </div>

    {% if breadcrumb and breadcrumb|length %}
      <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
          <li class="breadcrumb-item"><a href="{{ url_for('home') }}">Ana Dizin</a></li>
          {% for name, path in breadcrumb %}
            {% if loop.last %}
              <li class="breadcrumb-item active" aria-current="page">{{ name }}</li>
            {% else %}
              <li class="breadcrumb-item"><a href="{{ url_for('browse_folder', folder=path)|safe }}">{{ name }}</a></li>
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
          <a href="{{ url_for('browse_folder', folder=(current_folder ~ '/' if current_folder else '') ~ folder)|safe }}" class="text-reset text-decoration-none">
            <div class="p-3 bg-white border rounded-4 folder-card d-flex align-items-center gap-3">
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
              <img src="{{ file.url }}" alt="{{ file.name }}" loading="lazy"
                   onclick="openPreview('{{ loop.index0 }}')" style="cursor: zoom-in;">
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
                <a class="btn btn-sm btn-outline-primary" href="{{ file.url }}" target="_blank" rel="noopener">Aç</a>
                {% if file.is_image %}
                  <button class="btn btn-sm btn-primary" onclick="openPreview('{{ loop.index0 }}')">Önizle</button>
                {% endif %}
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

  <!-- Image Preview Modal -->
  <div class="modal fade" id="imgPreviewModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-xl">
      <div class="modal-content rounded-4 overflow-hidden">
        <div class="modal-header">
          <h5 class="modal-title" id="previewTitle">Önizleme</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Kapat"></button>
        </div>
        <div class="modal-body p-0">
          <div class="w-100" style="background:#0b0b0b;">
            <img id="previewImg" src="" alt="" style="width:100%;height:auto;display:block;max-height:80vh;object-fit:contain;">
          </div>
        </div>
        <div class="modal-footer">
          <a id="previewOpen" href="#" class="btn btn-outline-primary" target="_blank" rel="noopener">Yeni Sekmede Aç</a>
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Kapat</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const files = {{ files|tojson }};
    const modalEl = document.getElementById('imgPreviewModal');
    const previewImg = document.getElementById('previewImg');
    const previewTitle = document.getElementById('previewTitle');
    const previewOpen = document.getElementById('previewOpen');
    let bsModal;

    document.addEventListener('DOMContentLoaded', function() {
      bsModal = new bootstrap.Modal(modalEl);
    });

    function openPreview(idx) {
      const f = files[Number(idx)];
      if (!f || !f.is_image) return;
      previewImg.src = f.url;
      previewTitle.textContent = f.name;
      previewOpen.href = f.url;
      bsModal.show();
    }
  </script>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

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
    folder = unquote(folder)  # <<== Unicode decode
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
            if key == prefix: continue
            file_name = key[len(prefix):]
            if '/' in file_name: continue

            url = s3.generate_presigned_url('get_object', Params={'Bucket': R2_BUCKET, 'Key': key}, ExpiresIn=3600)
            ext = get_ext(file_name)
            is_image = ext in IMAGE_EXTS
            icon = DOC_ICON_MAP.get(ext, 'bi-file-earmark')

            files.append({
                'name': file_name,
                'key': key,
                'url': url,
                'size_h': human_size(obj['Size']),
                'is_image': is_image,
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

if __name__ == '__main__':
    app.run(debug=True)
