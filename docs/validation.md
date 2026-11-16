# گزارش Build، Test و Validation

اجرا در ۲۰۲۶-۱۱-۱۶ روی Linux با Python 3.12.14.

```text
$ python -m compileall -q changeflow tests

Exit status: 0
```

```text
$ python -m unittest discover -s tests -v
test_approved_cannot_be_edited_even_with_current_version (test_api.ChangeFlowTests.test_approved_cannot_be_edited_even_with_current_version) ... ok
test_auth_ownership_and_read_visibility (test_api.ChangeFlowTests.test_auth_ownership_and_read_visibility) ... ok
test_competing_review_actions_only_commit_one_transition (test_api.ChangeFlowTests.test_competing_review_actions_only_commit_one_transition) ... ok
test_create_draft (test_api.ChangeFlowTests.test_create_draft) ... ok
test_independent_reviewer_can_approve (test_api.ChangeFlowTests.test_independent_reviewer_can_approve) ... ok
test_return_edit_resubmit_and_reject_old_review (test_api.ChangeFlowTests.test_return_edit_resubmit_and_reject_old_review) ... ok
test_self_approval_rejected_for_user_with_both_roles (test_api.ChangeFlowTests.test_self_approval_rejected_for_user_with_both_roles) ... ok
test_stale_edit_does_not_overwrite (test_api.ChangeFlowTests.test_stale_edit_does_not_overwrite) ... ok
test_submit_draft (test_api.ChangeFlowTests.test_submit_draft) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.135s

OK
Exit status: 0
```

Compileall همهٔ فایل‌های Python در دو پوشه را بررسی کرد. این پروژه مرحلهٔ بسته‌بندی مستقل ندارد. ۹ آزمون HTTP روی پایگاه‌های SQLite موقت اجرا و موفق شدند.

## اجرای مسیر عادی

```text
$ python -m changeflow --db <temp>/smoke.sqlite3 --port 0
ChangeFlow listening at http://127.0.0.1:35235
POST /requests (demo-owner) -> 201 Draft
POST /requests/1/submit (demo-owner) -> 200 PendingReview
POST /requests/1/approve (demo-owner) -> 403 Forbidden
POST /requests/1/approve (demo-reviewer) -> 200 Approved
SQLite record after server stop: ('Approved', 3)
```

## ردیابی معیارهای پذیرش

| معیار | آزمون یا شاهد |
|---|---|
| AC-01 | test_create_draft |
| AC-02 | test_submit_draft، test_stale_edit_does_not_overwrite، test_auth_ownership_and_read_visibility |
| AC-03 | test_self_approval_rejected_for_user_with_both_roles |
| AC-04 | test_independent_reviewer_can_approve، test_approved_cannot_be_edited_even_with_current_version |
| AC-05 | test_return_edit_resubmit_and_reject_old_review |
| AC-06 | test_stale_edit_does_not_overwrite، test_competing_review_actions_only_commit_one_transition |
| AC-07، AC-08 | test_auth_ownership_and_read_visibility |

مرز API و لایهٔ کاربرد و نبود تغییر داده پس از پاسخ‌های ناموفق در بررسی فنی تأیید شد. پذیرش انسانی در انتظار ارزیاب تمرین است.
