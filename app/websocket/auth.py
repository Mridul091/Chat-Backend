from app.services.auth import decode_access_token


async def ws_authenticate(token: str | None):
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    return user_id
