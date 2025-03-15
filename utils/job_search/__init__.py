# Package initialization file

# Import and expose the search_jobs function
from .job_search import search_jobs, search_jobs_mock
from .job_submitter import submit_application, submit_application_async

# Make these functions available when importing from utils.job_search
__all__ = ['search_jobs', 'search_jobs_mock', 'submit_application', 'submit_application_async']
