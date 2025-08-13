import os
import subprocess
from flask import Flask, request, redirect, send_from_directory

app = Flask(__name__)

AVATAR_DIR = os.path.join(os.path.dirname(__file__), 'avatars')
os.makedirs(AVATAR_DIR, exist_ok=True)

COOKIE_FILE = 'cookies.txt'
COOKIE_CONTENT = """# Netscape HTTP Cookie File

.instagram.com	TRUE	/	TRUE	1789062185	csrftoken	2053d62e31aa1c89d75cf4f5300022c0
.instagram.com	TRUE	/	TRUE	1787118016	datr	wOl1aMfDmY6zt8HtAyaeaibd
.instagram.com	TRUE	/	TRUE	1784094016	ig_did	BB71273F-1D11-4D30-AF50-FE1C50DBE6EE
.instagram.com	TRUE	/	TRUE	1754743831	wd	1549x739
.instagram.com	TRUE	/	TRUE	1787651229	mid	aH4MnAALAAFRZVkEINKxhkFSiDj1
.instagram.com	TRUE	/	TRUE	1785084253	ig_nrcb	1
.instagram.com	TRUE	/	TRUE	1785674903	sessionid	75960500904%3AUMBRcC2W2hClMz%3A26%3AAYclgNCdkQsuDof2ScDp7TWZ3ahRiErwS4fU3YgsOg
.instagram.com	TRUE	/	TRUE	1762278185	ds_user_id	75960500904
.instagram.com	TRUE	/	TRUE	0	rur	"CLN\\05475960500904\\0541786038186:01fea25a7f508bb38553049b45e143c87dbf6c8cd5d51e8056318983866f6edc8ee1c095"
.instagram.com	TRUE	/	TRUE	1788698985	ps_l	1
.instagram.com	TRUE	/	TRUE	1788698985	ps_n	1
"""

with open(COOKIE_FILE, 'w') as f:
    f.write(COOKIE_CONTENT)

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Avatar Fetcher</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 400px;
            margin: 50px auto;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }

        h1 {
            text-align: center;
            color: #333;
        }

        form {
            display: flex;
            flex-direction: column;
        }

        label {
            margin-bottom: 5px;
            color: #555;
        }

        input {
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        button {
            padding: 10px;
            background: #3897f0;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }

        button:hover {
            background: #287acc;
        }

        p {
            text-align: center;
            color: #777;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Instagram Profile Picture Fetcher</h1>
        <form action="/fetch" method="post">
            <label for="username">Instagram Username:</label>
            <input type="text" id="username" name="username" required>
            <button type="submit">Fetch</button>
        </form>
        <p>After fetching, the profile picture will be displayed here. You can right-click to download or open the link in a new tab.</p>
    </div>
</body>
</html>
"""

RESULT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Avatar - {username}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }}

        .container {{
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            text-align: center;
        }}

        h1 {{
            color: #333;
        }}

        img {{
            max-width: 100%;
            height: auto;
            border-radius: 50%;
            margin-bottom: 20px;
        }}

        a {{
            display: inline-block;
            padding: 10px 20px;
            background: #3897f0;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }}

        a:hover {{
            background: #287acc;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Profile Picture for @{username}</h1>
        <img src="{avatar_url}" alt="Profile Picture">
        <a href="{avatar_url}" target="_blank">Open in New Tab</a>
        <p><a href="/">Fetch Another</a></p>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_CONTENT

def download_avatar(username):
    avatar_filename = f'{username}.jpg'
    avatar_path = os.path.join(AVATAR_DIR, avatar_filename)

    if not os.path.exists(avatar_path):
        try:
            subprocess.check_call([
                'gallery-dl',
                f'https://www.instagram.com/{username}/avatar/',
                '--directory', AVATAR_DIR,
                '--filename', '{username}.{extension}',
                '--cookies', COOKIE_FILE
            ])
        except subprocess.CalledProcessError:
            return False

    return os.path.exists(avatar_path)

@app.route('/fetch', methods=['POST'])
def fetch():
    username = request.form['username'].strip().lower()
    if not username:
        return "Username is required", 400

    if download_avatar(username):
        avatar_url = f'/{username}/avatar'
        return RESULT_HTML_TEMPLATE.format(username=username, avatar_url=avatar_url)
    else:
        return "Error downloading avatar. User may not exist or rate limit reached.", 500

@app.route('/<username>/avatar')
def avatar(username):
    username = username.lower()
    avatar_filename = f'{username}.jpg'
    avatar_path = os.path.join(AVATAR_DIR, avatar_filename)

    if not os.path.exists(avatar_path):
        return "Avatar not found", 404

    return send_from_directory(AVATAR_DIR, avatar_filename)

if __name__ == '__main__':
    app.run(debug=True)
