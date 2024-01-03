import jwt
from datetime import datetime, timedelta, timezone #, UTC
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from app.models import APIToken
from app import db
import os

def generate_token(expiration_date: datetime, connection_name:str="Malldepot_central") -> str:
    """
        expiration_date (datetime): token expiration date
        connection_name (str, optional): Name for connection, descriptive purpose only Defaults to "Malldepot_central".

    Returns:
        str: JWT token
    """

    if not isinstance(expiration_date, datetime):
        print("wrong expiration date format!")
        # if expiration date was not a datetime object, return None
        return None
        # raise ValueError("Invalid expiration_date")

    # Set expiration to midnight (00:00:00) of the provided date
    # expiration_datetime = datetime.combine(expiration_date, datetime.min.time(), tzinfo=timezone.utc)

    # Ensure that the expiration date is in the future
    if expiration_date <= datetime.now(timezone.utc):
        print("expiration date in the past!")
        # if expiration date is not in the future, return None
        return None
        # raise ValueError("Expiration date must be in the future")

    payload = {
        'iss': current_app.config['APP_ID'],  # Issuer
        'aud': current_app.config['APP_ID'],  # Audience
        'exp': expiration_date,
        'iat': datetime.now(timezone.utc),
        # 'connection_name': connection_name
    }

    # Encode the token
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256') # .encode('utf-8') # .decode('utf-8')
    print("TOKEN: ", token)


    return token


def validate_token(token):
    """
    Token validator checks:
    - if the supplied API token is registered with the database,
    - if the token is not expired (using expiration date in the database and using 'exp' claim in the token),
    - if the token is not revoked (using revocation status in the database),
    - if the token was issued by and for the current application.

    Requires access to SECRET_KEY used to encode the API tokens issued.

    Args:
        token (str): API token to analyze.

    Returns:
        bool: True if the token is valid (all conditions are met), False otherwise.
    """
    os.environ['JWT_DECODE_DEBUG'] = 'False'
    
    print("*** TOKEN VALIDATOR ***")
    print("token received:", token)
    print("unverified header", jwt.get_unverified_header(token))
    print("secret key:", current_app.config['SECRET_KEY'])
    payload = jwt.decode(jwt=token, key=current_app.config['SECRET_KEY'], algorithms=['HS256'], options={"verify_signature": False})
    print("decoded payload", payload)
    print("----")
    try:
        payload = jwt.decode(jwt=token, key=current_app.config['SECRET_KEY'], 
                             algorithms=['HS256'], audience=current_app.config['APP_ID']) #, options={"verify_signature": False})

        api_token = APIToken.query.filter_by(token=token).first()
        if not api_token:
            print("--- token not found!")

        if not api_token or api_token.revoked:
            print("--- token revoked!")
            # token not found in the database or has been revoked.
            return False

        print("expires", api_token.expires_at)
        expires_at_utc = api_token.expires_at.replace(tzinfo=timezone.utc)
        if api_token.expires_at and expires_at_utc < datetime.now(timezone.utc):
            print("--- token expired!")
            # token has expired based on the records in the database
            return False

        app_id = current_app.config['APP_ID']
        if payload.get('iss') != app_id or payload.get('aud') != app_id:
            print("--- issued for a wrong app!")
            # token was not issued by or not issued for the current application
            return False

        # Token is valid
        return True

    except jwt.ExpiredSignatureError as e:
        print("-- expired signature exception!", e)
        # capture if the token has expired according to 'exp' claim
        return False

    except jwt.InvalidTokenError as e:
        print("--- invalid token exception!", e)
        return False

    return False

def get_claim_from_token(token, claim):
    """
    Args:
        token: JWT token to extract the claim from
        claim: Name of the claim to be extracted

    Returns:
        extracted claim or None if the claim was not present in the token, or other problem was encountered.
        NB, for 'exp','iat' and 'nbf' claims, a Python datetime object will be returned
    """
    try:
        # Decode the token
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        
        # Extract the specified claim
        claim_value = payload.get(claim)
        if claim_value is not None:
            # Special handling for 'iat', 'exp' or 'nbf' claims to convert to datetime
            if claim in ['iat', 'exp', 'nbf']:
                return datetime.utcfromtimestamp(claim_value)
            return claim_value
        else:
            return None

    except Exception as e:
        print("exception when getting claim", e)
        # Return None if there are any issues with the token.
        return None
    