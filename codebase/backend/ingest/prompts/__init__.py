from .enrich_v1 import ENRICH_V1
from .schedule_v1 import SCHEDULE_V1

PROMPT_VERSION = "v1"
PROMPTS = {"v1": ENRICH_V1}  # thêm enrich_v2.py thì đăng ký vào đây

SCHEDULE_VERSION = "v1"
SCHEDULE_PROMPTS = {"v1": SCHEDULE_V1}  # thêm schedule_v2.py thì đăng ký vào đây
