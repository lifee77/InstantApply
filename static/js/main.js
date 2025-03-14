document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('job-search-form');
    const resultsContainer = document.getElementById('results-container');
    const jobResultsDiv = document.getElementById('job-results');
    
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const jobTitle = document.getElementById('job-title').value;
        const location = document.getElementById('location').value;
        
        // Show loading indicator
        jobResultsDiv.innerHTML = '<p>Searching for jobs...</p>';
        resultsContainer.style.display = 'block';
        
        // Make API request to search for jobs
        fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_title: jobTitle,
                location: location
            })
        })
        .then(response => response.json())
        .then(data => {
            // Display job results
            displayJobResults(data.jobs);
        })
        .catch(error => {
            console.error('Error:', error);
            jobResultsDiv.innerHTML = '<p>An error occurred while searching for jobs. Please try again.</p>';
        });
    });
    
    function displayJobResults(jobs) {
        if (!jobs || jobs.length === 0) {
            jobResultsDiv.innerHTML = '<p>No jobs found matching your criteria. Please try a different search.</p>';
            return;
        }
        
        let html = '';
        
        jobs.forEach(job => {
            html += `
                <div class="job-card">
                    <h3>${job.title}</h3>
                    <p><strong>${job.company}</strong> - ${job.location}</p>
                    <p class="job-description">${job.description_snippet || 'No description available'}</p>
                    <button class="apply-btn" data-job-id="${job.id}">Apply Instantly</button>
                </div>
            `;
        });
        
        jobResultsDiv.innerHTML = html;
        
        // Add event listeners to apply buttons
        document.querySelectorAll('.apply-btn').forEach(button => {
            button.addEventListener('click', function() {
                const jobId = this.getAttribute('data-job-id');
                applyForJob(jobId);
            });
        });
    }
    
    function applyForJob(jobId) {
        // In a real application, this would check if the user is logged in
        // and has completed their profile before applying
        
        // For demo purposes, we'll assume user ID 1
        const userId = localStorage.getItem('userId') || 1;
        
        // Show application in progress message
        alert('Your application is being submitted automatically. This process may take a moment...');
        
        fetch('/api/apply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: jobId,
                user_id: userId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Application submitted successfully! ${data.message}`);
            } else {
                alert(`Application submission failed: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while submitting your application. Please try again.');
        });
    }
    
    // Function to handle user profile creation/update
    function setupUserProfileForm() {
        const profileForm = document.getElementById('user-profile-form');
        
        if (profileForm) {
            profileForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = {
                    name: document.getElementById('user-name').value,
                    email: document.getElementById('user-email').value,
                    resume: document.getElementById('user-resume').value,
                    skills: document.getElementById('user-skills').value,
                    experience: document.getElementById('user-experience').value
                };
                
                fetch('/api/user', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                })
                .then(response => response.json())
                .then(data => {
                    alert('Profile saved successfully!');
                    // Store user ID in localStorage for later use
                    localStorage.setItem('userId', data.id);
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while saving your profile. Please try again.');
                });
            });
        }
    }
    
    // Initialize profile form if it exists
    setupUserProfileForm();
});
