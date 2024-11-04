from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'tracker'
app.config['METADATA_FILE'] = 'metadata.json'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['METADATA_FILE']):
    with open(app.config['METADATA_FILE'], 'w') as f:
        json.dump({}, f)

def load_metadata():
    with open(app.config['METADATA_FILE'], 'r') as f:
        return json.load(f)

def save_metadata(metadata):
    with open(app.config['METADATA_FILE'], 'w') as f:
        json.dump(metadata, f)

@app.route('/')
def index():
    files = []
    metadata = load_metadata()
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        upload_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
        magnet_link = metadata.get(filename, {}).get('magnet_link', '')
        if filename[-2:] == 'py':
            continue
        files.append({'name': filename, 'upload_time': upload_time, 'magnet_link': magnet_link})
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'magnet_link' not in request.form:
        return redirect(request.url)
    file = request.files['file']
    magnet_link = request.form['magnet_link']
    if file and magnet_link:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        metadata = load_metadata()
        metadata[filename] = {'magnet_link': magnet_link}
        save_metadata(metadata)
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)