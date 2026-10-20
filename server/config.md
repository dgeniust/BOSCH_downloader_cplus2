# Hướng dẫn cài đặt Flask Application với Nginx và Gunicorn trên Ubuntu 22.04

Hướng dẫn cách deploy một ứng dụng Flask sử dụng Gunicorn làm WSGI server và Nginx làm reverse proxy. 

**Thông tin cấu hình:**
- **Tên project:** `server`
- **Môi trường ảo (virtualenv):** `downloader-py`
- **Đường dẫn thư mục làm việc:** `/home/<id-user>/Working/<folder-chứa-project>/server`

---

## Bước 1: Cài đặt các thành phần cần thiết

Đầu tiên, cập nhật hệ thống và cài đặt các package cần thiết bao gồm Python, Nginx và các công cụ build.

```bash
sudo apt update
sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv nginx -y
```

## Bước 2: Thiết lập thư mục và Môi trường ảo

Tạo thư mục chứa project và di chuyển vào đó. **Lưu ý:** Hãy thay thế `<id-user>` và `<folder-chứa-project>` bằng tên user và thư mục thực tế của bạn.

```bash
# Tạo cấu trúc thư mục 
# (can pass this step, cd into /server in the project clone from gitlab)
mkdir -p /home/<id-user>/Working/<folder-chứa-project>/server
cd /home/<id-user>/Working/<folder-chứa-project>/server

# Tạo môi trường ảo với tên downloader-py
python3 -m venv downloader-py

# Kích hoạt môi trường ảo
source downloader-py/bin/activate
```
*Sau khi kích hoạt, terminal của bạn sẽ có tiền tố `(downloader-py)` ở đầu.*

## Bước 3: Cài đặt Flask và Gunicorn

Bên trong môi trường ảo, tiến hành cài đặt wheel, Flask và Gunicorn:

```bash
pip install wheel
pip install gunicorn flask
```

## Bước 4: Tạo ứng dụng Flask mẫu và WSGI Entry Point
(CAN PASS THIS STEP, app.py already has code inside)
Tạo file chạy chính của ứng dụng. Ví dụ tạo file `app.py`:

```bash
nano app.py
```
Thêm nội dung sau vào `app.py`:
```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "<h1 style='color:blue'>Flask Server đang chạy!</h1>"

if __name__ == "__main__":
    app.run(host='0.0.0.0')
```
(CAN PASS THIS STEP, ALREADY HAS wsgi.py)
Tiếp theo, tạo file entry point cho Gunicorn có tên là `wsgi.py`:

```bash
nano wsgi.py
```
Nội dung file `wsgi.py`:
```python
from app import app

if __name__ == "__main__":
    app.run()
```

## Bước 5: Cấu hình systemd để chạy Gunicorn dưới dạng Service

Tạo file service cho systemd để Gunicorn tự động chạy khi khởi động server.

```bash
sudo nano /etc/systemd/system/server.service
```

Dán nội dung sau vào file (Nhớ thay thế `<id-user>` và `<folder-chứa-project>`):

```ini
[Unit]
Description=Gunicorn instance to serve Flask Project (server)
After=network.target

[Service]
# Đổi <id-user> thành username của bạn trên Ubuntu
User=<id-user>
Group=www-data

WorkingDirectory=/home/<id-user>/Working/<folder-chứa-project>/server
Environment="PATH=/home/<id-user>/Working/<folder-chứa-project>/server/downloader-py/bin"

# Chạy Gunicorn, tạo file server.sock
ExecStart=/home/<id-user>/Working/<folder-chứa-project>/server/downloader-py/bin/gunicorn --workers 3 --bind unix:server.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
```

Khởi động và kích hoạt service:

```bash
sudo systemctl start server
sudo systemctl enable server
sudo systemctl status server
```
*Đảm bảo status báo `active (running)`.*

## Bước 6: Cấu hình Nginx làm Reverse Proxy

Tạo file cấu hình server block cho Nginx:

```bash
sudo nano /etc/nginx/sites-available/server
```

Thêm nội dung sau (thay `your_domain_or_IP` bằng IP của server hoặc tên miền):

(THIS STEP YOU CAN TYPE: "server_name _;" TO ALLOW CATCH EVERY DOMAIN)
```nginx
server {
    listen 80;
    server_name your_domain_or_IP;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/<id-user>/Working/<folder-chứa-project>/server/server.sock;
    }
}
```

Kích hoạt cấu hình Nginx bằng cách tạo symlink:

```bash
sudo ln -s /etc/nginx/sites-available/server /etc/nginx/sites-enabled/
```

Kiểm tra lỗi cú pháp Nginx và khởi động lại:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## Bước 7: Phân quyền thư mục (Khắc phục lỗi 502 Bad Gateway)

Nginx cần quyền truy cập vào file `.sock` trong thư mục user của bạn. Hãy đảm bảo thư mục home và các thư mục con có quyền đọc/thực thi (ít nhất là `755` hoặc `711`).

```bash
chmod 755 /home/<id-user>
chmod 755 /home/<id-user>/Working
chmod 755 /home/<id-user>/Working/<folder-chứa-project>
chmod 755 /home/<id-user>/Working/<folder-chứa-project>/server
```

## Bước 8: Mở cổng Firewall (Tùy chọn)

Nếu bạn đang bật UFW, hãy mở port cho Nginx:

```bash
sudo ufw allow 'Nginx Full'
```

---
**Hoàn tất!** Bây giờ bạn có thể truy cập `http://your_domain_or_IP` trên trình duyệt để xem thành quả.
(TRY http://localhost)