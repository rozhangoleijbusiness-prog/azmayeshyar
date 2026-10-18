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
شما «آزمایش‌یار» هستید؛ یک دستیار هوشمند، بسیار دقیق و ایمن پزشکی که تحلیل مقدماتی نتایج آزمایش را به زبان ساده و قابل فهم به بیمار ارائه می‌دهد.

دستورالعمل‌ها و الزامات بالینی:
۱. سلب مسئولیت شفاف: صمیمانه تأکید کنید این بررسی صرفاً جنبه آگاهی‌بخشی دارد و قطعی نیست؛ تشخیص نهایی فقط در صلاحیت پزشک معالج است.
۲. جلوگیری از سردرگمی و هزینه‌های اضافه: با بررسی دقیق مقادیر خارج از محدوده، «تنها ۱ تخصص پزشکی اصلی» را به عنوان اولویت اول مراجعه مشخص کنید و علت آن را به زبان ساده توضیح دهید.
۳. تحلیل مقادیر: به پارامترهای غیرطبیعی و مهم آزمایش اشاره کنید و علت اهمیت آنها را بیان نمایید.
"""

def analyze_lab_data(user_text: str = "", image_file: Image.Image | None = None) -> str:
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        return "خطا: متغیر GEMINI_API_KEY در تنظیمات Environment رندر وارد نشده است."

    contents = []
    if user_text.strip():
        contents.append(user_text.strip())
    if image_file is not None:
        contents.append(image_file)

    if not contents:
        return "لطفاً متن مقادیر آزمایش را بنویسید یا عکس برگه آزمایش را انتخاب کنید."

    try:
        genai.configure(api_key=gemini_key)

        # مدل‌های پیشنهادی گوگل بر اساس پیام خطا
        model_names = [
            "gemini-3.8-flash",
            "gemini-3.0-flash",
            "gemini-2.5-flash",
            "gemini-1.5-flash"
        ]
        
        last_error = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_PROMPT
                )
                response = model.generate_content(contents)
                if response and response.text:
                    return response.text
            except Exception as err:
                last_error = err
                continue

        return f"خطا در دریافت پاسخ از هوش مصنوعی: {str(last_error)}"

    except Exception as exc:
        return f"خطا در اتصال به سرویس هوش مصنوعی: {str(exc)}"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    template_path = BASE_DIR / "templates" / "index.html"
    if not template_path.is_file():
        template_path = BASE_DIR / "index.html"

    if not template_path.is_file():
        return HTMLResponse("<h1>فایل index.html در مسیر پروژه یافت نشد.</h1>", status_code=500)

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
                {"analysis": "فرمت تصویر پشتیبانی نمی‌شود یا فایل خراب است."},
                status_code=400
            )

    result = analyze_lab_data(user_text=text, image_file=pil_image)
    return JSONResponse({"analysis": result})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
