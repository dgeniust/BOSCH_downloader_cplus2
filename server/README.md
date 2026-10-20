# 🛠️ Hướng Dẫn Cài Đặt Môi Trường & Thư Viện Dự Án

Tài liệu này hướng dẫn các bước chi tiết để khởi tạo môi trường ảo Python, cài đặt các thư viện phụ thuộc từ `requirements.txt` và khởi chạy ứng dụng Flask trên server.

---

## 📋 1. Yêu Cầu Hệ Thống

Trước khi bắt đầu, hãy đảm bảo hệ thống của bạn đã cài đặt:
- **Python 3.10+**
- **pip** (trình quản lý gói của Python)
- **git**

---

## 🚀 2. Các Bước Cài Đặt Ban Đầu

### Bước 2.1: Clone dự án và truy cập thư mục
```bash
git clone <URL_REPOSITORY_CỦA_BẠN>
cd server
```

---

### Bước 2.2: Tạo môi trường ảo (Virtual Environment)
Tạo môi trường ảo cách ly với tên `downloader-py`:

- **Trên Linux / Ubuntu / macOS:**
  ```bash
  python3 -m venv downloader-py
  ```

- **Trên Windows:**
  ```cmd
  python -m venv downloader-py
  ```

*(Lưu ý: Nếu hệ thống Ubuntu báo thiếu gói `venv`, hãy chạy `sudo apt install python3-venv` để bổ sung).*

---

### Bước 2.3: Kích hoạt môi trường ảo (Activate)

- **Trên Linux / Ubuntu / macOS:**
  ```bash
  source downloader-py/bin/activate
  ```

- **Trên Windows (Command Prompt):**
  ```cmd
  downloader-py\Scripts\activate.bat
  ```

- **Trên Windows (PowerShell):**
  ```powershell
  .\downloader-py\Scripts\Activate.ps1
  ```

> 💡 **Dấu hiệu thành công:** Tên môi trường `(downloader-py)` sẽ xuất hiện ở đầu dòng lệnh Terminal.

---

### Bước 2.4: Cài đặt thư viện từ `requirements.txt`

1. **Cập nhật pip lên bản mới nhất (khuyên dùng):**
   ```bash
   pip install --upgrade pip
   ```

2. **Cài đặt tất cả các thư viện trong dự án:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🏃 3. Kiểm Tra & Khởi Chạy Ứng Dụng

### 3.1. Kiểm tra các thư viện đã cài đặt
```bash
pip list
```
#>>>>>> WATCH config.md <<<<<<
### 3.2. Khởi chạy Flask Server (Chế độ Development)
```bash
python app.py
# Hoặc: python wsgi.py
```

### 3.3. Khởi chạy với Gunicorn (Chế độ Production)
```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

---

## 🛠️ 4. Mẹo & Câu Lệnh Thường Dùng

- **Thoát môi trường ảo:**
  ```bash
  deactivate
  ```

- **Cập nhật `requirements.txt` khi cài thêm gói mới:**
  ```bash
  pip freeze > requirements.txt
  ```

- **Lưu ý về Git:**
  Đảm bảo file `.gitignore` chứa dòng `downloader-py/` để tránh push nhầm toàn bộ file môi trường ảo lên repository:
  ```text
  downloader-py/
  __pycache__/
  *.pyc
  .env
  ```