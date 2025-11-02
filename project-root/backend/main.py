import os
import sys

# Disable Python bytecode caching to ensure code changes are always loaded
sys.dont_write_bytecode = True

from routes.initialEndpoints import app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "5000"))
    print(f"Starting Flask server on 0.0.0.0:{port}")
    # Disable reloader to prevent infinite restart loops caused by file changes
    # You can still use debug=True for better error messages without auto-reload
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True, use_reloader=False)
