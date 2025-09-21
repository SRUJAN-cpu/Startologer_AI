import os
from routes.initialEndpoints import app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "5000"))
    print(f"Starting Flask server on 0.0.0.0:{port}")
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
