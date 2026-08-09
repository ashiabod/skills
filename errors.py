from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    @app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify({
            "error": "Bad Request",
            "message": str(error.description if hasattr(error, 'description') else "Invalid request parameters"),
            "status": 400
        }), 400

    @app.errorhandler(401)
    def handle_unauthorized(error):
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication required or token invalid/expired",
            "status": 401
        }), 401

    @app.errorhandler(403)
    def handle_forbidden(error):
        return jsonify({
            "error": "Forbidden",
            "message": "You do not have permission to access this resource",
            "status": 403
        }), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource or page was not found",
            "status": 404
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            "error": "Method Not Allowed",
            "message": "The HTTP method is not allowed for this endpoint",
            "status": 405
        }), 405

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server",
            "status": 500
        }), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        return jsonify({
            "error": "Database Error",
            "message": "A database exception occurred while processing your request",
            "status": 500
        }), 500

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return jsonify({
            "error": "Value Error",
            "message": str(error),
            "status": 400
        }), 400

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        if isinstance(error, HTTPException):
            return jsonify({
                "error": error.name,
                "message": error.description,
                "status": error.code
            }), error.code
            
        return jsonify({
            "error": "Server Error",
            "message": "An unhandled error occurred",
            "details": str(error),
            "status": 500
        }), 500