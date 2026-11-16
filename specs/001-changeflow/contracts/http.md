# قرارداد HTTP

همهٔ مسیرها به `Authorization: Bearer <token>` نیاز دارند. بدنهٔ عملیات نوشتن JSON است.

| روش و مسیر | بدنه | موفق | مجوز |
|---|---|---|---|
| POST /requests | title, description, reason | 201 و Location | Requester |
| GET /requests/{id} | — | 200 | مالک دارای Requester یا Reviewer برای وضعیت‌های خارج از Draft |
| PUT /requests/{id} | title, description, reason, version | 200 | مالک دارای Requester در Draft یا ChangesRequested |
| POST /requests/{id}/submit | version | 200 | مالک دارای Requester در Draft یا ChangesRequested |
| POST /requests/{id}/approve | version | 200 | Reviewer مستقل در PendingReview |
| POST /requests/{id}/request-changes | version | 200 | Reviewer در PendingReview |

موفقیت، رکورد کامل را برمی‌گرداند. نمونهٔ پاسخ ثبت

```json
{"id":1,"requesterId":"analyst","title":"API change","description":"Update response fields","reason":"Display branch title","status":"Draft","version":1}
```

خطاهای قراردادی بدنهٔ `{"error":"message"}` دارند. 400 برای بدنهٔ نامعتبر، 401 برای نبود هویت معتبر، 403 برای منع دسترسی، 404 برای شناسه یا مسیر ناموجود، 409 برای نسخه یا وضعیت ناسازگار، 415 برای نوع محتوای نامعتبر و 503 همراه Retry-After برای اشغال ماندن پایگاه است. پس از 409 نسخهٔ جاری را دوباره بخوانید و پیش از تلاش مجدد، اعتبار اقدام را روی دادهٔ جدید بررسی کنید.
