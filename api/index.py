from flask import Flask, render_template_string, request, Response
import cv2
import numpy as np
import base64
import threading
import time

app = Flask(__name__)

latest_frame = None
lock = threading.Lock()

@app.route('/')
def index():
    return render_template_string('''
    <html>
    <head><title>Kamera Yayını</title></head>
    <body>
        <h2>Telefon Kameranı Aç</h2>
        <video id="video" autoplay playsinline width="300"></video>
        <br>
        <button onclick="startCamera('user')">Ön Kamera</button>
        <button onclick="startCamera('environment')">Arka Kamera</button>
        
        <script>
            let video = document.getElementById('video');
            let streamRef;

            async function startCamera(mode="user") {
                if (streamRef) {
                    streamRef.getTracks().forEach(t => t.stop());
                }
                try {
                    streamRef = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: { exact: mode } },
                        audio: false
                    });
                } catch (e) {
                    // bazı cihazlarda "exact" hata verir, fallback yap
                    streamRef = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: mode },
                        audio: false
                    });
                }
                video.srcObject = streamRef;

                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                setInterval(() => {
                    if(video.videoWidth === 0) return;
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    canvas.toBlob(blob => {
                        let reader = new FileReader();
                        reader.onloadend = () => {
                            fetch('/upload', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ image: reader.result })
                            }).catch(err => console.log(err));
                        }
                        reader.readAsDataURL(blob);
                    }, 'image/jpeg', 0.3); // kaliteyi düşürdük
                }, 100); // 100ms = daha akıcı
            }

            // varsayılan olarak arka kamera ile başlat
            startCamera('environment');
        </script>
    </body>
    </html>
    ''')

@app.route('/upload', methods=['POST'])
def upload():
    global latest_frame
    try:
        data = request.json['image']
        header, encoded = data.split(",", 1)
        img = base64.b64decode(encoded)
        npimg = np.frombuffer(img, dtype=np.uint8)
        frame = cv2.imdecode(npimg, 1)
        with lock:
            latest_frame = frame
    except Exception as e:
        print("Upload hata:", e)
    return "ok"

@app.route('/stream')
def stream():
    def generate():
        global latest_frame
        while True:
            frame = None
            with lock:
                if latest_frame is not None:
                    ret, jpeg = cv2.imencode('.jpg', latest_frame)
                    frame = jpeg.tobytes()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
