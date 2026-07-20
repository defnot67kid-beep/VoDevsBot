from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import io
from PIL import Image, ImageDraw
import random

app = Flask(__name__)

CONFIG_FILE = "rank_configs.json"

# Load user configurations
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        configs = json.load(f)
else:
    configs = {}

@app.route('/')
def home():
    return "✅ Rank Card Dashboard is online!"

@app.route('/dashboard/<user_id>')
def dashboard(user_id):
    user_config = configs.get(user_id, {})
    return render_template('dashboard.html', user_id=user_id, config=user_config)

@app.route('/save_config/<user_id>', methods=['POST'])
def save_config(user_id):
    data = request.json
    configs[user_id] = data
    with open(CONFIG_FILE, 'w') as f:
        json.dump(configs, f, indent=4)
    return jsonify({"status": "saved"})

@app.route('/get_card/<user_id>')
def get_card(user_id):
    # Generate the rank card image
    config = configs.get(user_id, {
        "bg_color": "#2f3136",
        "bar_color": "#5865F2",
        "opacity": 100,
        "font_color": "#ffffff"
    })

    # Create a blank image (800 x 200 pixels)
    img = Image.new('RGB', (800, 200), color=config.get('bg_color', '#2f3136'))
    draw = ImageDraw.Draw(img)

    # Draw a progress bar (Mock: 50% progress)
    draw.rectangle([20, 150, 780, 180], fill="#ffffff")
    draw.rectangle([20, 150, 400, 180], fill=config.get('bar_color', '#5865F2'))

    # Return the image
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
