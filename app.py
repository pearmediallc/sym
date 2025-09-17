# app.py
import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

TIKTOK_BASE = "https://business-api.tiktok.com/open_api/v1.3"

app = Flask(__name__, static_url_path="", static_folder="static")
CORS(app, supports_credentials=True)

def tt_headers(access_token: str):
    return {
        "Access-Token": access_token,
        "Content-Type": "application/json"
    }

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/script_generator")
@app.route("/script_generator/")
def script_generator():
    return send_from_directory("static/script_generator", "index.html")

@app.route("/avatar")
@app.route("/avatar/")
def avatar():
    return send_from_directory("static/avatar", "index.html")

@app.post("/api/create_task")
def create_task():
    """
    Body JSON:
    {
      "access_token": "...",
      "mode": "CUSTOM" | "PRODUCT",
      "custom_prompt": "...",                # when CUSTOM
      "script_generation_count": 3,          # 1..8
      "script_info": { ... },                # tone/style/pov/lang/industry (optional)
      "product_info": { ... },               # when PRODUCT
      "media_list": { "video_id_list": [], "image_url_list": [] },  # optional for PRODUCT
      "video_duration": "15S" | "30S"        # optional
    }
    """
    data = request.get_json(force=True) or {}

    # Debug logging
    print(f"Received data: {data}")

    access_token = data.get("access_token", "").strip()
    mode = data.get("mode", "CUSTOM")

    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400

    payload = {
        "script_generation_count": data.get("script_generation_count", 3),
    }

    # Attach mode-specific fields
    if mode.upper() == "CUSTOM":
        payload["script_source"] = "CUSTOM"
        custom_prompt = data.get("custom_prompt", "").strip()

        print(f"Custom prompt received: {custom_prompt}")

        if not custom_prompt:
            return jsonify({
                "error": "custom_prompt is required for CUSTOM mode",
                "details": f"Received data keys: {list(data.keys())}"
            }), 400
        payload["custom_prompt"] = custom_prompt
        # Note: script_info is NOT allowed for CUSTOM mode per TikTok API
    else:
        payload["script_source"] = "PRODUCT"
        # script_info is only used for PRODUCT mode
        payload["script_info"] = data.get("script_info") or {
            "tone": "Friendly",
            "style": "Product focused",
            "point_of_view": "From consumer",
            "script_language": "en",
            "relevant_industry": "All"
        }
        product_info = data.get("product_info")
        if not product_info:
            return jsonify({"error": "product_info is required for PRODUCT mode"}), 400
        payload["product_info"] = product_info
        media_list = data.get("media_list")
        if media_list:
            payload["media_list"] = media_list
        vd = data.get("video_duration")
        if vd in ("15S", "30S"):
            payload["video_duration"] = vd

    try:
        print(f"Sending payload to TikTok API: {payload}")
        r = requests.post(
            f"{TIKTOK_BASE}/creative/aigc/script_generation/task/create/",
            headers=tt_headers(access_token),
            json=payload,
            timeout=30,
        )
        response_data = r.json()
        print(f"TikTok API response: {response_data}")

        # If TikTok API returns an error, provide more context
        # TikTok API returns code as string "0" for success
        if r.status_code != 200 or str(response_data.get("code")) != "0":
            error_response = {
                "error": "TikTok API Error",
                "message": response_data.get("message", "Unknown error"),
                "code": response_data.get("code"),
                "details": f"Status: {r.status_code}, Code: {response_data.get('code')}",
                "request_payload": payload,
                "tiktok_response": response_data
            }
            return jsonify(error_response), r.status_code if r.status_code != 200 else 400

        return jsonify(response_data), r.status_code
    except requests.RequestException as e:
        print(f"Request exception: {str(e)}")
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.get("/api/task_status")
def task_status():
    """
    Query params:
      access_token=...
      task_id=...
    """
    access_token = (request.args.get("access_token") or "").strip()
    task_id = (request.args.get("task_id") or "").strip()
    if not access_token or not task_id:
        return jsonify({"error": "access_token and task_id are required"}), 400

    try:
        r = requests.get(
            f"{TIKTOK_BASE}/creative/aigc/script/task/get/",
            headers={"Access-Token": access_token},
            params={"task_id": task_id},
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/list_scripts")
def list_scripts():
    """
    Query params:
      access_token=...
      page=1
      page_size=20
    """
    access_token = (request.args.get("access_token") or "").strip()
    if not access_token:
        return jsonify({"error": "access_token is required"}), 400
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    try:
        r = requests.get(
            f"{TIKTOK_BASE}/creative/aigc/script/list/",
            headers={"Access-Token": access_token},
            params={"page": page, "page_size": page_size},
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/get_avatars")
def get_avatars():
    """
    Get available digital avatars.
    Query params:
      access_token=...
      page=1 (optional)
      page_size=10 (optional)
    """
    access_token = (request.args.get("access_token") or "").strip()
    if not access_token:
        return jsonify({"error": "access_token is required"}), 400

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))

    try:
        r = requests.get(
            f"{TIKTOK_BASE}/creative/digital_avatar/get/",
            headers={"Access-Token": access_token},
            params={"page": page, "page_size": page_size},
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/create_avatar_video_task")
def create_avatar_video_task():
    """
    Create digital avatar video tasks.
    Body JSON:
    {
      "access_token": "...",
      "material_packages": [
        {
          "avatar_id": "...",
          "script": "...",
          "video_name": "..." (optional),
          "package_id": "..." (optional)
        }
      ]
    }
    """
    data = request.get_json(force=True) or {}
    access_token = data.get("access_token", "").strip()
    material_packages = data.get("material_packages", [])

    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400
    if not material_packages:
        return jsonify({"error": "material_packages is required"}), 400

    # Validate material packages
    for package in material_packages:
        if not package.get("avatar_id"):
            return jsonify({"error": "avatar_id is required in material_packages"}), 400
        if not package.get("script"):
            return jsonify({"error": "script is required in material_packages"}), 400

    payload = {"material_packages": material_packages}

    try:
        r = requests.post(
            f"{TIKTOK_BASE}/creative/digital_avatar/video/task/create/",
            headers=tt_headers(access_token),
            json=payload,
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/get_avatar_video_task_status")
def get_avatar_video_task_status():
    """
    Get the results of digital avatar video tasks.
    Query params:
      access_token=...
      task_ids=["task1","task2",...] (JSON array as string)
    """
    access_token = (request.args.get("access_token") or "").strip()
    task_ids_str = (request.args.get("task_ids") or "").strip()

    if not access_token:
        return jsonify({"error": "access_token is required"}), 400
    if not task_ids_str:
        return jsonify({"error": "task_ids is required"}), 400

    try:
        # Parse task_ids JSON array
        import json
        task_ids = json.loads(task_ids_str)
        if not isinstance(task_ids, list):
            return jsonify({"error": "task_ids must be a JSON array"}), 400
    except (json.JSONDecodeError, Exception) as e:
        return jsonify({"error": f"task_ids must be a valid JSON array: {str(e)}"}), 400

    try:
        r = requests.get(
            f"{TIKTOK_BASE}/creative/digital_avatar/video/task/get/",
            headers={"Access-Token": access_token},
            params={"task_ids": task_ids_str},
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/list_avatar_videos")
def list_avatar_videos():
    """
    Get digital avatar videos under your account.
    Query params:
      access_token=...
      avatar_id=... (optional)
      start_date=YYYY-MM-DD (optional)
      end_date=YYYY-MM-DD (optional)
      page=1 (optional)
      page_size=10 (optional)
    """
    access_token = (request.args.get("access_token") or "").strip()
    if not access_token:
        return jsonify({"error": "access_token is required"}), 400

    # Build filtering object
    filtering = {}
    avatar_id = request.args.get("avatar_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if avatar_id:
        filtering["avatar_id"] = avatar_id
    if start_date:
        filtering["start_date"] = start_date
    if end_date:
        filtering["end_date"] = end_date

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))

    params = {"page": page, "page_size": page_size}
    if filtering:
        params["filtering"] = filtering

    try:
        r = requests.get(
            f"{TIKTOK_BASE}/creative/digital_avatar/video/list/",
            headers={"Access-Token": access_token},
            params=params,
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/update_avatar_video_name")
def update_avatar_video_name():
    """
    Update the name of a digital avatar video.
    Body JSON:
    {
      "access_token": "...",
      "avatar_video_id": "...",
      "file_name": "..."
    }
    """
    data = request.get_json(force=True) or {}
    access_token = data.get("access_token", "").strip()
    avatar_video_id = data.get("avatar_video_id", "").strip()
    file_name = data.get("file_name", "").strip()

    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400
    if not avatar_video_id:
        return jsonify({"error": "Missing avatar_video_id"}), 400
    if not file_name:
        return jsonify({"error": "Missing file_name"}), 400

    payload = {
        "avatar_video_id": avatar_video_id,
        "file_name": file_name
    }

    try:
        r = requests.post(
            f"{TIKTOK_BASE}/file/video/ad/update/",
            headers=tt_headers(access_token),
            json=payload,
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/get_assets_videos")
def get_assets_videos():
    """
    Get videos from TikTok Ads assets library.
    Query params:
      access_token=...
      advertiser_id=...
      page=1 (optional)
      page_size=20 (optional)
    """
    access_token = (request.args.get("access_token") or "").strip()
    advertiser_id = (request.args.get("advertiser_id") or "").strip()

    if not access_token:
        return jsonify({"error": "access_token is required"}), 400
    if not advertiser_id:
        return jsonify({"error": "advertiser_id is required"}), 400

    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    try:
        r = requests.get(
            f"{TIKTOK_BASE}/file/video/ad/search/",
            headers={"Access-Token": access_token},
            params={
                "advertiser_id": advertiser_id,
                "page": page,
                "page_size": page_size
            },
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/upload_video_to_ads")
def upload_video_to_ads():
    """
    Upload a video to TikTok Ads account (from URL or file_id).
    Body JSON:
    {
      "access_token": "...",
      "advertiser_id": "...",
      "video_url": "..." OR "video_id": "...",
      "video_name": "..."
    }
    """
    data = request.get_json(force=True) or {}
    access_token = data.get("access_token", "").strip()
    advertiser_id = data.get("advertiser_id", "").strip()
    video_url = data.get("video_url", "").strip()
    video_id = data.get("video_id", "").strip()
    video_name = data.get("video_name", "").strip()

    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400
    if not advertiser_id:
        return jsonify({"error": "Missing advertiser_id"}), 400
    if not video_url and not video_id:
        return jsonify({"error": "Either video_url or video_id is required"}), 400

    payload = {
        "advertiser_id": advertiser_id,
    }

    if video_url:
        payload["video_url"] = video_url
    if video_id:
        payload["video_id"] = video_id
    if video_name:
        payload["file_name"] = video_name

    try:
        # Upload video to TikTok Ads
        r = requests.post(
            f"{TIKTOK_BASE}/file/video/ad/upload/",
            headers=tt_headers(access_token),
            json=payload,
            timeout=60,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/get_video_upload_signature")
def get_video_upload_signature():
    """
    Get video upload signature from TikTok.
    Query params:
    - access_token
    - advertiser_id
    """
    access_token = (request.args.get("access_token") or "").strip()
    advertiser_id = (request.args.get("advertiser_id") or "").strip()

    if not access_token:
        return jsonify({"error": "access_token is required"}), 400
    if not advertiser_id:
        return jsonify({"error": "advertiser_id is required"}), 400

    try:
        # Get upload signature
        r = requests.get(
            f"{TIKTOK_BASE}/file/video/ad/upload/",
            headers={"Access-Token": access_token},
            params={"advertiser_id": advertiser_id},
            timeout=30,
        )
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/upload_image_file")
def upload_image_file():
    """
    Upload an image file to TikTok Ads.
    Supports both file upload and URL upload.
    Multipart form data with:
    - access_token
    - advertiser_id
    - image_file (the actual file) OR image_url
    - upload_type: "UPLOAD_BY_FILE" or "UPLOAD_BY_URL"
    """
    import requests
    import tempfile
    import os

    access_token = request.form.get("access_token", "").strip()
    advertiser_id = request.form.get("advertiser_id", "").strip()
    upload_type = request.form.get("upload_type", "UPLOAD_BY_FILE").strip()

    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400
    if not advertiser_id:
        return jsonify({"error": "Missing advertiser_id"}), 400

    if upload_type == "UPLOAD_BY_FILE":
        if 'image_file' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
    elif upload_type == "UPLOAD_BY_URL":
        image_url = request.form.get("image_url", "").strip()
        if not image_url:
            return jsonify({"error": "image_url is required for URL upload"}), 400

    try:
        if upload_type == "UPLOAD_BY_FILE":
            image_file = request.files['image_file']

            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_file.filename)[1]) as tmp_file:
                image_file.save(tmp_file.name)
                tmp_path = tmp_file.name

            try:
                # Open the file in binary mode
                with open(tmp_path, 'rb') as f:
                    # Prepare multipart form data
                    files = {
                        'image_file': (image_file.filename, f, image_file.content_type or 'image/jpeg')
                    }

                    data = {
                        'advertiser_id': advertiser_id,
                        'upload_type': 'UPLOAD_BY_FILE',
                        'file_name': image_file.filename
                    }

                    r = requests.post(
                        f"{TIKTOK_BASE}/file/image/ad/upload/",
                        headers={"Access-Token": access_token},
                        files=files,
                        data=data,
                        timeout=300,  # 5 minutes for large files
                    )
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            # URL upload
            image_url = request.form.get("image_url", "").strip()

            # Use correct parameters for URL upload
            payload = {
                "advertiser_id": advertiser_id,
                "upload_type": "UPLOAD_BY_URL",
                "image_url": image_url,
                "file_name": request.form.get("file_name", "uploaded_image.jpg")
            }

            r = requests.post(
                f"{TIKTOK_BASE}/file/image/ad/upload/",
                headers=tt_headers(access_token),
                json=payload,
                timeout=60,
            )

        # Try to parse JSON response
        try:
            response_data = r.json()
        except:
            # If JSON parsing fails, return the raw text
            return jsonify({"error": "Invalid JSON response", "raw_response": r.text}), r.status_code

        return jsonify(response_data), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.post("/api/upload_video_file")
def upload_video_file():
    """
    Upload a video file from local computer to TikTok.
    Supports both file upload with signature and URL upload.
    Multipart form data with:
    - access_token
    - advertiser_id
    - video_file (the actual file) OR video_url
    - video_signature (for file upload)
    - upload_type: "UPLOAD_BY_FILE" or "UPLOAD_BY_URL"
    """
    import requests
    import tempfile
    import os

    access_token = request.form.get("access_token", "").strip()
    advertiser_id = request.form.get("advertiser_id", "").strip()
    upload_type = request.form.get("upload_type", "UPLOAD_BY_FILE").strip()

    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400
    if not advertiser_id:
        return jsonify({"error": "Missing advertiser_id"}), 400

    if upload_type == "UPLOAD_BY_FILE":
        if 'video_file' not in request.files:
            return jsonify({"error": "No video file provided"}), 400
        # Signature is optional for file upload - let's try without it first
        video_signature = request.form.get("video_signature", "").strip()
    elif upload_type == "UPLOAD_BY_URL":
        video_url = request.form.get("video_url", "").strip()
        if not video_url:
            return jsonify({"error": "video_url is required for URL upload"}), 400

    try:
        if upload_type == "UPLOAD_BY_FILE":
            video_file = request.files['video_file']
            video_signature = request.form.get("video_signature", "").strip()

            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1]) as tmp_file:
                video_file.save(tmp_file.name)
                tmp_path = tmp_file.name

            try:
                # Open the file in binary mode
                with open(tmp_path, 'rb') as f:
                    # Prepare multipart form data with signature
                    files = {
                        'video_file': (video_file.filename, f, video_file.content_type or 'video/mp4')
                    }

                    data = {
                        'advertiser_id': advertiser_id,
                        'upload_type': 'UPLOAD_BY_FILE',
                        'file_name': video_file.filename,
                        'flaw_detect': 'true',
                        'auto_fix_enabled': 'true',
                        'auto_bind_enabled': 'true'
                    }

                    # Only include signature if provided
                    if video_signature:
                        data['video_signature'] = video_signature

                    r = requests.post(
                        f"{TIKTOK_BASE}/file/video/ad/upload/",
                        headers={"Access-Token": access_token},
                        files=files,
                        data=data,
                        timeout=300,  # 5 minutes for large files
                    )
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            # URL upload
            video_url = request.form.get("video_url", "").strip()
            if not video_url:
                return jsonify({"error": "video_url is required for URL upload"}), 400

            # Use correct parameters for URL upload
            payload = {
                "advertiser_id": advertiser_id,
                "upload_type": "UPLOAD_BY_URL",
                "video_url": video_url,
                "file_name": request.form.get("file_name", "uploaded_video.mp4"),
                "flaw_detect": True,
                "auto_fix_enabled": True,
                "auto_bind_enabled": True
            }

            r = requests.post(
                f"{TIKTOK_BASE}/file/video/ad/upload/",
                headers=tt_headers(access_token),
                json=payload,
                timeout=60,
            )

        # Try to parse JSON response
        try:
            response_data = r.json()
        except:
            # If JSON parsing fails, return the raw text
            return jsonify({"error": "Invalid JSON response", "raw_response": r.text}), r.status_code

        return jsonify(response_data), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
