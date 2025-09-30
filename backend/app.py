import os
import uuid
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from yt_dlp import YoutubeDL
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# CORS configurado (aunque Nginx lo maneja)
CORS(app, resources={r"/*": {"origins": "*"}})

# Define the base directory for temporary audio files
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_audio')
os.makedirs(TEMP_DIR, exist_ok=True)

@app.route('/api/convert', methods=['POST'])
def convert_video():
    """
    Converts a YouTube video URL to MP3 (medium quality only).
    """
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    request_id = str(uuid.uuid4())
    output_dir = os.path.join(TEMP_DIR, request_id)
    os.makedirs(output_dir)

    try:
        app.logger.info(f"Starting conversion for URL: {url} with request_id: {request_id}")

        # --- Download Audio using yt-dlp ---
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'best',
            }],
            'quiet': True,
            # Opciones para evitar detección de bot
            'nocheckcertificate': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_files = os.listdir(output_dir)
            if not downloaded_files:
                raise Exception("Failed to download audio from URL.")

            original_audio_path = os.path.join(output_dir, downloaded_files[0])
            base_filename = os.path.splitext(downloaded_files[0])[0]
            app.logger.info(f"Successfully downloaded: {original_audio_path}")

        # --- Convert to MP3 (Medium Quality Only) ---
        app.logger.info("Loading audio file for conversion.")
        audio = AudioSegment.from_file(original_audio_path)
        app.logger.info("Audio file loaded. Starting MP3 export.")

        # Solo calidad media (128k)
        filename = f"{base_filename}_medium.mp3"
        mp3_path = os.path.join(output_dir, filename)
        
        app.logger.info(f"Exporting medium quality to {filename} at 128k...")
        audio.export(mp3_path, format="mp3", bitrate="128k")
        app.logger.info("Export completed successfully.")

        # --- Cleanup original file ---
        os.remove(original_audio_path)
        app.logger.info(f"Removed original audio file: {original_audio_path}")

        return jsonify({
            'message': 'Conversion successful!',
            'download': {
                'url': f'/api/download/{request_id}/{filename}',
                'filename': filename
            },
            'video_title': info_dict.get('title', 'Unknown Title')
        })

    except Exception as e:
        app.logger.error(f"An error occurred during conversion for request_id {request_id}: {e}", exc_info=True)
        # Clean up failed request directory
        if os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                os.remove(os.path.join(output_dir, f))
            os.rmdir(output_dir)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/download/<request_id>/<filename>')
def download_file(request_id, filename):
    """
    Serves a converted MP3 file for download.
    """
    safe_request_id = os.path.basename(request_id)
    safe_filename = os.path.basename(filename)

    directory = os.path.join(TEMP_DIR, safe_request_id)

    # Security check
    if not os.path.abspath(directory).startswith(os.path.abspath(TEMP_DIR)):
        return jsonify({'error': 'Invalid request ID'}), 400

    app.logger.info(f"Download request for: {safe_filename} from request_id: {safe_request_id}")
    return send_from_directory(directory, safe_filename, as_attachment=True)

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'backend'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)