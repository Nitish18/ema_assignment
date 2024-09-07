from google.oauth2.credentials import Credentials
from auth_service.models import UserCredentials
import requests


def get_credentials_from_user_credentials(user_credentials):
    """
    Reconstructs the Google API credentials from the stored user credentials.
    """
    return Credentials(
        token=user_credentials.token,
        refresh_token=user_credentials.refresh_token,
        token_uri=user_credentials.token_uri,
        client_id=user_credentials.client_id,
        client_secret=user_credentials.client_secret,
        scopes=user_credentials.scopes.split(' ')
    )


def get_credentials_from_user_id(user_id):
    """
    Fetches the user credentials from the database using the user ID.
    """
    user_credentials = UserCredentials.objects.get(user_id=user_id)
    return get_credentials_from_user_credentials(user_credentials)

def revoke_token(token):
    """
    Revoke the given OAuth token (access or refresh).
    """
    revoke_url = 'https://oauth2.googleapis.com/revoke'
    params = {'token': token}

    response = requests.post(revoke_url, params=params, headers={'content-type': 'application/x-www-form-urlencoded'})

    if response.status_code == 200:
        print("Token successfully revoked")
    else:
        print(f"Failed to revoke token: {response.content}")

    return response.status_code

