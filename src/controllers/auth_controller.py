from flask import request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from src.utils.response import success_response, error_response
from src.repositories.user_repo import UserRepository
from src.utils.errors import APIError

def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    user = UserRepository.get_by_email(email)
    if user and user.check_password(password):
        # Create standard short-lived Access and long-lived Refresh tokens
        access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role or "user"})
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return success_response(data={
            'access_token': access_token, 
            'refresh_token': refresh_token,
            'user_id': user.id,
            'role': user.role or "user"
        }, message="Login successful - Production Session Secured")
    
    return error_response(message="Identities do not match our secure baseline.", status_code=401)

def register():
    # Production Registration with automatic role assignment
    data = request.json
    try:
        if UserRepository.get_by_email(data.get('email')):
            return error_response(message="Identity already exists.")
            
        # Defaulting all first-time registrations to 'user' role
        data['role'] = 'user'
        user = UserRepository.create(data)
        
        access_token = create_access_token(identity=str(user.id), additional_claims={"role": "user"})
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return success_response(data={
            'access_token': access_token, 
            'refresh_token': refresh_token
        }, message="Security profile established.")
    except Exception as e:
        raise APIError(str(e))

@jwt_required(refresh=True)
def refresh_token():
    # Broker new access tokens using valid refresh tokens
    current_user = get_jwt_identity()
    new_token = create_access_token(identity=current_user)
    return success_response(data={'access_token': new_token}, message="Session Extended")
