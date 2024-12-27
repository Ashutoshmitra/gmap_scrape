from flask import Flask, request, jsonify, send_file, render_template
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from io import BytesIO

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def emit_progress(message):
    socketio.emit('progress', {'message': message})

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")  # Required in container environments
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited /dev/shm space
    options.add_argument("--disable-gpu")  # Disable GPU rendering (headless mode doesn't use it)
    options.add_argument("--remote-debugging-port=9222")  # Debugging port for Chrome
    driver = webdriver.Chrome(options=options)
    return driver

def get_lat_long_from_address(driver, address):
    try:
        driver.get(f"https://www.google.com/maps/place/{address}")
        wait = WebDriverWait(driver, 3)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")))
        
        try:
            close_button = driver.find_element(By.CSS_SELECTOR, "button.yra0jd.Hk4XGb")
            close_button.click()
            time.sleep(2)
        except Exception as e:
            emit_progress(f"Could not close side panel: {e}")

        map_canvas = driver.find_element(By.CSS_SELECTOR, "canvas")
        action = ActionChains(driver)
        action.context_click(map_canvas).perform()
        time.sleep(1)

        lat_long_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mLuXec")))
        return lat_long_element.text

    except Exception as e:
        emit_progress(f"Error retrieving coordinates: {e}")
        return None

def process_excel_file(filepath):
    df = pd.read_excel(filepath)
    driver = setup_driver()
    
    for index, row in df.iterrows():
        address = row.get("Full Address", None)
        if address:
            emit_progress(f"Processing address: {address}")
            lat_long = get_lat_long_from_address(driver, address)
            df.at[index, 'Google Map Coordinates'] = lat_long

    driver.quit()
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': 'Invalid file format. Please upload an Excel file.'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        processed_df = process_excel_file(filepath)
        
        # Save to BytesIO object
        output = BytesIO()
        processed_df.to_excel(output, index=False)
        output.seek(0)
        
        os.remove(filepath)  # Clean up uploaded file
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='processed_addresses.xlsx'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True)