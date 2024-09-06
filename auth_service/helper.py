from google.oauth2.credentials import Credentials

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
