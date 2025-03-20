import logging
import json
from models.user import User

logger = logging.getLogger(__name__)

def get_user_profile_dict(user_id: int) -> dict:
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User with ID {user_id} not found.")
        return {}

    profile = user.to_dict()

    if isinstance(profile.get('skills'), str):
        try:
            profile['skills'] = json.loads(profile['skills'])
        except:
            profile['skills'] = [s.strip() for s in profile['skills'].split(',')]

    if isinstance(profile.get('experience'), str):
        profile['experience'] = profile['experience']

    logger.info(f"Loaded profile for user {user.email}")
    return profile

def get_user_email(user_id: int) -> str:
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User with ID {user_id} not found.")
        return ""
    return user.email