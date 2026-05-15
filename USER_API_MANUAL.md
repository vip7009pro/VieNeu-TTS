# VieNeu-TTS User API Manual

Tài liệu này mô tả cách dùng API server hiện có trong repo để:

- Liệt kê giọng preset sẵn có.
- Đổi model đang phục vụ.
- Sinh audio từ văn bản và nhận lại file WAV.
- Streaming audio khi muốn phát từng phần.
- Trích xuất text từ một URL rồi đem đi synthesize.

## 1. Tổng quan kiến trúc

Repo này đã có một FastAPI server ở [apps/web_stream.py](apps/web_stream.py) và một entrypoint CLI được khai báo trong [pyproject.toml](pyproject.toml) với tên `vieneu-stream`.

Server này chạy local, có CORS mở để web app bên ngoài có thể gọi trực tiếp. Các endpoint chính:

- `GET /health`
- `GET /models`
- `POST /set_model`
- `GET /voices`
- `POST /extract_url`
- `GET /stream`
- `POST /stream`
- `POST /synthesize`

## 2. Cách chạy server

### Cách 1: Chạy bằng uv

```bash
uv run vieneu-stream
```

### Cách 2: Chạy trực tiếp module

```bash
python -m apps.web_stream
```

Mặc định server sẽ lắng nghe tại:

- Host: `127.0.0.1`
- Port: `8001`

Mở trình duyệt để xem giao diện demo tại:

- `http://127.0.0.1:8001/`

## 3. Startup flow

Khi server khởi động, nó sẽ:

1. Load model mặc định `ngochuyen`.
2. Load codec ONNX nhẹ cho chế độ local CPU.
3. Nạp danh sách voice preset từ `voices.json` của model.
4. Mở FastAPI app để client gọi API.

Nếu model chưa load được, endpoint `/health` vẫn trả thông tin trạng thái và các API khác sẽ trả lỗi rõ ràng thay vì crash âm thầm.

## 4. Endpoint health

### `GET /health`

Kiểm tra server còn sống hay không.

#### Response

```json
{
  "status": "ok",
  "model_loaded": true,
  "current_model": "ngochuyen"
}
```

#### Khi dùng

- Dùng làm health check cho backend hoặc Docker.
- Dùng để frontend biết server đã sẵn sàng trước khi hiển thị UI.

## 5. Liệt kê model

### `GET /models`

Trả danh sách model preset mà server đang biết.

#### Response mẫu

```json
[
  {
    "key": "q4",
    "name": "VieNeu 0.3B (Q4_0) - Fast/Light",
    "desc": "Recommended for most CPUs (Speed > Quality)",
    "active": false
  }
]
```

#### Ý nghĩa

- `key`: khóa model để gửi vào `/set_model`
- `name`: tên hiển thị
- `desc`: mô tả ngắn
- `active`: model hiện đang được load

## 6. Đổi model đang phục vụ

### `POST /set_model`

Đổi model local đang chạy.

#### Request body

```json
{
  "model_key": "q4"
}
```

#### Giá trị hợp lệ

- `q4`
- `q8`
- `ngochuyen`
- Hoặc Hugging Face repo ID có chứa `gguf`

#### Response thành công

```json
{
  "status": "ok",
  "current_model": "q4"
}
```

#### Response lỗi

```json
{
  "status": "error",
  "message": "..."
}
```

#### Khi dùng

- Cho phép user đổi voice model hoặc mức chất lượng/speed.
- Có thể gắn vào dropdown model trên web app.

## 7. Liệt kê preset voices

### `GET /voices`

Trả danh sách giọng preset đi kèm model đang load.

#### Response mẫu

```json
[
  {
    "id": "Tuyen",
    "name": "Phạm Tuyên (nam miền Bắc)"
  },
  {
    "id": "Ly",
    "name": "Trúc Ly (nữ miền Bắc)"
  }
]
```

#### Ý nghĩa

- `id`: ID dùng để gửi vào `voice_id`
- `name`: label để hiển thị cho user

#### Lưu ý

- Nếu model chưa load, server sẽ trả lỗi HTTP `503`.
- Nếu model không có preset voices, server trả mảng rỗng hoặc lỗi tùy trạng thái load.

## 8. Trích xuất text từ URL

### `POST /extract_url`

Endpoint này lấy text từ một URL bài viết để đưa vào TTS.

#### Request body

```json
{
  "url": "https://example.com/article",
  "max_chars": 5000
}
```

#### Response thành công

```json
{
  "status": "ok",
  "title": "Tiêu đề bài viết",
  "text": "Nội dung đã trích xuất...",
  "char_count": 4210,
  "truncated": false
}
```

#### Khi dùng

- Dùng cho web app đọc tin tức, blog, hoặc nội dung dài từ một link.
- Frontend có thể gọi endpoint này, đổ text vào ô soạn, rồi gọi `/synthesize`.

## 9. Streaming audio

### `GET /stream`

Trả audio dạng stream WAV.

#### Query parameters

- `text`: văn bản cần đọc
- `voice_id`: ID giọng preset, tùy chọn

#### Ví dụ

```text
GET /stream?text=Xin%20chao&voice_id=Tuyen
```

#### Response

- Media type: `audio/wav`
- Dữ liệu được stream dần về client

### `POST /stream`

Giống `GET /stream`, nhưng nhận JSON body.

#### Request body

```json
{
  "text": "Xin chào, đây là ví dụ stream.",
  "voice_id": "Tuyen"
}
```

#### Khi dùng

- Phù hợp với text dài.
- Phù hợp khi bạn muốn phát dần trong UI thay vì đợi file hoàn tất.

## 10. API sinh file WAV và trả file về client

### `POST /synthesize`

Đây là endpoint phù hợp nhất cho web app của bạn nếu muốn:

1. User chọn giọng.
2. User nhập text.
3. Frontend gửi request lên server.
4. Server sinh file âm thanh.
5. Server trả file WAV lại cho client.

#### Request body

```json
{
  "text": "Xin chào, đây là bản test.",
  "voice_id": "Tuyen",
  "filename": "my_sample.wav"
}
```

#### Trường dữ liệu

- `text`: bắt buộc, nội dung cần synthesize
- `voice_id`: tùy chọn, chọn preset voice
- `filename`: tùy chọn, tên file trả về; nếu không truyền thì server tự tạo tên

#### Response

Server trả thẳng file WAV với header download inline/attachment tùy client.

- Media type: `audio/wav`
- File được lưu tạm trong `outputs/api/`

#### Ví dụ cURL

```bash
curl -X POST http://127.0.0.1:8001/synthesize ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Xin chào, đây là bản test.\",\"voice_id\":\"Tuyen\",\"filename\":\"demo.wav\"}" ^
  --output demo.wav
```

#### Khi dùng với frontend

- Nếu bạn dùng `fetch`, hãy đọc response bằng `blob()` rồi tạo URL để phát audio.
- Nếu bạn dùng `<audio>`, chỉ cần gán blob URL cho `src`.

## 11. Ví dụ gọi API bằng JavaScript

### Lấy danh sách voices

```javascript
const res = await fetch('http://127.0.0.1:8001/voices');
const voices = await res.json();
console.log(voices);
```

### Gọi synthesize và nhận file WAV

```javascript
async function synthesize(text, voiceId) {
  const res = await fetch('http://127.0.0.1:8001/synthesize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      voice_id: voiceId,
      filename: 'output.wav'
    })
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText);
  }

  const blob = await res.blob();
  const audioUrl = URL.createObjectURL(blob);
  return audioUrl;
}
```

### Phát audio trong browser

```javascript
const audioUrl = await synthesize('Xin chào', 'Tuyen');
const audio = new Audio(audioUrl);
await audio.play();
```

## 12. Luồng tích hợp cho web app

Đây là flow khuyến nghị nếu bạn làm web app riêng:

1. Khi mở trang, gọi `GET /health` để kiểm tra server.
2. Gọi `GET /voices` để nạp danh sách giọng.
3. User chọn giọng từ dropdown.
4. User nhập nội dung text.
5. Gửi `POST /synthesize` với `text` và `voice_id`.
6. Nhận file WAV về frontend.
7. Phát audio trực tiếp hoặc cho phép download.

## 13. Ví dụ payload cho frontend

### State tối thiểu

```json
{
  "voiceId": "Tuyen",
  "text": "Xin chào",
  "filename": "demo.wav"
}
```

### Quy ước UI

- Dropdown voices lấy từ `/voices`
- Textarea nhập nội dung
- Nút Generate gọi `/synthesize`
- Nút Play phát audio blob
- Nút Download tải file WAV

## 14. Error handling

### `503 Service Unavailable`

Server trả khi model chưa load xong.

### `404 Not Found`

Server trả khi `voice_id` không tồn tại.

### `500 Internal Server Error`

Server trả khi quá trình synthesize lỗi ngoài dự kiến.

### Gợi ý frontend

- Luôn kiểm tra `response.ok` trước khi đọc blob.
- Hiển thị message rõ ràng nếu API trả `503` hoặc `404`.

## 15. Mẫu tích hợp nhanh với React

```javascript
async function handleGenerate() {
  const res = await fetch('http://127.0.0.1:8001/synthesize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      voice_id: selectedVoice,
      filename: 'result.wav'
    })
  });

  if (!res.ok) {
    const message = await res.text();
    throw new Error(message);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  setAudioUrl(url);
}
```

## 16. Lưu ý về file output

- File sinh ra được lưu trong `outputs/api/`.
- Nếu không truyền `filename`, server tự đặt tên theo timestamp.
- Nếu frontend chỉ cần phát ngay, có thể không cần quan tâm file trên ổ đĩa.

## 17. Kết luận

Nếu mục tiêu của bạn là một web app lấy danh sách voice preset, cho user nhập text, rồi sinh audio trả về client, thì endpoint quan trọng nhất là `GET /voices` và `POST /synthesize`.

`/stream` vẫn hữu ích nếu bạn muốn phát audio dạng stream, còn `/extract_url` là tiện ích phụ để tự động lấy nội dung từ link.