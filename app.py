import io
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
import google.generativeai as genai


app = FastAPI(title="آزمایش‌یار")

BASE_DIR = Path(__file__).resolve().parent
SYSTEM_PROMPT = """
شما «آزمایش‌یار» هستید؛ دستیار آگاهی‌بخش برای توضیح مقدماتی نتایج آزمایش.

- تحلیل شما تشخیص پزشکی نیست و جایگزین ویزیت پزشک نمی‌شود.
- مقادیر را فقط با توجه به محدوده مرجع درج‌شده در برگه تفسیر کنید؛ اگر محدوده موجود نیست، این محدودیت را بگویید.
- از نتیجه آزمایش به‌تنهایی تشخیص قطعی ندهید و درباره دارو یا تغییر درمان دستور ندهید.
- در صورت نیاز به مراجعه، فقط یک تخصص اصلی پیشنهاد دهید و دلیلش را ساده توضیح دهید.
- اگر اطلاعات کافی نیست، سؤال یا محدودیت را روشن بیان کنید.
"""

def analyze_lab_data(user_text: str = "", image_file: Image.Image | None = None) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "خطا: متغیر GEMINI_API_KEY در Environment Variables سرویس Render تنظیم نشده است."

    contents = []
    if user_text.strip():
        contents.append(user_text.strip())
    if image_file is not None:
        contents.append(image_file)

    if not contents:
        return "لطفاً متن آزمایش یا تصویر برگه را وارد کنید."

    try:
        genai.configure(api_key=api_key)

        # نام‌های مدل را به‌ترتیب امتحان می‌کند؛ دسترسی به مدل به API key و پروژه بستگی دارد.
        model_names = ["gemini-2.5-flash", "gemini-2.0-flash"]
        last_error = None

        for model_name in model_names:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_PROMPT,
                )
                response = model.generate_content(contents)
                answer = getattr(response, "text", None)
                if answer:
                    return answer
                last_error = "مدل پاسخ متنی برنگرداند."
            except Exception as exc:
                last_error = exc

        return f"خطا در فراخوانی Gemini: {last_error}"

    except Exception as exc:
        return f"خطا در ارتباط با هوش مصنوعی: {exc}"


@app.get("/", response_class=HTMLResponse)
async def read_root():
    template_path = BASE_DIR / "templates" / "index.html"
    if not template_path.is_file():
        template_path = BASE_DIR / "index.html"

    if not template_path.is_file():
        return HTMLResponse(
            "<h1>فایل index.html پیدا نشد</h1>"
            "<p>آن را در پوشه templates کنار app.py قرار دهید.</p>",
            status_code=500,
        )

    return HTMLResponse(template_path.read_text(encoding="utf-8"))


@app.post("/api/analyze")
async def analyze(text: str = Form(""), file: UploadFile | None = File(None)):
    pil_image = None

    if file and file.filename:
        try:
            image_bytes = await file.read()
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except (UnidentifiedImageError, OSError):
            return JSONResponse(
                {"analysis": "فایل ارسالی تصویر قابل‌خواندن نیست؛ لطفاً تصویر دیگری بفرستید."},
                status_code=400,
            )

    result = analyze_lab_data(user_text=text, image_file=pil_image)
    return JSONResponse({"analysis": result})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
