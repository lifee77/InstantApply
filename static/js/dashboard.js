document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('job-search-form');
    const jobResultsDiv = document.getElementById('job-results');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const jobTitle = document.getElementById('job-title').value;
        const location = document.getElementById('location').value;
        
        // Show loading indicator
        jobResultsDiv.innerHTML = '<p class="loading">Searching for jobs...</p>';
        
        fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_title: jobTitle, location: location })
        })
        .then(response => response.json())
        .then(data => {
            displayJobs(data.jobs || data);
        })
        .catch(err => {
            console.error('Error during job search:', err);
            jobResultsDiv.innerHTML = '<p class="error">Error searching for jobs. Please try again.</p>';
        });
    });
    
    function displayJobs(jobs) {
        if (!jobs || jobs.length === 0) {
            jobResultsDiv.innerHTML = '<p class="no-results">No jobs found matching your criteria. Please try a different search.</p>';
            return;
        }
        
        let html = '<h3>Search Results</h3>';
        html += '<div class="job-list">';
        
        jobs.forEach(job => {
            html += `
                <div class="job-card">
                    <h4>${job.title || job.job_title}</h4>
                    <p class="company">${job.company}</p>
                    <p class="location">${job.location}</p>
                    <div class="job-actions">
                        <a href="${job.url}" target="_blank" class="view-job-btn">View Job</a>
                        <button class="apply-btn" data-job-url="${job.url}">Apply</button>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        jobResultsDiv.innerHTML = html;
        
        // Add event listeners to apply buttons
        document.querySelectorAll('.apply-btn').forEach(button => {
            button.addEventListener('click', function() {
                const jobUrl = this.getAttribute('data-job-url');
                applyToJob(jobUrl);
            });
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