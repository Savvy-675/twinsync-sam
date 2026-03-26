from flask import jsonify

def success_response(data=None, message="Success", status_code=200):
    return jsonify({
        "success": True,
        "data": data if data is not None else {},
        "message": message
    }), status_code

def error_response(message="An error occurred", status_code=400):
    return jsonify({
        "success": False,
        "data": {},
        "message": message
    }), status_code
