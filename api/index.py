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

# R2 istemcisi
s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name='auto'
)

# HTML template
HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>R2 Dosya Yükleme ve Listeleme</title>
</head>
<body>
  <h2>Dosya Yükle (R2)</h2>
  <form method="POST" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="submit" value="Yükle">
  </form>

  {% if file_url %}
    <h3>Yüklenen Dosya:</h3>
    <a href="{{ file_url }}" target="_blank">{{ file_url }}</a><br><br>
    <img src="{{ file_url }}" alt="Yüklenen Görsel" style="max-width: 400px;">
  {% endif %}

  <h2>Bucket İçeriği:</h2>
  {% if contents %}
    <ul>
      {% for item in contents %}
        <li>
          <a href="{{ item.url }}" target="_blank">{{ item.key }}</a>
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>Bucket boş.</p>
  {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    file_url = None

    # Yükleme
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            filename = file.filename
            s3.upload_fileobj(file, R2_BUCKET, filename)
            file_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{filename}"

    # Listeleme
    response = s3.list_objects_v2(Bucket=R2_BUCKET)
    contents = []
    for obj in response.get('Contents', []):
        key = obj['Key']
        url = f"{R2_ENDPOINT}/{R2_BUCKET}/{key}"
        contents.append({'key': key, 'url': url})

    return render_template_string(HTML, file_url=file_url, contents=contents)

if __name__ == '__main__':
    app.run(debug=True)
