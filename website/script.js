// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
        
        // Close menu when clicking on a link
        document.querySelectorAll('.nav-menu a').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });
    }
});

// Smooth Scrolling for Navigation Links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Intersection Observer for Animation on Scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Animate elements on scroll
document.addEventListener('DOMContentLoaded', function() {
    const animateElements = document.querySelectorAll('.feature-card, .pricing-card, .install-option');
    
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// Demo Video Play Button
document.addEventListener('DOMContentLoaded', function() {
    const playButton = document.querySelector('.play-button');
    if (playButton) {
        playButton.addEventListener('click', function() {
            // This would typically open a modal or redirect to a video
            alert('Demo video coming soon! 🎬\n\nIn the meantime, try installing the extension and testing it with the error examples in the project.');
        });
    }
});

// Pricing Card Hover Effects
document.addEventListener('DOMContentLoaded', function() {
    const pricingCards = document.querySelectorAll('.pricing-card');
    
    pricingCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            if (!this.classList.contains('popular')) {
                this.style.transform = 'translateY(-8px) scale(1.02)';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('popular')) {
                this.style.transform = 'translateY(0) scale(1)';
            } else {
                this.style.transform = 'translateY(0) scale(1.05)';
            }
        });
    });
});

// Copy to Clipboard for Install Commands
document.addEventListener('DOMContentLoaded', function() {
    const codeBlocks = document.querySelectorAll('.install-commands code');
    
    codeBlocks.forEach(code => {
        code.style.cursor = 'pointer';
        code.title = 'Click to copy';
        
        code.addEventListener('click', function() {
            navigator.clipboard.writeText(this.textContent).then(function() {
                // Show temporary feedback
                const originalText = code.textContent;
                code.textContent = 'Copied! ✓';
                code.style.color = '#28ca42';
                
                setTimeout(() => {
                    code.textContent = originalText;
                    code.style.color = '';
                }, 2000);
            }).catch(function(err) {
                console.error('Could not copy text: ', err);
            });
        });
    });
});

// Feature Cards Stagger Animation
document.addEventListener('DOMContentLoaded', function() {
    const featureCards = document.querySelectorAll('.feature-card');
    
    const staggerObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
            }
        });
    }, observerOptions);
    
    featureCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
        staggerObserver.observe(card);
    });
});

// Navbar Background on Scroll
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 100) {
        navbar.style.background = 'rgba(255, 255, 255, 0.98)';
        navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.background = 'rgba(255, 255, 255, 0.95)';
        navbar.style.boxShadow = 'none';
    }
});

// Install Button Tracking (for analytics)
document.addEventListener('DOMContentLoaded', function() {
    const installButtons = document.querySelectorAll('a[href*="vscode:extension"], a[href="#install"]');
    
    installButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Track install button clicks
            console.log('Install button clicked:', this.textContent.trim());
            
            // If it's a VS Code extension link, show helpful message
            if (this.href.includes('vscode:extension')) {
                e.preventDefault();
                alert('🚀 Extension installation:\n\n1. This will open VS Code\n2. Install the AI Error Translator extension\n3. Configure your API key in settings\n4. Start translating errors with Ctrl+Shift+E\n\nNote: Extension is in development - check GitHub for latest version!');
            }
        });
    });
});

// Contact Form Handler (if added later)
function handleContactForm(formData) {
    // This would integrate with a backend service
    console.log('Contact form submitted:', formData);
    alert('Thanks for your interest! We\'ll be in touch soon. 📧');
}

// Newsletter Signup (if added later)
function handleNewsletterSignup(email) {
    // This would integrate with an email service
    console.log('Newsletter signup:', email);
    alert('Thanks for subscribing! 📬 You\'ll be the first to know about updates.');
}

// Error Handling for Failed Network Requests
window.addEventListener('error', function(e) {
    console.error('Page error:', e.error);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
});

// Performance Monitoring
window.addEventListener('load', function() {
    if ('performance' in window) {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log('Page load time:', loadTime + 'ms');
    }
});

// Add keyboard navigation support
document.addEventListener('keydown', function(e) {
    // Escape key closes mobile menu
    if (e.key === 'Escape') {
        const hamburger = document.querySelector('.hamburger');
        const navMenu = document.querySelector('.nav-menu');
        if (hamburger && navMenu) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
        }
    }
});