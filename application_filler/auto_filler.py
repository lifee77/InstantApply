from application_filler.utils.click_utils import click_accept_or_apply_buttons, scroll_and_click


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

    async def fill_application_form(self, page):
        logger.info("Filling application form using user profile data...")
 
        user_data = {
            "name": self.user.name if hasattr(self.user, 'name') else "John Doe",
            "email": self.user.email if hasattr(self.user, 'email') else "john.doe@example.com",
            "phone": self.user.phone if hasattr(self.user, 'phone') else "555-123-4567",
            "location": self.user.location if hasattr(self.user, 'location') else "New York, NY",
            "available_start_date": str(self.user.available_start_date) if hasattr(self.user, 'available_start_date') else "2025-03-25",
            "skills": self.user.skills if hasattr(self.user, 'skills') else "Python, Communication",
            "experience": self.user.experience if hasattr(self.user, 'experience') else "I have relevant experience."
        }
 
        try:
            input_fields = await page.query_selector_all('input:visible, textarea:visible, select:visible')
            if input_fields:
                logger.info(f"Found {len(input_fields)} visible input fields")
 
                for i, input_field in enumerate(input_fields):
                    try:
                        input_type = await input_field.get_attribute('type') or 'text'
                        if input_type == 'file':
                            continue
                        placeholder = await input_field.get_attribute('placeholder') or ''
                        name = await input_field.get_attribute('name') or ''
                        id_attr = await input_field.get_attribute('id') or ''
                        is_visible = await input_field.is_visible()
                        if not is_visible:
                            continue
                        await page.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})", input_field)
                        await input_field.focus()
                        await asyncio.sleep(0.5)
 
                        # Fill based on hints
                        if 'name' in name.lower() or 'name' in placeholder.lower():
                            await input_field.fill(user_data["name"])
                        elif 'email' in name.lower() or 'email' in placeholder.lower():
                            await input_field.fill(user_data["email"])
                        elif 'phone' in name.lower() or 'phone' in placeholder.lower():
                            await input_field.fill(user_data["phone"])
                        elif 'location' in name.lower() or 'location' in placeholder.lower():
                            await input_field.fill(user_data["location"])
                        elif 'date' in name.lower() or 'date' in placeholder.lower() or 'start' in name.lower():
                            await input_field.fill(user_data["available_start_date"])
                        elif 'skills' in name.lower():
                            await input_field.fill(user_data["skills"])
                        elif 'experience' in name.lower():
                            await input_field.fill(user_data["experience"])
                        else:
                            await input_field.fill("N/A")
                        await input_field.press("Tab")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error interacting with field {i+1}: {str(e)}")
            else:
                logger.info("No visible input fields found on the page")
 
            logger.info("Finished filling out input fields based on user profile.")
            return True
 
        except Exception as e:
            logger.error(f"Error during form filling: {str(e)}")
            return False

    async def fill_application(self, browser_context=None):
        logger.info(f"Starting application fill for job URL: {self.job_url}")
        if not browser_context:
            raise ValueError("browser_context is required")

        page = await browser_context.new_page()
        logger.info(f"Navigating to {self.job_url}")
        await page.goto(self.job_url)
        await click_accept_or_apply_buttons(page)
        # scroll_and_click now handles scrolling into view before clicking, including modals and popups
        await scroll_and_click(page, 'button:has-text("Apply")')
        # Base filler now handles form field detection and apply button logic externally.
        await self.fill_application_form(page)
        await self.handle_resume_upload(page)
        await asyncio.sleep(5)
        await page.close()
        logger.info(f"Finished application fill for job URL: {self.job_url}")
        return {"status": "completed", "job_url": self.job_url}
        
    
    # Removed duplicate fill_application method