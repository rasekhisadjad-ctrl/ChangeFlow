# ChangeFlow

نمونهٔ جلسهٔ اول SDD برای ثبت، بررسی و تأیید درخواست تغییر. API با Python 3.12، کتابخانهٔ استاندارد و SQLite اجرا می‌شود. SQLite داده‌ها را در فایل نگه می‌دارد. نصب بستهٔ اضافی برای اجرای API لازم نیست.

## اجرا

نمونهٔ زیر برای Bash است. مقادیر توکن فقط برای تمرین محلی هستند. هر کاربر یک شناسهٔ پایدار و مجموعه‌ای از نقش‌ها دارد.

```bash
export CHANGEFLOW_IDENTITIES='{"demo-owner":{"id":"analyst","roles":["Requester","Reviewer"]},"demo-reviewer":{"id":"reviewer","roles":["Reviewer"]}}'
python -m changeflow --db changeflow.sqlite3 --port 8000
```

در ترمینال دوم، روی پایگاه تازه ابتدا درخواست ثبت کنید. اگر شناسهٔ پاسخ ۱ نیست، شماره را در مسیرهای بعدی جایگزین کنید. نسخه‌ها را از پاسخ عملیات قبل بردارید.

```bash
curl -sS http://127.0.0.1:8000/requests \
  -H 'Authorization: Bearer demo-owner' -H 'Content-Type: application/json' \
  -d '{"title":"Add account title","description":"Return accountTitle in the API response","reason":"Show account title to branch users"}'

curl -sS http://127.0.0.1:8000/requests/1/submit \
  -H 'Authorization: Bearer demo-owner' -H 'Content-Type: application/json' -d '{"version":1}'

curl -sS -i http://127.0.0.1:8000/requests/1/approve \
  -H 'Authorization: Bearer demo-owner' -H 'Content-Type: application/json' -d '{"version":2}'

curl -sS http://127.0.0.1:8000/requests/1/approve \
  -H 'Authorization: Bearer demo-reviewer' -H 'Content-Type: application/json' -d '{"version":2}'
```

انتظار می‌رود ثبت به Draft، ارسال به PendingReview، تلاش مالک برای تأیید به 403 و تأیید Reviewer مستقل به Approved منتهی شود.

## بررسی فنی

```bash
python -m compileall -q changeflow tests
python -m unittest discover -s tests -v
```

API مسئول احراز هویت و تبادل HTTP است. قواعد مالکیت، وضعیت و نسخه در ماژول کاربرد بررسی می‌شوند. هر تغییر در تراکنش SQLite انجام می‌شود و نسخهٔ رکورد یک واحد بالا می‌رود. نسخهٔ قدیمی پاسخ 409 می‌گیرد.

این سرور برای اجرای محلی روی loopback پیکربندی شده است. تغییر توکن یا نقش با راه‌اندازی مجدد اعمال می‌شود. ثبت مجدد همان محتوا رکورد تازه می‌سازد. عملیات فهرست، حذف، رابط کاربری و اجرای تغییر تأییدشده بیرون از محدوده‌اند.

## مراحل و شواهد

پروژه با GitHub Spec Kit 1.4.0 و ادغام Codex آماده شد. فرمان Init اجراشده در پوشهٔ والد

```bash
uv tool run --from specify-cli==1.4.0 specify init ChangeFlow --integration codex --script sh --ignore-agent-tools
```

Codex در همین جلسه اسناد، پیاده‌سازی و آزمون‌ها را تولید و بازبینی کرد. فرض‌های تکمیلی محصول در Clarifications ثبت شده‌اند و تصمیم رسمی مالک محصول دربارهٔ آن‌ها هنوز ثبت نشده است.

| مورد | سند |
|---|---|
| اصول معماری و کیفیت | [Constitution](.specify/memory/constitution.md) |
| قواعد، سناریوها و فرض‌ها | [Spec و Clarifications](specs/001-changeflow/spec.md) |
| معماری و تصمیم‌های فنی | [Plan](specs/001-changeflow/plan.md) · [Research](specs/001-changeflow/research.md) · [مدل داده](specs/001-changeflow/data-model.md) · [قرارداد API](specs/001-changeflow/contracts/http.md) |
| وظایف و وابستگی‌ها | [Tasks](specs/001-changeflow/tasks.md) |
| یافته‌های پیش از تحویل | [Analyze](docs/analyze.md) · [Converge](docs/converge.md) |
| شواهد اجرا و وضعیت پذیرش | [Build و Test و Validation](docs/validation.md) |
| پاسخ پرسش‌های تشریحی | [پاسخ‌های جلسهٔ اول](docs/answers/session-01.md) |
