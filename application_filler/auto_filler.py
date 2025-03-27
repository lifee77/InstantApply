from application_filler.utils.click_utils import click_accept_or_apply_buttons, scroll_and_click, scroll_and_click_dropdowns_and_modals
from application_filler.utils.date_utils import handle_date_picker
from application_filler.utils.radio_utils import handle_visa_questions, handle_radio_groups
from application_filler.utils.verification_utils import review_form_entries
from application_filler.utils.test_mode_utils import enable_test_mode, disable_test_mode
from application_filler.base_filler import BaseApplicationFiller
import logging
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
        """Fill the application form using enhanced utilities for handling various form elements."""
        logger.info("Filling application form using user profile data...")
        
        # First, handle standard fields
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
 
                    # Map common field types to user data
                    user_data = self.user
                    
                    # Use try/except with getattr to avoid AttributeError for missing fields
                    try:
                        # Fill based on field hints
                        if input_type == 'date' or 'date' in name.lower() or 'date' in placeholder.lower():
                            value = getattr(user_data, 'available_start_date', None)
                            if value is not None:
                                await input_field.fill(str(value))
                                logger.info(f"Filled date field with: {value}")
                        elif 'name' in name.lower() or 'name' in placeholder.lower():
                            value = getattr(user_data, 'name', None)
                            if value:
                                await input_field.fill(value)
                                logger.info(f"Filled name field with: {value}")
                        elif 'email' in name.lower() or 'email' in placeholder.lower():
                            value = getattr(user_data, 'email', None)
                            if value:
                                await input_field.fill(value)
                                logger.info(f"Filled email field with: {value}")
                        elif 'phone' in name.lower() or 'phone' in placeholder.lower():
                            value = getattr(user_data, 'phone', None)
                            if value:
                                await input_field.fill(value)
                                logger.info(f"Filled phone field with: {value}")
                        elif 'location' in name.lower() or 'city' in name.lower() or 'location' in placeholder.lower():
                            value = getattr(user_data, 'location', None)
                            if value:
                                await input_field.fill(value)
                                logger.info(f"Filled location field with: {value}")
                        elif 'linkedin' in name.lower() or 'linkedin' in placeholder.lower():
                            value = getattr(user_data, 'linkedin_url', None)
                            if value:
                                await input_field.fill(value)
                                logger.info(f"Filled LinkedIn field with: {value}")
                        elif 'github' in name.lower() or 'github' in placeholder.lower():
                            value = getattr(user_data, 'github_url', None)
                            if value:
                                await input_field.fill(value)
                                logger.info(f"Filled GitHub field with: {value}")
                        elif 'portfolio' in name.lower() or 'website' in name.lower() or 'site' in name.lower():
                            value = getattr(user_data, 'website_url', None)
                            if value:
                                await input_field.fill(value)
                                logger.info(f"Filled website field with: {value}")
                        else:
                            # Fallback: use the Gemini API for responses not covered above.
                            response = await self.fetch_gemini_response(placeholder or name)
                            if response:
                                await input_field.fill(response)
                                logger.info(f"Filled field {name or placeholder} using Gemini API with: {response}")
                    except Exception as e:
                        logger.warning(f"Error filling field {name or placeholder}: {str(e)}")
                    # Press Tab to move to next field
                    await input_field.press("Tab")
                    await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logger.warning(f"Error processing field {i+1}: {str(e)}")
        
        # Handle additional elements like date pickers and yes/no questions
        await self.handle_date_pickers(page)
        await self.handle_yes_no_questions(page)
        await self.handle_radio_groups(page)
        
        # Review what we've entered
        await review_form_entries(page)
        
        # Continue with handling next/continue buttons
        await scroll_and_click_dropdowns_and_modals(page)
        
        return True
    

    async def fill_application(self, browser_context=None):
        """Main method to fill an application, including browser management."""
        logger.info(f"Starting application fill for job URL: {self.job_url}")
        if not browser_context:
            raise ValueError("browser_context is required")

        page = await browser_context.new_page()
        logger.info(f"Navigating to {self.job_url}")
        
        # Apply test mode to prevent actual submission
        await enable_test_mode(page)
        
        try:
            await page.goto(self.job_url)
            await click_accept_or_apply_buttons(page)
            # scroll_and_click now handles scrolling into view before clicking, including modals and popups
            await scroll_and_click(page, 'button:has-text("Apply")')
            # Handle the application form
            await self.fill_application_form(page)
            await self.handle_resume_upload(page)
            
            # Final review
            await review_form_entries(page)
            
            # Wait for visual inspection if needed
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Error filling application: {str(e)}")
        finally:
            # Before closing, disable test mode if we're ready for real submissions
            # Uncomment this when ready for actual submissions:
            # await disable_test_mode(page)
            await page.close()
            
        logger.info(f"Finished application fill for job URL: {self.job_url}")
        return {"status": "completed", "job_url": self.job_url}