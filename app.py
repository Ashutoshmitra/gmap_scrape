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
import logging

CHROME_BINARY_LOCATION = os.getenv('CHROME_BINARY_LOCATION', '/usr/bin/chromium')
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def emit_progress(message):
    socketio.emit('progress', {'message': message})

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Add these additional options
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Set user agent to avoid detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    return webdriver.Chrome(options=options)

def get_lat_long_from_address(driver, address):
    try:
        driver.get(f"https://www.google.com/maps/place/{address}")
        
        # Increase wait time
        wait = WebDriverWait(driver, 10)
        
        # Wait for page load more explicitly
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        # Take screenshot for debugging if needed
        driver.save_screenshot(f"debug_{address.replace(' ', '_')}.png")
        
        # Try multiple selectors for the coordinates
        selectors = [
            "button.yra0jd.Hk4XGb",
            "div.mLuXec",
            "div[role='menuitem']"
        ]
        
        for selector in selectors:
            try:
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                if element.is_displayed():
                    return element.text
            except Exception as e:
                emit_progress(f"Selector {selector} failed: {str(e)}")
                continue
                
        raise Exception("Could not find coordinates with any selector")

    except Exception as e:
        emit_progress(f"Detailed error for {address}: {str(e)}")
        return None
    finally:
        # Clear cookies and cache after each request
        driver.delete_all_cookies()


def process_excel_file(filepath):
    df = pd.read_excel(filepath)
    try:
        driver = setup_driver()
        logger.info("Driver setup successful")
    except Exception as e:
        logger.error(f"Driver setup failed: {str(e)}")
        raise
    
    try:
        for index, row in df.iterrows():
            address = row.get("Full Address", None)
            if address:
                logger.info(f"Processing address: {address}")
                lat_long = get_lat_long_from_address(driver, address)
                logger.info(f"Retrieved coordinates: {lat_long}")
                df.at[index, 'Google Map Coordinates'] = lat_long
    finally:
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