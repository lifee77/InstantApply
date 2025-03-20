

import logging
from application_filler.base_filler import BaseApplicationFiller
from playwright.async_api import async_playwright
import asyncio

logger = logging.getLogger(__name__)

class AutoApplicationFiller(BaseApplicationFiller):
    async def map_question_to_response(self, question):
        import json
        q_lower = question['text'].lower()
        user_data = {
            "biggest_achievement": self.user.biggest_achievement,
            "career_goals": self.user.career_goals,
            "experience": self.user.experience,
            "skills": json.loads(self.user.skills) if self.user.skills else [],
            "needs_sponsorship": self.user.needs_sponsorship,
            "willing_to_relocate": self.user.willing_to_relocate,
            "available_start_date": str(self.user.available_start_date) if self.user.available_start_date else None
        }

        if any(phrase in q_lower for phrase in ["greatest strength", "strengths", "top strength", "biggest strength", "key strength"]):
            return (question['text'], user_data.get('biggest_achievement', 'I am a quick learner.'))
        elif any(phrase in q_lower for phrase in ["career goal", "career ambition", "long-term goal", "short-term goal", "where do you see yourself"]):
            return (question['text'], user_data.get('career_goals', 'I want to grow professionally.'))
        elif any(phrase in q_lower for phrase in ["experience", "work history", "previous roles", "professional background", "your background"]):
            return (question['text'], user_data.get('experience', 'I have relevant experience in my field.'))
        elif any(phrase in q_lower for phrase in ["skills", "core competencies", "technical skills", "expertise", "areas of expertise"]):
            skills = user_data.get('skills')
            if isinstance(skills, list):
                skills_str = ", ".join(skills) if skills else 'Python, Communication'
            else:
                skills_str = skills or 'Python, Communication'
            return (question['text'], skills_str)
        elif any(phrase in q_lower for phrase in ["authorization", "visa sponsorship", "sponsorship", "work authorization", "need sponsorship"]):
            return (question['text'], "Yes" if not user_data.get('needs_sponsorship') else "No")
        elif any(phrase in q_lower for phrase in ["relocate", "willing to move", "open to relocation", "consider relocation", "change location"]):
            return (question['text'], "Yes" if user_data.get('willing_to_relocate') else "No")
        elif any(phrase in q_lower for phrase in ["start date", "availability date", "when can you start", "available to start", "available start date"]):
            return (question['text'], str(user_data.get('available_start_date') or "2025-03-25"))
        else:
            return (question['text'], "I am excited about this opportunity.")

    async def fill_application(self, browser_context=None):
        logger.info(f"Starting application fill for job URL: {self.job_url}")
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=False)
            context = browser_context or await browser.new_context()
            page = await context.new_page()
            logger.info(f"Navigating to {self.job_url}")
            await page.goto(self.job_url)
            await self.fill_application_form(page)
            await self.handle_resume_upload(page)
            # Delay before closing to ensure all operations complete
            await asyncio.sleep(5)
            await browser.close()
            logger.info(f"Finished application fill for job URL: {self.job_url}")
            return {"status": "completed", "job_url": self.job_url}
        
    
    # Removed duplicate fill_application method