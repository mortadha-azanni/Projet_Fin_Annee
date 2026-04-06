# دليل استخدام Redis في المشروع

## ما هو Redis؟

Redis (Remote Dictionary Server) هو نظام قاعدة بيانات في الذاكرة مفتوح المصدر يُستخدم كمخزن مؤقت (cache)، قاعدة بيانات رئيسية، وسيط للرسائل. يتميز بسرعته العالية ودعمه لأنواع بيانات متعددة.

### المزايا الرئيسية:
- **سرعة عالية**: جميع البيانات محفوظة في الذاكرة
- **أنواع بيانات متعددة**: سلاسل، قوائم، مجموعات، مجموعات مرتبة، هاشات
- **الاستمرارية**: حفظ البيانات على القرص
- **التكرار**: دعم النسخ الاحتياطي والتكرار
- **الانتهاء التلقائي**: إمكانية تعيين وقت انتهاء صلاحية البيانات

## كيفية عمل Redis في هذا المشروع

في مشروعنا الموزع، نستخدم Redis كمخزن مؤقت لتحسين الأداء وتقليل الحمل على الخدمات.

### البنية العامة:
```
Gateway Node ←→ Redis ←→ Scraper Node
                    ←→ Ranker Node
```

## استخدام Redis في الكود

### 1. إعداد الاتصال

```python
import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

def get_redis():
    """إرجاع عميل Redis. يرجع None إذا كان Redis غير متاح."""
    try:
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.ping()  # اختبار الاتصال
        return client
    except Exception:
        return None
```

### 2. التخزين المؤقت في Scraper Node

```python
# تخزين نتائج الكشط لمدة 10 دقائق
CACHE_TTL = 600

@app.get("/scrape")
async def scrape(url: str):
    cache_key = f"scrape:{url}"
    r = get_redis()
    
    # محاولة استرجاع من الذاكرة المؤقتة
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["from_cache"] = True
            return result
    
    # إجراء الكشط...
    
    # حفظ في الذاكرة المؤقتة
    if r:
        r.setex(cache_key, CACHE_TTL, json.dumps(result.dict()))
    
    return result
```

### 3. التخزين المؤقت في Ranker Node

```python
# تخزين نتائج التصنيف لمدة 5 دقائق
CACHE_TTL = 300

@app.post("/rank")
async def rank(items: List[Item]):
    # إنشاء مفتاح فريد من البيانات المدخلة
    input_hash = hashlib.md5(json.dumps([item.dict() for item in sorted_items]).encode()).hexdigest()
    cache_key = f"rank:{input_hash}"
    
    r = get_redis()
    
    # محاولة استرجاع من الذاكرة المؤقتة
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["from_cache"] = True
            return result
    
    # إجراء التصنيف...
    
    # حفظ في الذاكرة المؤقتة
    if r:
        r.setex(cache_key, CACHE_TTL, json.dumps(result.dict()))
    
    return result
```

### 4. التخزين المؤقت في Gateway Node

```python
# تخزين النتائج الكاملة لمدة 5 دقائق
CACHE_TTL = 300

@app.get("/scrape-and-rank")
async def scrape_and_rank(url: str):
    cache_key = f"scrape-and-rank:{url}"
    
    r = get_redis()
    
    # محاولة استرجاع من الذاكرة المؤقتة
    if r:
        cached = r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["from_cache"] = True
            return result
    
    # استدعاء الخدمات...
    
    # حفظ في الذاكرة المؤقتة
    if r:
        r.setex(cache_key, CACHE_TTL, json.dumps(result))
    
    return result
```

## إعداد Redis في Docker

```yaml
# من docker-compose.yml
redis:
  image: redis:7-alpine
  container_name: redis
  ports:
    - "${REDIS_LOCAL_PORT:-6380}:6379"
  networks:
    - pfa-network
  restart: unless-stopped
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 5s
```

## فوائد استخدام Redis في هذا المشروع

### 1. تحسين الأداء
- تقليل وقت الاستجابة للطلبات المتكررة
- تقليل الحمل على خدمات الكشط والتصنيف

### 2. قابلية التوسع
- إمكانية إضافة المزيد من العقد دون تغيير منطق العمل
- توزيع الحمل عبر عدة خوادم

### 3. المرونة
- الخدمات تعمل حتى لو توقف Redis (مع رسائل تحذير)
- إمكانية تعطيل التخزين المؤقت مؤقتاً

## مراقبة Redis

### فحص الحالة الصحية
```bash
# من خلال API
GET /health
GET /services/health
```

### مراقبة استخدام Redis
```bash
# الاتصال بـ Redis CLI
docker exec -it redis redis-cli

# عرض الإحصائيات
INFO

# عرض المفاتيح
KEYS *

# عرض عدد المفاتيح
DBSIZE
```

## استكشاف الأخطاء

### مشاكل شائعة وحلولها

1. **Redis غير متاح**
   - تأكد من تشغيل الحاوية: `docker-compose up redis`
   - تحقق من متغيرات البيئة: `REDIS_HOST`, `REDIS_PORT`

2. **بيانات غير محفوظة**
   - تحقق من إعدادات TTL (وقت البقاء)
   - تأكد من صحة JSON عند التخزين

3. **بطء في الأداء**
   - زيادة موارد Redis في docker-compose
   - تحسين استراتيجية التخزين المؤقت

## تطوير مستقبلي

### إمكانيات إضافية لـ Redis:
- **Pub/Sub**: للتواصل بين الخدمات في الوقت الفعلي
- **Redis Cluster**: للتوسع الأفقي
- **Redis Streams**: لمعالجة البيانات المتدفقة
- **Redis JSON**: لتخزين هياكل بيانات معقدة

### اقتراحات للتحسين:
- إضافة مراقبة مفصلة لمعدلات الإصابة في الذاكرة المؤقتة
- تنفيذ إستراتيجيات مختلفة للتخزين المؤقت حسب نوع البيانات
- إضافة ضغط البيانات لتوفير المساحة</content>
<parameter name="filePath">c:\Users\souha_gnrk8xo\Desktop\Projet_Fin_Annee-main\REDIS_GUIDE.md