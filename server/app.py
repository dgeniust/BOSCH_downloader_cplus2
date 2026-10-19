import os
import json
import time
import uuid
import threading
from flask import Flask, request, jsonify, render_template
from flasgger import Swagger
from bloomfilter import URLBloomFilter
app = Flask(__name__)

swagger = Swagger(app, template={
    "info": {
        "title": "URL Processor API",
        "Description": "API xử lý danh sách URL chạy ngầm và lưu vào file JSON.",
        "version": "1.0.0"
    }
})
NEW_FOLDER = 'new'
os.makedirs(NEW_FOLDER,exist_ok=True)
BLOOM_FILE = 'bloom_filter.json'
HISTORY_FILE = './data/download_history.json'
HISTORY_LOCK = threading.Lock()
# DATA_FILE = os.path.join(NEW_FOLDER,'url_data.json')
JOBS={}
FILE_LOCK = threading.Lock()

def init_history():
    """Tạo file JSON history nếu chưa tồn tại"""
    if not os.path.exists(HISTORY_FILE):
      with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

bloom_filter = URLBloomFilter()
init_history()

# def process_urls_background(job_id, url_list):
#     """Tiến trình ngầm: Check trùng lặp với lịch sử và tạo file uuid.json"""
#     JOBS[job_id]['status'] = 'Processing'
#     new_urls=[]
#     with HISTORY_LOCK:
#       try:
#         with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
#           history_data = json.load(f)
#       except (json.JSONDecodeError, FileNotFoundError):
#           history_data = []

#       history_set = set(history_data)
#       for url in url_list: 
#         if url not in history_set:
#           new_urls.append(url)
#           history_set.add(url)
#           history_data.append(url)

#       if new_urls:
#          with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
#             json.dump(history_data, f, indent=4, ensure_ascii=False)

#     if new_urls:
#        job_file_path = os.path.join(NEW_FOLDER, f"{job_id}.json")
#        with open (job_file_path, 'w', encoding='utf-8') as f:
#           json.dump({"urls": new_urls}, f, indent=4, ensure_ascii=False)
    
#     JOBS[job_id]['status'] = 'Completed'
#     JOBS[job_id]['result'] = {
#         "received": len(url_list),
#         "saved_to_json": len(new_urls),
#         "saved_file": f"{job_id}.json" if new_urls else None
#     } 

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
    data = request.get_json()
    url_list = data.get('urls', [])
    
    if not url_list:
        return jsonify({"success": False, "error": "Danh sách URL trống"}), 400

    new_urls = []
    for url in url_list:
      clean_url = url.strip().rstrip('/')
      if clean_url and (clean_url not in bloom_filter):
          new_urls.append(clean_url)
          bloom_filter.add(clean_url)
    if new_urls:
      bloom_filter.save_to_file()
    else:
      return jsonify({
          "success": True,
          "message": "Tất cả các URL gửi lên đều đã tồn tại trong hệ thống, không có file mới được tạo.",
          "added_count": 0
      }), 200 
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'status': 'Pending',
        'total_urls': len(url_list)
    }
    thread = threading.Thread(target=process_urls_background, args=(job_id, url_list))
    thread.start()
    
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

@app.route('/api/benchmark', methods=['POST'])
def benchmark():
  """
    So sánh hiệu năng giữa phương pháp truyền thống và Bloom Filter
    ---
    tags:
      - Benchmark
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Danh sách URL dùng để chạy thử nghiệm benchmark
        schema:
          type: object
          required:
            - urls
          properties:
            urls:
              type: array
              items:
                type: string
              example: ["https://google.com", "https://github.com", "https://facebook.com"]
    responses:
      200:
        description: Kết quả đo đạc hiệu năng minh bạch giữa 2 phương pháp
        schema:
          type: object
          properties:
            input_urls_count:
              type: integer
              example: 3
            traditional_method:
              type: object
              properties:
                time_taken_ms:
                  type: number
                  example: 12.45
                new_urls_found:
                  type: integer
                  example: 3
                file_size_bytes:
                  type: integer
                  example: 1540
                file_size_formatted:
                  type: string
                  example: "1.50 KB"
            bloom_filter_method:
              type: object
              properties:
                time_taken_ms:
                  type: number
                  example: 0.85
                new_urls_found:
                  type: integer
                  example: 3
                file_size_bytes:
                  type: integer
                  example: 1798120
                file_size_formatted:
                  type: string
                  example: "1755.98 KB"
            speedup_factor:
              type: string
              example: "14.65x nhanh hơn"
      400:
        description: Lỗi do danh sách URL trống hoặc thiếu thông tin truyền vào
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Vui lòng cung cấp danh sách 'urls' trong body"
  """
  """
  Chạy song song 2 phương pháp trên cùng 1 mảng URL đầu vào để đo đạc chỉ số minh bạch
  """
  data = request.get_json()
  url_list = data.get('urls', [])
  if not url_list:
      return jsonify({"error": "Vui lòng cung cấp danh sách 'urls' trong body"}), 400

  # --- ĐO CÁCH TRUYỀN THỐNG (download_history.json) ---
  start_trad = time.perf_counter()
  with HISTORY_LOCK:
      try:
          with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
              history_data = json.load(f)
      except Exception:
          history_data = []

      history_set = set(history_data)
      trad_new_urls = []
      for url in url_list:
          if url not in history_set:
              trad_new_urls.append(url)
              history_set.add(url)
              history_data.append(url)

      with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
          json.dump(history_data, f, indent=4, ensure_ascii=False)
          
  time_trad_ms = round((time.perf_counter() - start_trad) * 1000, 3)

  # --- ĐO CÁCH BLOOM FILTER (bloom_filter.json) ---
  start_bloom = time.perf_counter()
  bloom_new_urls = []
  for url in url_list:
      if url not in bloom_filter:
          bloom_new_urls.append(url)
          bloom_filter.add(url)
          
  bloom_filter.save_to_file()
  time_bloom_ms = round((time.perf_counter() - start_bloom) * 1000, 3)

  # --- ĐO DUNG LƯỢNG FILE LƯU TRỮ ---
  history_size = os.path.getsize(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else 0
  bloom_size = os.path.getsize(BLOOM_FILE) if os.path.exists(BLOOM_FILE) else 0

  return jsonify({
      "input_urls_count": len(url_list),
      "traditional_method": {
          "time_taken_ms": time_trad_ms,
          "new_urls_found": len(trad_new_urls),
          "file_size_bytes": history_size,
          "file_size_formatted": f"{history_size / 1024:.2f} KB"
      },
      "bloom_filter_method": {
          "time_taken_ms": time_bloom_ms,
          "new_urls_found": len(bloom_new_urls),
          "file_size_bytes": bloom_size,
          "file_size_formatted": f"{bloom_size / 1024:.2f} KB"
      },
      "speedup_factor": f"{round(time_trad_ms / max(time_bloom_ms, 0.001), 2)}x nhanh hơn"
  })

if __name__ == '__main__':
    app.run(debug=True)