document.addEventListener('DOMContentLoaded', function() {
    // Toggle between view and edit modes
    const profileView = document.getElementById('profile-view');
    const profileEdit = document.getElementById('profile-edit');
    const btnEditProfile = document.getElementById('btn-edit-profile');
    const btnCancelEdit = document.getElementById('btn-cancel-edit');

    btnEditProfile.addEventListener('click', function() {
        profileView.style.display = 'none';
        profileEdit.style.display = 'block';
        setTimeout(() => window.scrollTo(0, 0), 10);
    });

    // Use the existing cancel button instead of creating a new one
    btnCancelEdit.addEventListener('click', function() {
        profileEdit.style.display = 'none';
        profileView.style.display = 'block';
    });

    // Resume parsing logic
    const resumeFileInput = document.getElementById('user-resume-file');
    const userResumeTextarea = document.getElementById('user-resume');

    function parseResumeAndFillFields(resumeText) {
        const lines = resumeText.split('\n').map(line => line.trim());

        // Personal Information
        const emailMatch = resumeText.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
        if (emailMatch && !document.getElementById('email').value) document.getElementById('email').value = emailMatch[0];

        const nameMatch = lines.find(line => line.match(/^(Name|Full Name):?\s*(.+)$/i));
        if (nameMatch) {
            const name = nameMatch.replace(/^(Name|Full Name):?\s*/i, '');
            document.getElementById('name').value = name;
        }

        // Skills
        const skillsSection = lines.findIndex(line => line.match(/skills/i));
        if (skillsSection !== -1) {
            const skills = lines.slice(skillsSection + 1)
                .filter(line => line && !line.match(/experience|education|certifications/i))
                .join(', ');
            document.getElementById('user-skills').value = skills;
        }

        // Experience
        const expSection = lines.findIndex(line => line.match(/experience/i));
        if (expSection !== -1) {
            const exp = lines.slice(expSection + 1)
                .filter(line => line && !line.match(/education|certifications|skills/i))
                .join('\n');
            document.getElementById('user-experience').value = exp;
        }

        // Certifications
        const certSection = lines.findIndex(line => line.match(/certifications/i));
        if (certSection !== -1) {
            const certs = lines.slice(certSection + 1)
                .filter(line => line && !line.match(/education|skills|experience/i))
                .map(line => ({ name: line, organization: '', expiry: '' }));
            document.getElementById('certifications-container').innerHTML = '';
            certs.forEach(addCertificationField);
        }

        // Desired Job Titles (basic guess)
        const titleMatch = resumeText.match(/(software engineer|data scientist|project manager)/i);
        if (titleMatch) {
            document.getElementById('job-titles-container').innerHTML = '';
            addJobTitleField(titleMatch[0]);
        }
    }

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

            uploadProgress.style.display = 'block';
            uploadStatus.style.display = 'block';
            uploadStatus.textContent = 'Reading file...';
            uploadStatus.className = 'upload-status mt-2';

            if (file.type === 'text/plain') {
                const reader = new FileReader();
                reader.onload = function(e) {
                    userResumeTextarea.value = e.target.result;
                    uploadStatus.textContent = 'Text file loaded successfully.';
                    uploadStatus.classList.add('success');
                    progressBar.style.width = '100%';
                    parseResumeAndFillFields(e.target.result);
                };
                reader.onerror = function() {
                    uploadStatus.textContent = 'Error reading file.';
                    uploadStatus.classList.add('error');
                };
                reader.readAsText(file);
            } else if (file.type === 'application/pdf' || 
                      file.type === 'application/msword' || 
                      file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
                uploadStatus.textContent = `${file.name} selected. Text will be extracted when you save.`;
                uploadStatus.classList.add('success');
                progressBar.style.width = '100%';
                if (userResumeTextarea.value === '') {
                    userResumeTextarea.value = 'Your resume text will be extracted from ' + file.name + ' when you save the profile.';
                }
            } else {
                uploadStatus.textContent = `Unsupported file type. Please use PDF, DOC, DOCX, or TXT.`;
                uploadStatus.classList.add('error');
                resumeFileInput.value = '';
            }
        });
    }

    userResumeTextarea.addEventListener('input', function() {
        parseResumeAndFillFields(this.value);
    });

    // Initialize dynamic fields with existing data
    function initializeDynamicFields(selector, data, addFunction) {
        try {
            const items = JSON.parse(data || '[]');
            if (items.length) {
                const container = document.getElementById(selector);
                container.innerHTML = '';
                items.forEach(item => addFunction(item));
            }
        } catch (e) {
            console.error(`Error loading ${selector}:`, e);
        }
    }

    // Pass initial data from Jinja2 via a script tag or data attribute in the HTML
    const initialData = {
        jobTitles: document.getElementById('desired_job_titles_json')?.dataset?.initial || '[]',
        portfolioLinks: document.getElementById('portfolio_links_json')?.dataset?.initial || '[]',
        certifications: document.getElementById('certifications_json')?.dataset?.initial || '[]',
        languages: document.getElementById('languages_json')?.dataset?.initial || '[]',
        values: document.getElementById('applicant_values_json')?.dataset?.initial || '[]',
        projects: document.getElementById('projects_json')?.dataset?.initial || '[]'
    };

    initializeDynamicFields('job-titles-container', initialData.jobTitles, addJobTitleField);
    initializeDynamicFields('portfolio-links-container', initialData.portfolioLinks, addPortfolioLinkField);
    initializeDynamicFields('certifications-container', initialData.certifications, addCertificationField);
    initializeDynamicFields('languages-container', initialData.languages, addLanguageField);
    initializeDynamicFields('values-container', initialData.values, addValueField);
    initializeDynamicFields('projects-container', initialData.projects, addProjectField);

    toggleMilitaryFields();

    // Auto-resize textareas
    const textAreas = document.querySelectorAll('textarea');
    textAreas.forEach(textarea => {
        adjustHeight(textarea);
        textarea.addEventListener('input', () => adjustHeight(textarea));
        window.addEventListener('resize', () => adjustHeight(textarea));
    });

    function adjustHeight(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = `${textarea.scrollHeight}px`;
    }
});

function copyResumeText() {
    const resumeText = document.getElementById('resume-content').innerText;
    navigator.clipboard.writeText(resumeText)
        .then(() => alert('Resume text copied to clipboard!'))
        .catch(err => alert('Failed to copy resume text.'));
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
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function toggleMilitaryFields() {
    const militaryStatus = document.getElementById('military_status').value;
    const additionalFields = document.getElementById('military-additional-fields');
    additionalFields.style.display = (militaryStatus && militaryStatus !== 'No Military Service') ? 'block' : 'none';
}

document.getElementById('add-job-title').addEventListener('click', () => addJobTitleField());
function addJobTitleField(value = '') {
    const container = document.getElementById('job-titles-container');
    const div = document.createElement('div');
    div.className = 'input-group mb-2';
    div.innerHTML = `
        <input type="text" class="form-control job-title" value="${value}" placeholder="e.g., Software Engineer">
        <button type="button" class="btn remove-job-title">Remove</button>
    `;
    container.appendChild(div);
    div.querySelector('.remove-job-title').addEventListener('click', () => container.removeChild(div));
}

document.getElementById('add-portfolio-link').addEventListener('click', () => addPortfolioLinkField());
function addPortfolioLinkField(value = '') {
    const container = document.getElementById('portfolio-links-container');
    const div = document.createElement('div');
    div.className = 'input-group mb-2';
    div.innerHTML = `
        <input type="url" class="form-control portfolio-link" value="${value}" placeholder="https://github.com/yourusername">
        <button type="button" class="btn remove-portfolio-link">Remove</button>
    `;
    container.appendChild(div);
    div.querySelector('.remove-portfolio-link').addEventListener('click', () => container.removeChild(div));
}

document.getElementById('add-certification').addEventListener('click', () => addCertificationField());
function addCertificationField(cert = {}) {
    const container = document.getElementById('certifications-container');
    const div = document.createElement('div');
    div.className = 'certification-entry border rounded p-3 mb-3';
    div.innerHTML = `
        <div class="mb-2">
            <label class="form-label">Certification Name</label>
            <input type="text" class="form-control cert-name" value="${cert.name || ''}" placeholder="e.g., AWS Solutions Architect">
        </div>
        <div class="row">
            <div class="col">
                <label class="form-label">Issuing Organization</label>
                <input type="text" class="form-control cert-org" value="${cert.organization || ''}" placeholder="e.g., Amazon Web Services">
            </div>
            <div class="col">
                <label class="form-label">Expiration Date</label>
                <input type="date" class="form-control cert-expiry" value="${cert.expiry || ''}">
            </div>
        </div>
        <button type="button" class="btn btn-sm mt-3 remove-cert">Remove</button>
    `;
    container.appendChild(div);
    div.querySelector('.remove-cert').addEventListener('click', () => container.removeChild(div));
}

document.getElementById('add-language').addEventListener('click', () => addLanguageField());
function addLanguageField(lang = {}) {
    const container = document.getElementById('languages-container');
    const div = document.createElement('div');
    div.className = 'language-entry row mb-2';
    const proficiencyOptions = ['Native', 'Fluent', 'Advanced', 'Intermediate', 'Basic']
        .map(level => `<option value="${level}" ${lang.proficiency === level ? 'selected' : ''}>${level}</option>`)
        .join('');
    div.innerHTML = `
        <div class="col-md-6">
            <input type="text" class="form-control language-name" value="${lang.language || ''}" placeholder="Language">
        </div>
        <div class="col-md-4">
            <select class="form-select language-proficiency">${proficiencyOptions}</select>
        </div>
        <div class="col-md-2">
            <button type="button" class="btn remove-language">Remove</button>
        </div>
    `;
    container.appendChild(div);
    div.querySelector('.remove-language').addEventListener('click', () => container.removeChild(div));
}

document.getElementById('add-value').addEventListener('click', () => addValueField());
function addValueField(value = '') {
    const container = document.getElementById('values-container');
    const div = document.createElement('div');
    div.className = 'input-group mb-2';
    div.innerHTML = `
        <input type="text" class="form-control value-item" value="${value}" placeholder="e.g., Innovation">
        <button type="button" class="btn remove-value">Remove</button>
    `;
    container.appendChild(div);
    div.querySelector('.remove-value').addEventListener('click', () => container.removeChild(div));
}

// New function for managing projects
document.getElementById('add-project')?.addEventListener('click', () => addProjectField());
function addProjectField(project = {}) {
    const container = document.getElementById('projects-container');
    const div = document.createElement('div');
    div.className = 'project-entry border rounded p-3 mb-3';
    
    // Generate a unique ID for technology tags input
    const techInputId = 'tech-input-' + Date.now();
    
    div.innerHTML = `
        <div class="mb-3">
            <label class="form-label">Project Name</label>
            <input type="text" class="form-control project-name" value="${project.name || ''}" placeholder="e.g., Personal Portfolio Website">
        </div>
        <div class="mb-3">
            <label class="form-label">Description</label>
            <textarea class="form-control project-description" rows="2" placeholder="Brief description of your project">${project.description || ''}</textarea>
        </div>
        <div class="mb-3">
            <label class="form-label">Project URL (optional)</label>
            <input type="url" class="form-control project-link" value="${project.link || ''}" placeholder="e.g., https://github.com/username/project">
        </div>
        <div class="mb-3">
            <label class="form-label">Technologies Used</label>
            <div class="tech-tags-container mb-2">
                ${(project.technologies || []).map(tech => 
                    `<span class="badge me-1 mb-1 tech-tag">
                        ${tech}<button type="button" class="btn-close ms-1" aria-label="Remove"></button>
                    </span>`).join('')}
            </div>
            <div class="input-group">
                <input type="text" class="form-control" id="${techInputId}" placeholder="Type a technology and press Enter (e.g., React)">
                <button type="button" class="btn add-tech">Add</button>
            </div>
        </div>
        <div class="mb-3 project-details-container">
            <label class="form-label">Project Details</label>
            <div class="project-details">
                ${(project.details || []).map(detail => 
                    `<div class="input-group mb-2 detail-entry">
                        <input type="text" class="form-control project-detail" value="${detail}" placeholder="e.g., Implemented responsive design">
                        <button type="button" class="btn remove-detail">Remove</button>
                    </div>`).join('')}
            </div>
            <button type="button" class="btn btn-sm add-project-detail">
                <i class="bi bi-plus"></i> Add Detail
            </button>
        </div>
        <button type="button" class="btn btn-sm mt-3 remove-project">Remove Project</button>
    `;
    
    container.appendChild(div);
    
    // Set up event listeners for the project entry
    div.querySelector('.remove-project').addEventListener('click', () => {
        container.removeChild(div);
    });
    
    // Add project detail
    div.querySelector('.add-project-detail').addEventListener('click', () => {
        const detailsContainer = div.querySelector('.project-details');
        const detailDiv = document.createElement('div');
        detailDiv.className = 'input-group mb-2 detail-entry';
        detailDiv.innerHTML = `
            <input type="text" class="form-control project-detail" placeholder="e.g., Implemented responsive design">
            <button type="button" class="btn remove-detail">Remove</button>
        `;
        detailsContainer.appendChild(detailDiv);
        
        detailDiv.querySelector('.remove-detail').addEventListener('click', () => {
            detailsContainer.removeChild(detailDiv);
        });
    });
    
    // Handle existing details
    div.querySelectorAll('.remove-detail').forEach(button => {
        button.addEventListener('click', () => {
            const detailEntry = button.closest('.detail-entry');
            detailEntry.parentNode.removeChild(detailEntry);
        });
    });
    
    // Handle technology tags
    const techInput = div.querySelector(`#${techInputId}`);
    const addTechButton = div.querySelector('.add-tech');
    const tagsContainer = div.querySelector('.tech-tags-container');
    
    function addTechTag(techName) {
        if (!techName.trim()) return;
        
        const tagSpan = document.createElement('span');
        tagSpan.className = 'badge me-1 mb-1 tech-tag';
        tagSpan.innerHTML = `
            ${techName.trim()}
            <button type="button" class="btn-close ms-1" aria-label="Remove"></button>
        `;
        tagsContainer.appendChild(tagSpan);
        
        // Add remove button functionality
        tagSpan.querySelector('.btn-close').addEventListener('click', () => {
            tagsContainer.removeChild(tagSpan);
        });
        
        techInput.value = '';
    }
    
    // Add tech tag with button
    addTechButton.addEventListener('click', () => {
        addTechTag(techInput.value);
    });
    
    // Add tech tag with Enter key
    techInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTechTag(techInput.value);
        }
    });
    
    // Handle existing tech tags
    div.querySelectorAll('.tech-tag .btn-close').forEach(button => {
        button.addEventListener('click', () => {
            const tagSpan = button.closest('.tech-tag');
            tagsContainer.removeChild(tagSpan);
        });
    });
}

document.querySelector('form').addEventListener('submit', function(event) {
    const jobTitles = [];
    document.querySelectorAll('.job-title').forEach(input => {
        if (input.value.trim()) jobTitles.push(input.value.trim());
    });
    document.getElementById('desired_job_titles_json').value = JSON.stringify(jobTitles);

    const portfolioLinks = [];
    document.querySelectorAll('.portfolio-link').forEach(input => {
        if (input.value.trim()) portfolioLinks.push(input.value.trim());
    });
    document.getElementById('portfolio_links_json').value = JSON.stringify(portfolioLinks);

    const certifications = [];
    document.querySelectorAll('.certification-entry').forEach(cert => {
        const name = cert.querySelector('.cert-name').value.trim();
        const org = cert.querySelector('.cert-org').value.trim();
        const expiry = cert.querySelector('.cert-expiry').value;
        if (name) certifications.push({ name, organization: org, expiry });
    });
    document.getElementById('certifications_json').value = JSON.stringify(certifications);

    const languages = [];
    document.querySelectorAll('.language-entry').forEach(lang => {
        const language = lang.querySelector('.language-name').value.trim();
        const proficiency = lang.querySelector('.language-proficiency').value;
        if (language) languages.push({ language, proficiency });
    });
    document.getElementById('languages_json').value = JSON.stringify(languages);

    const values = [];
    document.querySelectorAll('.value-item').forEach(input => {
        if (input.value.trim()) values.push(input.value.trim());
    });
    document.getElementById('applicant_values_json').value = JSON.stringify(values);

    // Projects - New
    const projects = [];
    document.querySelectorAll('.project-entry').forEach(projectEntry => {
        const name = projectEntry.querySelector('.project-name').value.trim();
        const description = projectEntry.querySelector('.project-description').value.trim();
        const link = projectEntry.querySelector('.project-link').value.trim();
        
        // Extract technologies
        const technologies = [];
        projectEntry.querySelectorAll('.tech-tag').forEach(tag => {
            const techName = tag.textContent.trim();
            if (techName) technologies.push(techName);
        });
        
        // Extract project details
        const details = [];
        projectEntry.querySelectorAll('.project-detail').forEach(detail => {
            const detailText = detail.value.trim();
            if (detailText) details.push(detailText);
        });
        
        if (name) {
            projects.push({
                name,
                description,
                link,
                technologies,
                details
            });
        }
    });
    
    const projectsInput = document.getElementById('projects_json');
    if (projectsInput) projectsInput.value = JSON.stringify(projects);
});