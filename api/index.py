from flask import Flask, request, render_template_string
import boto3

# R2 erişim bilgilerin
AWS_ACCESS_KEY_ID = '112b183cdd116461df8ee2d8a647a58c'
AWS_SECRET_ACCESS_KEY = 'dd104010783bf0278926182bb9a1d0496c6f62907241d5f196918d7089fe005d'
R2_BUCKET = 'walter'
ACCOUNT_ID = '238a54d3f39bc03c25b5550bbd2683ed'

# R2 endpoint URL'si (Cloudflare'dan al)
R2_ENDPOINT = f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com'
app = Flask(__name__)

s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name='auto'
)

HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <title>R2 Dosya Yöneticisi</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container py-4">
    <h1 class="mb-4">Cloudflare R2 Dosya Yöneticisi</h1>

    {% if current_folder %}
      <a href="{{ url_for('home') }}" class="btn btn-secondary mb-3">&larr; Ana Dizin</a>
      <h3>Klasör: {{ current_folder }}</h3>
    {% endif %}

    {% if folders %}
      <h4>Klasörler</h4>
      <div class="list-group mb-4">
      {% for folder in folders %}
        <a href="{{ url_for('browse_folder', folder=folder) }}" class="list-group-item list-group-item-action">
          📁 {{ folder }}
        </a>
      {% endfor %}
      </div>
    {% endif %}

    {% if files %}
      <h4>Dosyalar</h4>
      <ul class="list-group">
      {% for file in files %}
        <li class="list-group-item d-flex justify-content-between align-items-center">
          <a href="{{ file.url }}" target="_blank">{{ file.name }}</a>
          <span class="badge bg-primary rounded-pill">{{ file.size_kb }} KB</span>
        </li>
      {% endfor %}
      </ul>
    {% endif %}
  </div>
</body>
</html>
"""

def get_size_kb(size_bytes):
    return f"{size_bytes // 1024}" if size_bytes > 1024 else f"{size_bytes} B"

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
        # Alt klasörler
        for common_prefix in page.get('CommonPrefixes', []):
            folder_name = common_prefix['Prefix'][len(prefix):].rstrip('/')
            folders.append(folder_name)

        # Dosyalar
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key == prefix:
                continue  # klasör ismi dosya olarak gelmiş olabilir, atla
            file_name = key[len(prefix):]
            if '/' in file_name:
                continue  # alt alt klasör dosyası, göz ardı et
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': R2_BUCKET, 'Key': key},
                ExpiresIn=3600
            )
            size_kb = get_size_kb(obj['Size'])
            files.append({'name': file_name, 'url': url, 'size_kb': size_kb})

    folders.sort()
    files.sort(key=lambda x: x['name'].lower())

    return render_template_string(HTML,
                                  folders=folders,
                                  files=files,
                                  current_folder=current_folder)

if __name__ == '__main__':
    app.run(debug=True)
