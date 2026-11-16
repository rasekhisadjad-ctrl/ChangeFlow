# مدل داده

| فیلد | نوع SQLite | معنی و قید |
|---|---|---|
| id | INTEGER PRIMARY KEY | شناسهٔ عمومی درخواست |
| requesterId | TEXT NOT NULL | شناسهٔ ثابت ثبت‌کننده از پیکربندی هویت |
| title | TEXT NOT NULL | عنوان |
| description | TEXT NOT NULL | شرح تغییر |
| reason | TEXT NOT NULL | دلیل تغییر |
| status | TEXT NOT NULL | یکی از Draft، PendingReview، ChangesRequested و Approved |
| version | INTEGER NOT NULL | از ۱ شروع می‌شود و هر ویرایش یا انتقال موفق یک واحد به آن اضافه می‌کند |

Draft و ChangesRequested قابل ویرایش هستند و Submit آن‌ها را به PendingReview می‌برد. PendingReview ثابت است و فقط دو مسیر خروج دارد. Approved خروجی ندارد. حذف و تاریخچه در محدوده نیستند. نقش‌ها در پایگاه ذخیره نمی‌شوند.
