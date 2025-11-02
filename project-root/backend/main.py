import os
import sys

# Disable Python bytecode caching to ensure code changes are always loaded
sys.dont_write_bytecode = True

from routes.initialEndpoints import app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug, host='0.0.0.0', port=port, threaded=True)
