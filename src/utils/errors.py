from flask import jsonify
from werkzeug.exceptions import HTTPException

def handle_exception(e):
    # Pass through HTTP errors
    if isinstance(e, HTTPException):
        return jsonify({
            "success": False,
            "error": e.description,
            "code": e.code
        }), e.code

    # Handle non-HTTP exceptions (unexpected errors)
    return jsonify({
        "success": False,
        "error": str(e),
        "code": 500
    }), 500

class APIError(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code
