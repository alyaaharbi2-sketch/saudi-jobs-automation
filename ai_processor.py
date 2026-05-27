import os
import json
import requests
import urllib.parse
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- إعداد المفاتيح والمعرفات ---
GEMINI_API_KEY = "AIzaSyAHf1dHxnYgiTP9y8iK6Plfw1V2RDsPTrM"
BLOG_ID = "2242214858615228803"
DB_FILE = "published_jobs.txt"
CLIENT_SECRETS_FILE = "client_secret.json" 
TOKEN_FILE = "token.json"

# تشغيل ذكاء جيميناي
client = genai.Client(api_key=GEMINI_API_KEY)

# الاتصال الآمن عبر OAuth 2.0
creds = None
scopes = ['https://www.googleapis.com/auth/blogger']

if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not os.path.exists(CLIENT_SECRETS_FILE):
            print(f"⚠️ خطأ: ملف {CLIENT_SECRETS_FILE} غير موجود بجانب السكربت!")
            exit()
        
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        
        auth_url, _ = flow.authorization_url(prompt='consent')
        print('\n🚀 افتحي هذا الرابط في المتصفح وسجلي دخولكِ واقبلي الصلاحيات:\n')
        print(auth_url)
        print('\n' + '='*50 + '\n')
        
        code = input('🔑 الصكي رمز التحقق (code) الذي ظهر لكِ في المتصفح هنا ثم اضغطي Enter: ').strip()
        flow.fetch_token(code=code)
        creds = flow.credentials
    
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

blogger_service = build('blogger', 'v3', credentials=creds)
print("🔒 تم تفعيل نظام التوثيق الشخصي بنجاح والتغلب على القيود.")

def is_already_published(job_link):
    if not os.path.exists(DB_FILE):
        return False
    with open(DB_FILE, "r") as file:
        return job_link in file.read().splitlines()

def save_published_link(job_link):
    with open(DB_FILE, "a") as file:
        file.write(job_link + "\n")

def fetch_latest_job_from_ewdifh():
    print("🔍 جاري فحص خلاصة وظائف موقع أي وظيفة (ewdifh.com)...")
    url = "https://www.ewdifh.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if '/jobs/' in href:
                job_title = link.text.strip() if link.text else "وظيفة شاغرة جديدة"
                job_link = "https://www.ewdifh.com" + href if not href.startswith('http') else href
                return {
                    "title": job_title,
                    "link": job_link,
                    "full_text": f"العنوان: {job_title}\nيعلن موقع أي وظيفة عن طرح فرص وظيفية وتعليمية وتدريبية جديدة ومحدثة اليوم للرجال والنساء في المملكة لحملة كافة المؤهلات."
                }
    except Exception as e:
        print(f"❌ حدث خطأ أثناء سحب البيانات: {e}")
    return None

def format_with_gemini_seo(raw_job_text, source_url):
    prompt = f"""
    أنت خبير كاتب محتوى وظائف سعودي ومحترف SEO. قم بإعادة صياغة إعلان الوظيفة/الدورة التالي إلى مقال احترافي وجذاب لمدونة بلوجر.
    اكتب بأسلوب بشري طبيعي بالكامل، ونسق تفاصيل الإعلان في جدول HTML أنيق أو قوائم مرتبة، وأنشئ وصفاً بحثياً (Snippet) للمقال لا يتعدى 140 حرفاً.
    كذلك، استخرج بدقة (اسم الجهة الطارحة للاعلان أو المؤسسة أو الجامعة المعنية) فقط دون أي كلمات إضافية.

    نص الإعلان الخام:
    {raw_job_text}
    
    أريد النتيجة بصيغة JSON نظيفة كالتالي تماماً:
    {{
        "title": "العنوان المطور هنا ويكون جذاباً ومتوافقاً مع السيو",
        "snippet": "الوصف البحثي المركّز للميتا تاق هنا - لا يتجاوز 140 حرفاً ويحتوي على الكلمات المفتاحية",
        "company_name": "اسم الجهة الطارحة هنا فقط (مثال: مكتبة الملك فهد العامة)",
        "content": "المحتوى الكامل بتنسيق HTML والجداول هنا"
    }}
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    
    data = json.loads(response.text)
    
    # توليد رابط شعار ديناميكي آمن يعتمد على اسم الجهة المستخرجة بالذكاء الاصطناعي
    company_query = urllib.parse.quote(data.get('company_name', 'وظائف السعودية'))
    logo_url = f"https://logo.clearbit.com/{company_query}.com?size=120"
    
    # بديل محلي ذكي للشعار في حال لم يتوفر في قاعدة البيانات العالمية لـ Clearbit
    # نضع واجهة محايدة وأنيقة تعرض الحرف الأول أو أيقونة بصيغة متناسقة للـ SEO
    logo_html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="{logo_url}" onerror="this.onerror=null;this.src='https://ui-avatars.com/api/?name={company_query}&background=0D8ABC&color=fff&size=120&bold=true';" 
             alt="شعار {data.get('company_name')}" style="max-width: 120px; height: auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"/>
    </div>
    """
    
    # دمج الشعار في بداية المقال، وتذييل المصدر في نهايته
    data['content'] = logo_html + data['content']
    disclaimer_html = f'<br><hr><br><div style="text-align: right; direction: rtl;"><strong>ملاحظة:</strong> للاطلاع على تفاصيل أكثر أو التقديم، يرجى زيارة <a href="{source_url}" target="_blank">المصدر الأصلي هنا</a>.</div>'
    data['content'] += disclaimer_html
    return data

def publish_to_blogger(title, content, snippets):
    body = {
        "kind": "blogger#post",
        "blog": {"id": BLOG_ID},
        "title": title,
        "content": content,
        "labels": ["وظائف السعودية", "تحديث يومي", "فرص تدريبية"],
        "customMetaData": snippets 
    }
    request = blogger_service.posts().insert(blogId=BLOG_ID, body=body, isDraft=True)
    response = request.execute()
    print(f"🎉 تم النشر المتوافق كمسودة بنجاح من حسابكِ المباشر!")
    print(f"🔗 رابط المعاينة: {response['url']}")

if __name__ == "__main__":
    job_data = fetch_latest_job_from_ewdifh()
    if job_data:
        if is_already_published(job_data['link']):
            print("⚠️ تخطي: الوظيفة تم نشرها مسبقاً لحمايتك من التكرار.")
        else:
            print("💡 إعلان جديد فريد! جاري تهيئته لمعايير Google AdSense والشعارات...")
            smart_data = format_with_gemini_seo(job_data['full_text'], job_data['link'])
            print("🚀 جاري دفع المقال مع ميزات الـ SEO الكاملة والشعار إلى بلوجر...")
            publish_to_blogger(title=smart_data['title'], content=smart_data['content'], snippets=smart_data['snippet'])
            save_published_link(job_data['link'])
    else:
        print("❌ تعذر جلب بيانات جديدة حالياً.")