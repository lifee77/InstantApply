

import logging
from models.job_recommendation import JobRecommendation
from models.user import User
from flask import current_app

logger = logging.getLogger(__name__)


def get_user_by_id(user_id: int) -> User:
    """
    Retrieve a user by their ID from the database.
    
    Args:
        user_id: The ID of the user
    
    Returns:
        User object or None if not found
    """
    from models.user import db
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User with ID {user_id} not found.")
    return user


def get_job_recommendations_for_user(user: User, min_score: int = 0) -> list:
    """
    Fetch job recommendations for a user, optionally filtered by match score.
    
    Args:
        user: The user object
        min_score: Minimum match score to filter jobs
    
    Returns:
        List of JobRecommendation objects
    """
    query = JobRecommendation.query.filter_by(user_id=user.id)
    if min_score > 0:
        query = query.filter(JobRecommendation.match_score >= min_score)
    jobs = query.all()
    logger.info(f"Found {len(jobs)} job recommendations for user {user.email} with min score {min_score}")
    return jobs


def get_job_links_for_user(user: User, min_score: int = 0) -> list:
    """
    Retrieve only job URLs for a user’s job recommendations.
    
    Args:
        user: The user object
        min_score: Minimum match score to filter jobs
    
    Returns:
        List of job URLs
    """
    jobs = get_job_recommendations_for_user(user, min_score)
    return [job.url for job in jobs]