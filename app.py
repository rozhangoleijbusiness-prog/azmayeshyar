import io
import os
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="آزمایش‌یار")
templates = Jinja2Templates(directory="templates")

# تنظیم کلید جمینای
gemini_api_key = os.getenv("GEMINI_API_KEY", "")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

SYSTEM_PROMPT = """
شما «آزمایش‌یار» هستید؛ یک دستیار هوشمند و ایمن پزشکی که وظیفه تحلیل مقدماتی آزمایش‌ها و راهنمایی بیمار به مناسب‌ترین پزشک را بر عهده دارد.

قوانین بسیار مهم:
1. ایمنی بالینی (Safety Disclaimer): به زبان صمیمی و محترمانه یادآوری کنید که این تحلیل صرفاً جهت آگاهی‌بخشی است و به هیچ وجه جایگزین ویزیت حضوری و تشخیص قطعی پزشک نیست.
2. جلوگیری از سردرگمی بیمار: بیمار را با نام بردن از چند تخصص مختلف گیج نکنید؛ با توجه به مهم‌ترین نتیجه غیرطبیعی آزمایش، «تنها ۱ تخصص پزشکی اصلی» را به عنوان بهترین گزینه مراجعه پیشنهاد دهید و علتش را خیلی ساده توضیح دهید.
3. تحلیل ساده و صرفه‌جویی در هزینه: مقادیر غیرعادی را مشخص کنید و علت نیاز به پزشک را واضح بگویید تا بیمار هزینه‌های غیرضروری انجام ندهد.
"""

def analyze_lab_data(user_text: str = "", image_file: Image.Image = None) -> str:
    try:
        current_key = os.getenv("GEMINI_API_KEY", "")
        if not current_key:
            return "خطا: کلید GEMINI_API_KEY در تنظیمات رندر (Environment) یا فایل .env تنظیم نشده است."

        genai.configure(api_key=current_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        contents = []
        if user_text:
            contents.append(user_text)
        if image_file:
            contents.append(image_file)
        
        if not contents:
            return "لطفاً متن آزمایش یا تصویر برگه آن را وارد کنید."

        response = model.generate_content(contents)
        return response.text
    except Exception as e:
        return f"خطا در ارتباط با هوش مصنوعی: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.post("/api/analyze")
async def analyze(text: str = Form(""), file: UploadFile = File(None)):
    pil_image = None
    if file and file.filename:
        image_bytes = await file.read()
        pil_image = Image.open(io.BytesIO(image_bytes))
    result = analyze_lab_data(user_text=text, image_file=pil_image)
    return JSONResponse({"analysis": result})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

