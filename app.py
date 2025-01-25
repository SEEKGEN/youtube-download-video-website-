import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import tempfile
import shutil
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

FFMPEG_PATHS = {
    'windows': r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
    'linux': '/usr/bin/ffmpeg',
    'darwin': '/usr/local/bin/ffmpeg'
}

DOWNLOAD_FOLDER = tempfile.mkdtemp(prefix='ytdl_')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize_filename(filename):
    """Remove invalid characters from filenames"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def get_ffmpeg_path():
    """Check system for FFmpeg executable"""
    for path in FFMPEG_PATHS.values():
        if os.path.exists(path):
            return path
    return None

@app.route('/api/fetch-formats', methods=['GET'])
def fetch_formats():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'simulate': True,
            'ignoreerrors': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                return jsonify({'error': 'Playlists are not supported'}), 400

            formats = info.get('formats', [])
            ffmpeg_available = get_ffmpeg_path() is not None
            
            valid_formats = []
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    valid_formats.append({
                        'format_id': fmt['format_id'],
                        'resolution': f"{fmt.get('width', 0)}x{fmt.get('height', 0)}",
                        'ext': fmt.get('ext', 'mp4'),
                        'requires_ffmpeg': False
                    })
                elif ffmpeg_available:
                    valid_formats.append({
                        'format_id': fmt['format_id'],
                        'resolution': f"{fmt.get('width', 0)}x{fmt.get('height', 0)}",
                        'ext': fmt.get('ext', 'mp4'),
                        'requires_ffmpeg': True
                    })

            seen = set()
            unique_formats = []
            for fmt in valid_formats:
                key = (fmt['resolution'], fmt['ext'])
                if key not in seen:
                    seen.add(key)
                    unique_formats.append(fmt)

            return jsonify({
                'formats': unique_formats,
                'ffmpeg_available': ffmpeg_available
            })

    except Exception as e:
        logging.error(f"Format fetch error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_file():
    data = request.get_json()
    url = data.get('url')
    format_id = data.get('format_id')

    if not url or not format_id:
        return jsonify({'error': 'URL and format_id are required'}), 400

    try:
        ffmpeg_path = get_ffmpeg_path()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"video_{timestamp}"
        out_template = os.path.join(DOWNLOAD_FOLDER, f"{base_filename}.%(ext)s")

        ydl_opts = {
            'format': format_id,
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'ffmpeg_location': ffmpeg_path,
            'ignoreerrors': True,
            'windowsfilenames': True,
            'restrictfilenames': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if not info:
                raise ValueError("Failed to process download")

            # Get actual downloaded filename
            actual_filename = ydl.prepare_filename(info)
            if not os.path.exists(actual_filename):
                raise FileNotFoundError(f"Downloaded file not found at {actual_filename}")

            # Sanitize filename for download
            clean_filename = sanitize_filename(os.path.basename(actual_filename))
            final_path = os.path.join(DOWNLOAD_FOLDER, clean_filename)
            os.rename(actual_filename, final_path)

        return send_file(
            final_path,
            as_attachment=True,
            download_name=clean_filename,
            mimetype='video/mp4'
        )

    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        error_msg = str(e)
        if 'ffmpeg' in error_msg.lower():
            error_msg += ". Please install FFmpeg and add it to your PATH."
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)