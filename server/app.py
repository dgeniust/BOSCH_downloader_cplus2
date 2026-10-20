import os
import json
import time
import uuid
import threading
from flask import Flask, request, jsonify, render_template
from flasgger import Swagger
import atexit
app = Flask(__name__)

swagger = Swagger(app, template={
    "info": {
        "title": "URL Processor API",
        "Description": "API xử lý danh sách URL chạy ngầm và lưu vào file JSON.",
        "version": "1.0.0"
    }
})
NEW_FOLDER = './data/new'
os.makedirs(NEW_FOLDER,exist_ok=True)
HISTORY_FILE = './data/download_history.json'
HISTORY_LOCK = threading.Lock()
JOBS={}
JOB_EXPIRE_TIME = 3600

url_history_set = set()
history_dirty = False

def init_history():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if os.path.exists(HISTORY_FILE):
      try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
          data = json.load(f)
          url_history_set.update(data)
      except Exception as e:
         print(f"Lỗi đọc file history: {e}")
    else:
      with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
         json.dump([], f)

init_history()

def save_history():
   global history_dirty
   with HISTORY_LOCK:
      if history_dirty:
        temp_file = HISTORY_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
           json.dump(list(url_history_set), f, indent=4)
        os.replace(temp_file, HISTORY_FILE)
        history_dirty = False

def background_maintenance():
  while True:
    time.sleep(60)
    save_history()

    current_time = time.time()
    expired_jobs = [
      j_id for j_id, j_info in list(JOBS.items())
      if current_time - j_info.get('create_at', current_time) > JOB_EXPIRE_TIME
    ]
    for j_id in expired_jobs:
       JOBS.pop(j_id, None)

threading.Thread(target=background_maintenance, daemon=True).start()

atexit.register(save_history)

def process_urls_background(job_id, url_list):
  JOBS[job_id]['status'] = 'Processing'
  saved_count = 0

  for url in url_list:
     clean_url = url.strip()
     if not clean_url:
        continue

  epoch_ms = int(time.time() * 1000)
  short_uuid = uuid.uuid4().hex[:8]
  item_id = f"{epoch_ms}-{short_uuid}"

  job_data = {
     "id": item_id,
     "url": clean_url,
     "created_ms": epoch_ms
  }
  tmp_file_path = os.path.join(NEW_FOLDER, f"{item_id}.tmp")
  final_file_path = os.path.join(NEW_FOLDER, f"{item_id}.json")

  with open(tmp_file_path, 'w', encoding='utf-8') as f:
    json.dump(job_data, f, indent=4, ensure_ascii=False)

  os.rename(tmp_file_path, final_file_path)
  saved_count += 1

  JOBS[job_id]['status'] = 'Completed'
  JOBS[job_id]['result'] = {
        "saved_to_json": saved_count
  }
  
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/process-list', methods=['POST'])
def process_list():
    """
    Nhận danh sách URL và xử lý ngầm
    ---
    tags:
      - Jobs
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Danh sách URL cần xử lý
        schema:
          type: object
          required:
            - urls
          properties:
            urls:
              type: array
              items:
                type: string
              example: ["https://google.com", "https://github.com"]
    responses:
      202:
        description: Job được tạo thành công và đang chạy ngầm
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            job_id:
              type: string
              example: "123e4567-e89b-12d3-a456-426614174000"
            message:
              type: string
              example: "Saving to JSON file"
      400:
        description: Lỗi do danh sách URL trống
    """
    data = request.get_json()
    url_list = data.get('urls', [])
    
    if not url_list:
        return jsonify({"success": False, "error": "Danh sách URL trống"}), 400

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'status': 'Pending',
        'total_urls': len(url_list),
        'created_at': time.time()
    }
    threading.Thread(target=process_urls_background, args=(job_id, url_list)).start()

    return jsonify({
        "success": True, 
        "job_id": job_id,
        "message": f"Đã nhận {len(url_list)} link mới.",
        "added_count": len(url_list)
    }), 202

@app.route('/api/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Lấy trạng thái và kết quả của Job
    ---
    tags:
      - Jobs
    produces:
      - application/json
    parameters:
      - in: path
        name: job_id
        required: true
        type: string
        description: ID của Job được trả về từ API /api/process-list
    responses:
      200:
        description: Thông tin trạng thái Job
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            job_id:
              type: string
            status:
              type: string
              example: "Completed"
            details:
              type: object
      404:
        description: Không tìm thấy Job ID
    """
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"success": False, "error": "Không tìm thấy Job ID"}), 404

    return jsonify({
        "success": True,
        "job_id": job_id,
        "status": job['status'],
        "details": job.get('result',{})
    })


if __name__ == '__main__':
    app.run(debug=True)