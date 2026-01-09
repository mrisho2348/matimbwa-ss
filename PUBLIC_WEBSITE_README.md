# Matimbwa Secondary School - Public Website

## Overview

This is a comprehensive public-facing website for Matimbwa Secondary School, a government secondary school in Makueni County, Kenya. The website provides information about the school and includes a login system for authorized users.

## Features

### Public Pages (Accessible to Everyone)

1. **Home Page** (`/`)
   - Welcome message and school overview
   - Key features of the school
   - School statistics (students, staff, achievements)
   - Quick links to other sections

2. **About School** (`/about/`)
   - School history and background
   - Mission and Vision statements
   - Core values (Integrity, Excellence, Respect, Responsibility, Teamwork, Innovation)
   - School leadership profiles
   - School facilities list

3. **Academic Programs** (`/programs/`)
   - Science Stream details
   - Arts Stream details
   - Technical Stream details
   - Subject offerings for each stream
   - Career pathways
   - Academic support services
   - Examination structure
   - Academic achievements

4. **News and Updates** (`/news/`)
   - Latest school news and announcements
   - Upcoming events calendar
   - Academic calendar (term dates)
   - News archive with categories
   - Event announcements

5. **Gallery and Events** (`/gallery/`)
   - School events showcase
   - Campus gallery
   - Student activities (sports, clubs, societies)
   - Community service initiatives
   - Cultural events
   - Student leadership opportunities

6. **Contact Us** (`/contact/`)
   - Contact information (address, phone, email)
   - Contact form for messages
   - School leadership contact details
   - Office hours
   - Frequently Asked Questions (FAQ)
   - Location information
   - Directions

### Authentication Pages

7. **Login Page** (`/login/`)
   - Username and password authentication
   - User type-based redirection:
     - HOD/Principal → Admin dashboard
     - Staff → Staff dashboard
   - Remember me option
   - Password recovery link
   - Security information

8. **Logout** (`/logout/`)
   - Secure logout functionality
   - Redirects to home page

## Project Structure

```
public/
├── __init__.py
├── apps.py          # App configuration
├── views.py         # View functions for all pages
├── urls.py          # URL routing configuration

templates/public/
├── base.html        # Base template with navigation and footer
├── home.html        # Home page
├── about.html       # About school page
├── academic_programs.html  # Academic programs page
├── news.html        # News and updates page
├── gallery.html     # Gallery and events page
├── contact.html     # Contact us page
└── login.html       # Login page
```

## Technical Details

### Views

The `views.py` file contains the following functions:

- `public_home()` - Home page view
- `about_school()` - About school view
- `academic_programs()` - Academic programs view
- `news_and_updates()` - News page view
- `gallery_and_events()` - Gallery view
- `contact_school()` - Contact page with form handling
- `public_login()` - Login page with authentication
- `public_logout()` - Logout functionality

### URL Patterns

```
''                     → public_home
'about/'               → about_school
'programs/'            → academic_programs
'news/'                → news_updates
'gallery/'             → gallery_events
'contact/'             → public_contact
'login/'               → public_login
'logout/'              → public_logout
```

### Database Models

The login functionality uses the existing `CustomUser` model from the `accounts` app:
- User authentication with username and password
- User type-based access control (HOD, Staff)
- is_active flag for user status

## Styling

The website features:
- Responsive design (works on desktop, tablet, mobile)
- Professional color scheme:
  - Primary: #1e3c72 (dark blue)
  - Secondary: #2a5298 (medium blue)
  - Accent: #ffd700 (gold)
- Modern UI with smooth transitions
- Accessible navigation
- Mobile-friendly hamburger menu considerations

## Key Features

### Navigation
- Sticky header with school logo and navigation menu
- Active page highlighting
- Authentication buttons in header
- Responsive navigation for mobile devices

### Footer
- School information
- Quick links
- Contact details
- Social media links (template ready)
- Copyright information

### Contact Form
- Name, email, phone, subject, message fields
- CSRF protection
- Server-side validation
- Success/error messages

### Login System
- Secure authentication
- User type-based redirection
- Session management
- Password fields with secure input
- Remember me functionality

## Installation & Setup

1. The public app is already integrated into the Django project
2. Ensure `'public.apps.PublicConfig'` is added to `INSTALLED_APPS` in settings.py
3. Run migrations: `python manage.py migrate`
4. Start the development server: `python manage.py runserver`

## Usage

### For Public Visitors
- Navigate to `http://localhost:8000/` to access the website
- Browse all public pages without authentication
- Submit contact form for inquiries

### For School Staff/Admins
- Click "Login" button in the header
- Enter username and password
- Access dashboard based on user type

## Content Management

### School Information
- School name, location, and contact details can be updated in `views.py`
- Programs, facilities, and staff info are hardcoded in view functions
- For dynamic content, consider connecting to a database model

### News and Events
- Currently displayed from hardcoded data in `news_and_updates()` view
- To make dynamic: Create a News/Event model and update view

### Images
- Gallery currently uses placeholder system with icons
- To add real images: Update template with actual image file references
- Images should be stored in `static/images/` folder

## Future Enhancements

- Add real image gallery with image upload
- Create dynamic News/Event database model
- Implement email sending for contact form
- Add student portal integration
- Social media widget integration
- Search functionality
- Comment system for news
- Event calendar with Google Calendar integration
- Online admission form
- Payment gateway integration for fees

## Security Considerations

- CSRF protection enabled on all forms
- Authentication required for protected views
- Password validation using Django's built-in validators
- Session-based authentication
- Secure password hashing

## Browser Compatibility

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Android)

## Performance

- Clean HTML structure
- Lightweight CSS (inline styles for simplicity)
- Optimized image delivery (placeholder system)
- Fast page load times

## Support & Maintenance

For support or maintenance:
- Contact: info@matimbwa.ac.ke
- Phone: +254 712 345 678
- Office Hours: Monday - Friday, 8:00 AM - 5:00 PM

---

**Created for:** Matimbwa Secondary School  
**Last Updated:** January 2025  
**Version:** 1.0
