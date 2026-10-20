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
      j_id for j_id, j_info in JOBS.items()
      if current_time - j_info.get('create_at', current_time) > JOB_EXPIRE_TIME
    ]
    for j_id in expired_jobs:
       JOBS.pop(j_id, None)

threading.Thread(target=background_maintenance, daemon=True).start()

atexit.register(save_history)

def process_urls_background(job_id, url_list):
  JOBS[job_id]['status'] = 'Processing'
  
  if url_list:
      job_file_path = os.path.join(NEW_FOLDER, f"{job_id}.json")
      with open(job_file_path, 'w', encoding='utf-8') as f:
          json.dump({"urls": url_list}, f, indent=4, ensure_ascii=False)

  JOBS[job_id]['status'] = 'Completed'
  JOBS[job_id]['result'] = {
      "saved_to_json": len(url_list),
      "saved_file": f"{job_id}.json" if url_list else None
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
    global history_dirty
    data = request.get_json()
    url_list = data.get('urls', [])
    
    if not url_list:
        return jsonify({"success": False, "error": "Danh sách URL trống"}), 400

    new_urls = []
    with HISTORY_LOCK:
      for url in url_list:
        clean_url = url.strip().rstrip('/')
        if clean_url and (clean_url not in url_history_set):
            new_urls.append(clean_url)
            url_history_set.add(clean_url)
      if new_urls:
        history_dirty = True

    if not new_urls:
      return jsonify({
          "success": True,
          "message": "Tất cả các URL gửi lên đều đã tồn tại trong hệ thống, không có file mới được tạo.",
          "added_count": 0
      }), 200 
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'status': 'Pending',
        'total_urls': len(url_list),
        'created_at': time.time()
    }
    threading.Thread(target=process_urls_background, args=(job_id, new_urls)).start()
    
    return jsonify({
        "success": True, 
        "job_id": job_id,
        "message": f"Đã nhận {len(new_urls)} link mới.",
        "added_count": len(new_urls)
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