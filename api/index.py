from flask import Flask, request, render_template_string, jsonify, redirect, url_for
import subprocess
import json
import base64
import requests
import tempfile
import os

app = Flask(__name__)

# Cookies içeriğini doğrudan koda gömüyoruz
COOKIES_CONTENT = """\
.instagram.com	TRUE	/	TRUE	1789642815	csrftoken	1FXuJev8Ddd5jExWa-GiuT
.instagram.com	TRUE	/	TRUE	1789578029	datr	LHObaEi5RirKmPcuuCNKYhgK
.instagram.com	TRUE	/	TRUE	1786554165	ig_did	1BB2A60D-0329-4D40-BE8E-6C0B84A6CB03
.instagram.com	TRUE	/	TRUE	1755687611	wd	1549x739
.instagram.com	TRUE	/	TRUE	1789578030	mid	aJtzLAALAAH8M0ZZrDqepfdJfeyd
.instagram.com	TRUE	/	TRUE	1786554039	ig_nrcb	1
.instagram.com	TRUE	/	TRUE	1786618793	sessionid	75960500904%3A3YweVf7NJu2Pyl%3A7%3AAYcZ1UQYyvPH1WXdZtYWeyalj4UWwC3crxYvs0wJ8Q
.instagram.com	TRUE	/	TRUE	1762858815	ds_user_id	75960500904
.instagram.com	TRUE	/	TRUE	1789642794	ps_l	1
.instagram.com	TRUE	/	TRUE	1789642794	ps_n	1
.instagram.com	TRUE	/	TRUE	0	rur	"CLN\05475960500904\0541786618817:01fefe6514d2fc4d8043d9c73a456efeb116896afe572cf37c7a7358b9e893f35742271e"
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Bilgileri</title>
      <link rel="shortcut icon" href="data:image/jpeg;base64,{{ data.image_base64 }}" type="image/x-icon">

    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        img { max-width: 200px; display: block; margin-bottom: 5px; }
        .container { max-width: 500px; margin: auto; }
        .img-link { font-size: 14px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Instagram Kullanıcı Bilgileri</h2>
        <form method="GET">
            <input type="text" name="username" value="{{ username }}" placeholder="Kullanıcı adı">
            <button type="submit">Getir</button>
        </form>
        {% if error %}
            <p style="color:red;">{{ error }}</p>
        {% elif data %}
            <h3>@{{ data.username }}</h3>
            <img src="data:image/jpeg;base64,{{ data.image_base64 }}" alt="Profil Fotoğrafı">
            <p class="img-link"><a href="{{ data.display_url }}" target="_blank">link</a></p>
            <p><b>Biyografi:</b> {{ data.biography }}</p>
            <p><b>Takipçi:</b> {{ data.followers }}</p>
            <p><b>Takip:</b> {{ data.following }}</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    username = request.args.get("username")
    output_format = request.args.get("format", "html").lower()

    # Eğer username yoksa otomatik olarak varsayılan kullanıcıya yönlendir
    if not username:
        return redirect(url_for('index', username="emineey41"))

    data = None
    error = None

    try:
        # Geçici cookies.txt oluştur
        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as tmp_cookie:
            tmp_cookie.write(COOKIES_CONTENT)
            tmp_cookie_path = tmp_cookie.name

        # gallery-dl komutunu çalıştır
        cmd = [
            "gallery-dl",
            "--cookies", tmp_cookie_path,
            "--dump-json",
            f"https://www.instagram.com/{username}/avatar"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        # Geçici dosyayı sil
        os.remove(tmp_cookie_path)

        if result.returncode != 0:
            error = f"gallery-dl hatası: {result.stderr}"
        else:
            try:
                json_data = json.loads(result.stdout)
                user_info = json_data[0][1]["user"]
                display_url = json_data[1][2].get("display_url")

                image_base64 = ""
                try:
                    img_resp = requests.get(display_url, timeout=10)
                    img_resp.raise_for_status()
                    image_base64 = base64.b64encode(img_resp.content).decode("utf-8")
                except Exception as e:
                    error = f"Resim indirilemedi: {e}"

                data = {
                    "username": user_info["username"],
                    "biography": user_info.get("biography", ""),
                    "display_url": display_url,
                    "image_base64": image_base64,
                    "followers": user_info.get("count_follow", 0),
                    "following": user_info.get("count_followed", 0)
                }
            except Exception as e:
                error = f"JSON parse hatası: {e}"

    except Exception as e:
        error = str(e)

    if output_format == "json":
        if error:
            return jsonify({"error": error}), 400
        return jsonify(data)

    return render_template_string(HTML_TEMPLATE, username=username, data=data, error=error)

if __name__ == "__main__":
    app.run(debug=True)
