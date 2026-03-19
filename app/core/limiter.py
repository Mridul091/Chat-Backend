from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize the limiter
# By default, it will track quotas based on the user's IP Address
limiter = Limiter(key_func=get_remote_address)
