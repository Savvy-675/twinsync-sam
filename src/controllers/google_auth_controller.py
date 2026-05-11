import json
import logging
from flask import request, redirect, url_for, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from google_auth_oauthlib.flow import Flow
from src.config.config import Config
from src.repositories.user_repo import UserRepository
from src.utils.response import success_response, error_response
from src.config.db import db

logger = logging.getLogger('GoogleAuthController')

# Scopes needed for Gmail read access
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

def get_google_flow(state=None):
    client_config = {
        "web": {
            "client_id": Config.GOOGLE_CLIENT_ID,
            "client_secret": Config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [Config.GOOGLE_REDIRECT_URI]
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
    return flow

@jwt_required()
def google_authorize():
    """Step 1: Get Google Auth URL and return it to frontend or redirect."""
    user_id = get_jwt_identity()
    
    if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET:
        return error_response("Google OAuth credentials are not configured in .env", 500)

    flow = get_google_flow()
    
    # Generate authorization URL
    # Include user_id in state to retrieve it during callback (or use session)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=json.dumps({"user_id": user_id})
    )
    
    return success_response(data={"auth_url": authorization_url}, message="Authorization URL generated.")

def google_callback():
    """Step 2: Handle Google Redirect, exchange code for tokens."""
    state_raw = request.args.get('state')
    code = request.args.get('code')
    
    if not state_raw or not code:
        return error_response("Missing state or code in Google callback.", 400)
    
    try:
        state = json.loads(state_raw)
        user_id = state.get('user_id')
        
        flow = get_google_flow(state=state_raw)
        flow.fetch_token(authorization_response=request.url)
        
        credentials = flow.credentials
        
        user = UserRepository.get_by_id(user_id)
        if not user:
            return error_response("User not found during Google callback.", 404)
        
        # Save tokens
        user.google_token = credentials.token
        if credentials.refresh_token:
            user.google_refresh_token = credentials.refresh_token
            
        db.session.commit()
        
        # Redirect back to the frontend app
        # Frontend should check profile to see if Google is linked
        return redirect(Config.GOOGLE_REDIRECT_URI.replace('/api/auth/google/callback', '/?google_linked=true'))
        
    except Exception as e:
        logger.error(f"Google OAuth Callback Failed: {e}")
        return error_response(f"Google authentication failed: {str(e)}", 500)
