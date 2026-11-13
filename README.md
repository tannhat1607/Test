# Hello Word — FastAPI + React Native + Firebase

Demo nhỏ để tập deploy backend lên Google Cloud Run. Màn hình app chỉ hiển thị **hello word** khi gọi API thành công.

```text
React Native (Expo Go) → FastAPI (Cloud Run) → Firebase Firestore
```

- `Backend/`: FastAPI, Firebase Admin SDK, Dockerfile.
- `Frontend/`: React Native dùng Expo, gọi API qua HTTP/HTTPS.
- Chạy local được ngay khi chưa cấu hình Firebase (`FIREBASE_ENABLED=false`).
- React Native chạy trên điện thoại/emulator. Cloud Run trong bài này chạy backend.

## 1. Chạy backend local

Cần Python 3.11 trở lên và Node.js LTS phù hợp với Expo SDK 58. Các lệnh dưới đây dùng **PowerShell**, bắt đầu tại thư mục gốc dự án.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Backend\requirements.txt
$env:FIREBASE_ENABLED = "false"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir Backend --host 0.0.0.0 --port 8080 --reload
```

Mở <http://localhost:8080/>:

```json
{"message":"hello word","source":"local"}
```

Swagger: <http://localhost:8080/docs>. Health check: <http://localhost:8080/health>.

`Backend/.env.example` mô tả các biến cấu hình; backend đọc biến môi trường của tiến trình, không tự nạp file `.env`.

## 2. Chạy frontend trên điện thoại

Mở terminal PowerShell thứ hai:

```powershell
cd Frontend
npm ci
Copy-Item .env.example .env
ipconfig
```

Sửa `Frontend/.env`, thay bằng IPv4 LAN của máy tính từ `ipconfig`:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.10:8080
```

Địa chỉ phía trên là ví dụ. Điện thoại và máy tính cần cùng Wi-Fi; cho phép Python qua Windows Firewall trên mạng riêng nếu được hỏi.

```powershell
npm start
```

Cài **Expo Go** trên điện thoại, quét QR để mở app. Nếu dùng Android emulator, đặt URL thành `http://10.0.2.2:8080`. Nếu dùng iOS simulator trên macOS, dùng `http://localhost:8080`. `localhost` trên điện thoại là chính điện thoại.

Khi đổi `.env`, dừng Expo rồi chạy `npm start -- --clear`. Biến `EXPO_PUBLIC_*` được đưa vào app, chỉ dùng cho URL/config công khai.

## 3. Tạo Firebase Firestore

1. Vào [Firebase Console](https://console.firebase.google.com/), tạo một project. Ghi lại **Project ID**, không phải tên hiển thị.
2. Build → Firestore Database → Create database. Chọn **Standard edition**, database **`(default)`**, production mode và vùng gần bạn, ví dụ Singapore nếu có.
3. Tạo collection `messages`, document ID `hello`, field `text` kiểu string với giá trị `hello word`.

```text
messages (collection)
  hello (document)
    text: "hello word"
```

App đọc Firestore thông qua backend. Không cần Firebase client config hay file service-account JSON trong frontend. Firebase Admin dùng IAM/ADC; Firestore Rules có thể giữ chặn truy cập trực tiếp từ client.

Để thử Firebase local, cài [Google Cloud CLI](https://cloud.google.com/sdk/docs/install), mở terminal mới, rồi chạy ở thư mục gốc:

```powershell
gcloud auth application-default login
$env:GOOGLE_CLOUD_PROJECT = "your-firebase-project-id"
gcloud auth application-default set-quota-project $env:GOOGLE_CLOUD_PROJECT
$env:FIREBASE_ENABLED = "true"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir Backend --host 0.0.0.0 --port 8080 --reload
```

Dừng backend cũ trước khi chạy lại. Tài khoản đăng nhập cần quyền đọc Firestore trong project. `/` phải trả `source: "firestore"`. Nếu thiếu document, thiếu field hoặc kết nối Firebase lỗi, API trả 503 để bạn nhận biết cấu hình chưa đúng; `/health` chỉ kiểm tra tiến trình API.

## 4. Deploy FastAPI lên Cloud Run

Dùng **cùng project với Firebase**. Project cần bật billing (Firebase Blaze khi liên kết billing). Cloud Run, Cloud Build, Artifact Registry và Firestore có thể phát sinh phí. Các bước IAM bên dưới dành cho tài khoản có quyền quản lý project, ví dụ Owner trong project cá nhân để học.

Mở PowerShell ở thư mục gốc. Thay đúng Project ID:

```powershell
gcloud auth login
$projectId = "your-firebase-project-id"
$region = "asia-southeast1"
gcloud config set project $projectId

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com

$projectNumber = gcloud projects describe $projectId --format="value(projectNumber)"
$runtimeAccount = "hello-word-api@${projectId}.iam.gserviceaccount.com"

gcloud iam service-accounts create hello-word-api --display-name="Hello Word API"
gcloud projects add-iam-policy-binding $projectId --member="serviceAccount:$runtimeAccount" --role="roles/datastore.viewer"

gcloud projects add-iam-policy-binding $projectId --member="serviceAccount:${projectNumber}-compute@developer.gserviceaccount.com" --role="roles/run.builder"

gcloud run deploy hello-word-api --source ./Backend --region $region --service-account $runtimeAccount --set-env-vars "FIREBASE_ENABLED=true,GOOGLE_CLOUD_PROJECT=$projectId" --allow-unauthenticated --port 8080 --min-instances 0 --max-instances 1
```

Lần đầu, đồng ý tạo Artifact Registry repository nếu CLI hỏi. Lệnh cấp `roles/run.builder` ở trên áp dụng cho build service account mặc định của luồng source deploy; nếu tổ chức cấu hình build identity khác, cấp quyền cho identity được Cloud Build báo trong lỗi. Khi deploy lại, bỏ qua bước tạo service account đã tồn tại.

Dockerfile được build từ `Backend/`; container lắng nghe `0.0.0.0:$PORT`. Cloud Run dùng runtime service account để lấy ADC và đọc Firestore, không cần tải private key lên server. API demo cho phép truy cập công khai để Expo Go gọi được.

Lấy URL và kiểm tra:

```powershell
$apiUrl = gcloud run services describe hello-word-api --region $region --format="value(status.url)"
Invoke-RestMethod "$apiUrl/health"
Invoke-RestMethod "$apiUrl/"
```

Kết quả `/` mong đợi:

```json
{"message":"hello word","source":"firestore"}
```

Nếu trả 503, kiểm tra document `messages/hello`, database `(default)`, Project ID và role của runtime service account. Xem log:

```powershell
gcloud run services logs read hello-word-api --region $region --limit 30
```

## 5. Cho app gọi Cloud Run

Sửa `Frontend/.env`, dùng nguyên URL HTTPS thực tế vừa nhận:

```dotenv
EXPO_PUBLIC_API_URL=https://your-service-url.run.app
```

Chạy lại Expo:

```powershell
cd Frontend
npm start -- --clear
```

Lúc này app gọi backend trên Cloud Run. Bạn có thể dừng backend local. Đổi field `text` trên Firebase Console rồi mở lại app để kiểm tra dữ liệu đi qua cả ba thành phần.

## 6. Kiểm tra và dọn tài nguyên

Kiểm tra API local và các trường hợp Firebase bằng fake client, không cần tài khoản cloud:

```powershell
.\.venv\Scripts\python.exe -m pip install -r Backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s Backend/tests -v
```

Kiểm tra bundle Android từ thư mục `Frontend`:

```powershell
npm run export:android
```

Tại thời điểm tạo demo, `npm audit` báo 3 mục mức moderate theo chuỗi `expo → @expo/fingerprint → minimatch`. Bản sửa tự động được đề xuất là hạ Expo qua nhiều major; demo giữ SDK 58 theo template chính thức. Kiểm tra lại bằng `npm audit` khi cập nhật dependency.

Docker local, nếu có Docker Desktop đang chạy:

```powershell
docker build -t hello-word-api ./Backend
docker run --rm -p 8080:8080 hello-word-api
```

Container mặc định trả dữ liệu local. Dừng bằng Ctrl+C.

Xóa service khi tập xong:

```powershell
gcloud run services delete hello-word-api --region asia-southeast1
```

Image trong Artifact Registry, build artifacts và database Firestore vẫn tồn tại; dọn chúng trong Console khi không dùng nữa.

Tài liệu chính thức: [Expo SDK](https://docs.expo.dev/versions/latest/), [Cloud Run source deploy](https://cloud.google.com/run/docs/deploying-source-code), [Cloud Run service identity](https://cloud.google.com/run/docs/securing/service-identity), [Firebase Admin / ADC](https://firebase.google.com/docs/admin/setup).
