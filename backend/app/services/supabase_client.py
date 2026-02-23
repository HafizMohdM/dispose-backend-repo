import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the .env file")

# The client uses the service role key to ensure we have permission
# to upload/delete files in the 'media' bucket without RLS policies getting in the way.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
