import os
import uvicorn
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    uvicorn.run('curalync_backend.asgi:application', host='0.0.0.0', port=port, reload=False)
