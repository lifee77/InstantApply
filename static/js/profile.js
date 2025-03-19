// This JavaScript should be added to the profile.html file in the scripts block

// Toggle between view and edit modes
document.addEventListener('DOMContentLoaded', function() {
    const profileView = document.getElementById('profile-view');
    const profileEdit = document.getElementById('profile-edit');
    const btnEditProfile = document.getElementById('btn-edit-profile');
    
    btnEditProfile.addEventListener('click', function() {
        profileView.style.display = 'none';
        profileEdit.style.display = 'block';
    });
    
    // Add a cancel button to the edit form if not present
    if (!document.getElementById('btn-cancel-edit')) {
        const submitButton = document.querySelector('#profile-edit button[type="submit"]');
        const cancelButton = document.createElement('button');
        cancelButton.id = 'btn-cancel-edit';
        cancelButton.type = 'button';
        cancelButton.className = 'btn btn-secondary btn-lg ms-2';
        cancelButton.textContent = 'Cancel';
        submitButton.parentNode.insertBefore(cancelButton, submitButton.nextSibling);
        
        cancelButton.addEventListener('click', function() {
            profileEdit.style.display = 'none';
            profileView.style.display = 'block';
        });
    }
    
    // Handle resume file upload and preview
    const resumeFileInput = document.getElementById('user-resume-file');
    if (resumeFileInput) {
        resumeFileInput.addEventListener('change', function() {
            const file = resumeFileInput.files[0];
            if (!file) return;
            
            const maxSizeMB = 10;
            const maxSizeBytes = maxSizeMB * 1024 * 1024;
            
            if (file.size > maxSizeBytes) {
                alert(`File is too large. Maximum size is ${maxSizeMB}MB.`);
                resumeFileInput.value = '';
                return;
            }
            
            const uploadProgress = document.querySelector('.upload-progress');
            const progressBar = document.getElementById('upload-progress-bar');
            const uploadStatus = document.getElementById('upload-status');
            
            // Show progress elements
            uploadProgress.style.display = 'block';
            uploadStatus.style.display = 'block';
            uploadStatus.textContent = 'Reading file...';
            
            // For text files, show preview directly
            if (file.type === 'text/plain') {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('user-resume').value = e.target.result;
                    uploadStatus.textContent = 'Text file loaded successfully.';
                };
                reader.onerror = function() {
                    uploadStatus.textContent = 'Error reading file.';
                };
                reader.readAsText(file);
            } else {
                // For other files, just show filename
                uploadStatus.textContent = `${file.name} selected. File will be parsed on save.`;
            }
        });
    }
});

// Functions for copying and downloading resume text
function copyResumeText() {
    const resumeText = document.getElementById('resume-content').innerText;
    navigator.clipboard.writeText(resumeText)
        .then(() => {
            alert('Resume text copied to clipboard!');
        })
        .catch(err => {
            console.error('Failed to copy text: ', err);
            alert('Failed to copy resume text.');
        });
}

function downloadResumeText() {
    const resumeText = document.getElementById('resume-content').innerText;
    const blob = new Blob([resumeText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'resume.txt';
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
