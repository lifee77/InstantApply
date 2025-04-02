/**
 * Handle all checkout page functionality
 */

// Price and promo code logic
function applyPromo() {
    const promoInput = document.getElementById('promo');
    const promoCode = promoInput.value.trim();
    const promoSuccess = document.getElementById('promo-success');
    const promoError = document.getElementById('error-msg');
    const originalPrice = document.getElementById('original-price');
    const currentPrice = document.getElementById('price');
    const discountBadge = document.getElementById('discount-badge');
    
    // Reset messages
    promoSuccess.style.display = 'none';
    promoError.style.display = 'none';
    
    // Check if promo code is valid
    if (promoCode.toLowerCase() === 'jobnow') {
        // Apply discount
        originalPrice.style.display = 'block'; // Show original price as strikethrough
        currentPrice.textContent = '$70';
        discountBadge.style.display = 'block'; // Show discount badge
        promoSuccess.style.display = 'block';
    } else {
        promoError.style.display = 'block';
    }
}

// Handle payment button click
function startPayment() {
    // Show loading spinner
    const pricingBox = document.querySelector('.pricing-box');
    const loadingContainer = document.getElementById('loading-container');
    const emailForm = document.getElementById('email-form');
    
    // Hide pricing box, show loading spinner
    pricingBox.style.display = 'none';
    loadingContainer.style.display = 'block';
    
    // After 2 seconds, show the email form
    setTimeout(() => {
        loadingContainer.style.display = 'none';
        emailForm.style.display = 'block';
    }, 2000);
}

// Handle email submission
function submitEmail() {
    const emailInput = document.querySelector('.email-input');
    const notifyButton = document.querySelector('.notify-button');
    const email = emailInput.value.trim();
    
    if (email && email.includes('@')) {
        // Disable button and show loading state
        notifyButton.disabled = true;
        notifyButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        // Send email to the server
        fetch('/api/save-waitlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                email: email,
                source: 'checkout_page',
                discount_applied: document.getElementById('original-price').style.display === 'block'
            })
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                // Try again once with a 2-second delay in case the server is creating tables
                return new Promise(resolve => {
                    setTimeout(() => {
                        fetch('/api/save-waitlist', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest'
                            },
                            body: JSON.stringify({
                                email: email,
                                source: 'checkout_page',
                                discount_applied: document.getElementById('original-price').style.display === 'block'
                            })
                        }).then(resp => {
                            if (resp.ok) {
                                return resp.json().then(resolve);
                            } else {
                                throw new Error(`Server responded with status: ${resp.status}`);
                            }
                        }).catch(resolve);
                    }, 2000);
                });
            }
        })
        .then(data => {
            if (!data || data.error) {
                throw new Error(data?.details || 'Unknown error');
            }
            
            console.log("Success:", data);
            
            // Update the email form with success message
            document.getElementById('email-form').innerHTML = `
                <div class="notice-icon">
                    <i class="fas fa-check-circle" style="color: var(--success-color);"></i>
                </div>
                <h3>Thank You!</h3>
                <p>We've saved your email address and will contact you as soon as possible to help you with your job search.</p>
                <p>A confirmation will be sent to <strong>${data.email || email}</strong>.</p>
                <p class="mt-4">
                    <button onclick="window.location.href='/dashboard'" class="pay-button">
                        Return to Dashboard
                    </button>
                </p>
            `;
        })
        .catch(error => {
            console.error('Error:', error);
            notifyButton.disabled = false;
            notifyButton.innerHTML = 'Notify Me';
            
            // Show a more user-friendly error message - but still store the email locally
            const errorMessage = document.createElement('p');
            errorMessage.className = 'promo-error';
            errorMessage.textContent = 'There was a problem connecting to our server, but we\'ve saved your email. We\'ll contact you soon!';
            
            // Store email in localStorage as backup
            try {
                const waitlist = JSON.parse(localStorage.getItem('waitlist') || '[]');
                waitlist.push({
                    email,
                    timestamp: new Date().toISOString(),
                    discount: document.getElementById('original-price').style.display === 'block'
                });
                localStorage.setItem('waitlist', JSON.stringify(waitlist));
            } catch (e) {
                console.error('Failed to save to localStorage:', e);
            }
            
            // Insert error message but still show success view
            document.getElementById('email-form').innerHTML = `
                <div class="notice-icon">
                    <i class="fas fa-check-circle" style="color: var(--success-color);"></i>
                </div>
                <h3>Thank You!</h3>
                <p>We've received your information and will contact you as soon as possible to help you with your job search.</p>
                <p>A confirmation will be sent to <strong>${email}</strong>.</p>
                <p class="mt-4">
                    <button onclick="window.location.href='/dashboard'" class="pay-button">
                        Return to Dashboard
                    </button>
                </p>
            `;
        });
    } else {
        // Show validation error
        const errorMessage = document.createElement('p');
        errorMessage.className = 'promo-error';
        errorMessage.textContent = 'Please enter a valid email address.';
        
        // Remove any existing error messages
        document.querySelectorAll('.email-input-group + .promo-error').forEach(el => el.remove());
        
        // Insert error message after the input group
        const emailInputGroup = document.querySelector('.email-input-group');
        if (emailInputGroup.nextElementSibling) {
            emailInputGroup.parentNode.insertBefore(errorMessage, emailInputGroup.nextElementSibling);
        } else {
            emailInputGroup.parentNode.appendChild(errorMessage);
        }
        
        // Remove the error message after 5 seconds
        setTimeout(() => {
            errorMessage.remove();
        }, 5000);
    }
}

// Video player functionality
document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('demo-video');
    const playButton = document.querySelector('.play-button');
    
    if (playButton && video) {
        playButton.addEventListener('click', function() {
            video.play();
            playButton.style.display = 'none';
        });
        
        video.addEventListener('pause', function() {
            playButton.style.display = 'flex';
        });
    }
});
