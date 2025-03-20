document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard JS loaded');
    const form = document.getElementById('job-search-form');
    const jobResultsDiv = document.getElementById('job-results');
    
    if (form && jobResultsDiv) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Form submitted');
            const jobTitle = document.getElementById('job-title').value;
            const location = document.getElementById('location').value;
            
            // Show loading indicator
            jobResultsDiv.innerHTML = '<p class="loading">Searching for jobs...</p>';
            
            fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_title: jobTitle, location: location })
            })
            .then(response => {
                console.log('Got response', response);
                return response.json();
            })
            .then(data => {
                console.log('Job search results:', data);
                // Check for data structure - adjust based on API response
                if (data.jobs) {
                    displayJobs(data.jobs);
                } else if (data.saved_jobs) {
                    displayJobs(data.saved_jobs);
                } else if (Array.isArray(data)) {
                    displayJobs(data);
                } else {
                    jobResultsDiv.innerHTML = '<p class="error">No jobs found. Please try a different search.</p>';
                }
            })
            .catch(err => {
                console.error('Error during job search:', err);
                jobResultsDiv.innerHTML = '<p class="error">Error searching for jobs. Please try again.</p>';
            });
        });
    } else {
        console.error('Form or results container not found');
    }
    
    // Update the displayJobs function to handle console debugging and better error states
    function displayJobs(jobs) {
        console.log('Displaying jobs:', jobs);
        
        if (!jobs || jobs.length === 0) {
            jobResultsDiv.innerHTML = '<p class="no-results">No jobs found matching your criteria. Please try a different search.</p>';
            return;
        }
        
        // Log what we're working with
        console.log(`Displaying ${jobs.length} jobs`);
        
        // Check the first job to log its structure
        if (jobs.length > 0) {
            console.log('First job example:', jobs[0]);
            console.log('Job title:', jobs[0].title || jobs[0].job_title);
        }
        
        let html = '<h3>Search Results</h3>';
        html += '<div class="job-list">';
        
        jobs.forEach((job, index) => {
            // Handle different potential field names
            const title = job.title || job.job_title || 'Job Title Unavailable';
            const company = job.company || job.employer_name || 'Company Unavailable';
            const location = job.location || 'Location Unavailable';
            const url = job.url || job.job_apply_link || '';
            
            console.log(`Job ${index + 1}: ${title} at ${company}`);
            
            html += `
                <div class="job-card">
                    <h4>${title}</h4>
                    <p class="company">${company}</p>
                    <p class="location">${location}</p>
                    <div class="job-actions">
                        <a href="${url}" target="_blank" class="view-job-btn" ${url ? '' : 'style="display:none"'}>View Job</a>
                        <button class="apply-btn" data-job-url="${url}" ${url ? '' : 'disabled'}>Apply</button>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        jobResultsDiv.innerHTML = html;
        
        // Add event listeners to apply buttons
        document.querySelectorAll('.apply-btn').forEach(button => {
            if (!button.disabled) {
                button.addEventListener('click', function() {
                    const jobUrl = this.getAttribute('data-job-url');
                    applyToJob(jobUrl);
                });
            }
        });
    }
    
    function applyToJob(jobUrl) {
        // Show applying message
        alert('Applying to job. This may take a moment...');
        
        fetch('/api/apply', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({job_url: jobUrl})
        })
        .then(response => response.json())
        .then(data => {
            if(data.success || data.message) {
                alert('Application submitted successfully!');
                window.location.href = '/applications'; // Redirect to applications page
            } else {
                alert('Failed to apply: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => {
            console.error('Error:', err);
            alert('Error applying to job: ' + err);
        });
    }
});