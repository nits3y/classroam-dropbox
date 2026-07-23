from app import create_app
from app.exams import view_attempt_detail
import traceback

app = create_app()
with app.test_request_context('/admin/exams/attempts/75'):
    try:
        resp = view_attempt_detail(75)
        print('OK, response type:', type(resp))
        if hasattr(resp, 'get_data'):
            print(resp.get_data(as_text=True)[:2000])
    except Exception:
        traceback.print_exc()
