async def process_application_page(page: Page, user_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a job application page - uploading resume, filling form, and submitting
    
    Args:
        page: Playwright page object
        user_data: Dictionary with user profile information
        config: Configuration options
        
    Returns:
        Dictionary with results of the application attempt
    """
    logger.info(f"Processing application for URL: {page.url}")
    
    # Take a screenshot of the initial page
    await save_full_page_screenshot(page, "before_processing")
    
    # Initialize response generator for answering questions
    response_generator = ResponseGenerator(user_data)
    
    # Initialize the form filler
    form_filler = FormFiller(response_generator)
    
    # Track completion status
    fields_completion = {
        "resume_uploaded": False,
        "basic_fields_filled": False,
        "questions_filled": False,
        "total_fields_processed": 0,
        "fields_successfully_filled": 0
    }
    
    # Step 1: Detect form type to customize handling
    form_type, form_metadata = await detect_and_handle_form_type(page)
    logger.info(f"Detected form type: {form_type}")
    
    # Step 2: PRIORITY - Upload the resume first (it may auto-fill other fields)
    if "resume_file_path" in user_data:
        logger.info("Prioritizing resume upload first")
        fields_completion["resume_uploaded"] = await prioritize_resume_upload(
            page, 
            user_data.get("resume_file_path", "")
        )
        # Add a delay after resume upload to allow for autofill
        await asyncio.sleep(5)
    else:
        logger.warning("No resume file path provided in user data")
    
    # Step 3: Fill basic fields (name, email, phone)
    logger.info("Filling basic identification fields")
    fields_completion["basic_fields_filled"] = await form_filler.fill_basic_fields(page, user_data)
    
    # Step 4: Parse and fill the application questions
    logger.info("Parsing application questions")
    questions = await form_filler.parse_application_page(page)
    
    # If we found questions, fill them
    if questions:
        logger.info(f"Filling {len(questions)} application questions")
        for i, question in enumerate(questions):
            logger.info(f"Processing question {i+1}/{len(questions)}: {question['text']}")
            
            # Generate response for this question
            response = response_generator.generate_response(question["text"])
            fields_completion["total_fields_processed"] += 1
            
            # Fill the question field
            success = await form_filler.fill_application_field(page, question, response)
            if success:
                fields_completion["fields_successfully_filled"] += 1
        
        # Check if we filled at least some questions successfully
        fields_completion["questions_filled"] = fields_completion["fields_successfully_filled"] > 0
    else:
        logger.warning("No questions found to fill")
    
    # Take screenshot after filling form
    await save_full_page_screenshot(page, "after_filling")
    
    # If this is a multi-step form, look for and click the next/continue button
    # We'll only do this if we have completed enough of the form
    form_completion_rate = fields_completion["fields_successfully_filled"] / max(1, fields_completion["total_fields_processed"])
    
    # Check overall form completion status
    is_form_sufficiently_filled = (
        (fields_completion["resume_uploaded"] or fields_completion["basic_fields_filled"]) and
        (form_completion_rate >= 0.5 or fields_completion["fields_successfully_filled"] >= 5)
    )
    
    # Step 5: Wait several seconds before attempting to submit to ensure all validations have run
    if is_form_sufficiently_filled:
        logger.info("Form is sufficiently completed. Waiting before proceeding...")
        await asyncio.sleep(5)  # Generous wait to allow for form validations
        
        # Check for any validation errors that appeared after filling
        validation_errors = await check_form_validation_errors(page)
        
        if validation_errors > 0:
            logger.warning(f"Found {validation_errors} validation errors after filling form. Trying to fix...")
            # TODO: Add logic to fix validation errors - e.g. required fields
            # This could be complex, so just log for now
        
        # Only attempt to submit if we're satisfied with form completion
        if form_metadata.get("is_multi_step", False):
            # For multi-step forms, find and click the Next/Continue button
            next_button = await find_next_button(page)
            if next_button:
                logger.info("Found Next/Continue button. Clicking...")
                await next_button.click()
                await page.wait_for_load_state("networkidle", timeout=5000)
                
                # Process next page if needed
                # await process_application_page(page, user_data, config) # Uncomment for recursive handling
            else:
                logger.info("No Next button found. Trying submit...")
                # If no next button, try submit directly
                await find_and_click_submit_button(page)
        else:
            # For single-page forms, try to submit directly
            logger.info("Single-page form detected. Attempting submission...")
            await find_and_click_submit_button(page)
    else:
        logger.warning("Form is not sufficiently filled. Not attempting to submit.")
    
    # Take final screenshot
    await save_full_page_screenshot(page, "after_submission")
    
    # Return results
    return {
        "success": is_form_sufficiently_filled,
        "form_type": form_type,
        "resume_uploaded": fields_completion["resume_uploaded"],
        "fields_processed": fields_completion["total_fields_processed"],
        "fields_filled": fields_completion["fields_successfully_filled"],
        "completion_rate": form_completion_rate * 100,
        "multi_step_form": form_metadata.get("is_multi_step", False),
    }