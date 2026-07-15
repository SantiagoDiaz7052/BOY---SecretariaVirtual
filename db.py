import os
from supabase import create_client

_url = os.getenv("SUPABASE_URL", "")
_key = os.getenv("SUPABASE_KEY", "")

supabase = create_client(_url, _key) if _url and _key else None
