# Matimbwa Secondary School - Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Django 4.2.27
- MySQL Server running

### Setup Instructions

1. **Activate Virtual Environment**
   ```powershell
   .\msm\Scripts\Activate.ps1
   ```

2. **Install Dependencies** (if not already installed)
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run Migrations** (if using new database)
   ```powershell
   python manage.py migrate
   ```

4. **Create Superuser** (for admin access)
   ```powershell
   python manage.py createsuperuser
   ```

5. **Start Development Server**
   ```powershell
   python manage.py runserver
   ```

6. **Access the Website**
   - Public Website: `http://localhost:8000/`
   - Admin Panel: `http://localhost:8000/admin/`

---

## 📱 Website Pages

### Public Pages (No Login Required)

| Page | URL | Description |
|------|-----|-------------|
| Home | `/` | Welcome page with school overview |
| About | `/about/` | School history, mission, vision, values |
| Programs | `/programs/` | Academic streams and subjects |
| News | `/news/` | Latest updates and announcements |
| Gallery | `/gallery/` | Events, activities, and campus photos |
| Contact | `/contact/` | Contact form and school info |

### Authentication Pages

| Page | URL | Description |
|------|-----|-------------|
| Login | `/login/` | User authentication |
| Logout | `/logout/` | Logout and redirect to home |

---

## 🔐 Login Information

### Test User Accounts

To test the login system, use the superuser account created during setup:

- **Username:** (your superuser username)
- **Password:** (your superuser password)

### User Types

1. **HOD/Principal (user_type = 1)**
   - Redirects to admin dashboard
   - Full administrative access

2. **Staff (user_type = 2)**
   - Redirects to staff dashboard
   - Teaching and student management

---

## 📝 Important Information

### School Details (Displayed on Website)

- **Name:** Matimbwa Secondary School
- **Type:** Government Institution
- **Location:** Makueni County, Kenya
- **Founded:** 1985
- **Students:** 850+
- **Staff:** 120+

### Contact Information

- **Phone:** +254 712 345 678
- **Email:** info@matimbwa.ac.ke
- **Address:** Matimbwa Secondary School, Makueni County, Kenya
- **Office Hours:** Monday - Friday, 8:00 AM - 5:00 PM

### Academic Streams

1. **Science Stream** - Physics, Chemistry, Biology, Mathematics
2. **Arts Stream** - History, Geography, Economics, Literature
3. **Technical Stream** - Woodwork, Metalwork, Electricity, Building Construction

---

## 🎨 Customization Guide

### Change School Name

In all template files, replace "Matimbwa Secondary School" with your school name.

Files to update:
- `templates/public/base.html` (logo and footer)
- `templates/public/home.html` (hero section)
- All other template files

### Update Contact Information

In `public/views.py`, update the `contact_info` dictionary in `contact_school()` function:

```python
contact_info = {
    'address': 'Your School Address',
    'phone': '+254 YOUR NUMBER',
    'email': 'your@email.com',
    'principal': 'Your Principal Name',
    'deputy_principal': 'Your Deputy Name',
    'office_hours': 'Your Office Hours'
}
```

### Change Colors

The main colors are defined in `templates/public/base.html` CSS:

- Primary Blue: `#1e3c72`
- Secondary Blue: `#2a5298`
- Gold Accent: `#ffd700`

Update these hex values in the CSS section to match your school colors.

### Add School Logo

Currently uses text emoji (📚). To add a real logo:

1. Place logo image in `static/images/logo.png`
2. In `templates/public/base.html`, replace:
   ```html
   <span>📚</span>
   ```
   with:
   ```html
   <img src="{% static 'images/logo.png' %}" alt="Logo" style="height: 40px;">
   ```

### Update News Items

In `public/views.py`, in `news_and_updates()` function, update the `news_items` list with your school's news.

### Add Images to Gallery

In `public/views.py`, in `gallery_and_events()` function, update the `gallery_images` list to point to actual image files.

---

## 🛠️ Troubleshooting

### Login Not Working

1. Check if user exists: `python manage.py shell`
   ```python
   from accounts.models import CustomUser
   CustomUser.objects.all()
   ```

2. Ensure `is_active` is `True` for the user

3. Check if user_type is set correctly (1 for HOD, 2 for Staff)

### Static Files Not Loading

1. Run: `python manage.py collectstatic`
2. Check `STATIC_ROOT` and `STATICFILES_DIRS` in settings.py
3. Ensure files are in correct directories

### Database Issues

1. Check MySQL connection in settings.py
2. Run migrations: `python manage.py migrate`
3. Check database credentials

---

## 📚 Additional Features

### Contact Form

The contact form sends messages but currently just displays a success message. To enable email:

1. Update settings.py with email configuration:
   ```python
   EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
   EMAIL_HOST = 'smtp.gmail.com'
   EMAIL_PORT = 587
   EMAIL_USE_TLS = True
   EMAIL_HOST_USER = 'your_email@gmail.com'
   EMAIL_HOST_PASSWORD = 'your_password'
   ```

2. Update `contact_school()` view to send email (see Django email documentation)

### Responsive Design

The website is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile phones

Test by resizing browser window or using mobile device.

---

## 📖 File Structure

```
matimbwa/
├── public/                 # Public app
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py
│   └── views.py
├── templates/public/       # Public app templates
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── academic_programs.html
│   ├── news.html
│   ├── gallery.html
│   ├── contact.html
│   └── login.html
├── config/                 # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/               # User authentication
├── students/               # Student management
├── results/                # Results management
├── core/                   # Core functionality
└── manage.py
```

---

## 🎯 Next Steps

1. **Customize Content:** Update all school-specific information
2. **Add Images:** Replace placeholders with actual school photos
3. **Enable Email:** Set up email configuration for contact form
4. **Deploy:** Prepare for production deployment
5. **Add Features:** Implement online admission form, fee payment, etc.

---

## ❓ FAQ

**Q: How do I add more staff members to the leadership section?**  
A: Edit the `contact_school()` function in `public/views.py` or create a Staff model.

**Q: Can I translate the website to Swahili?**  
A: Yes, use Django's translation framework (i18n).

**Q: How do I add more student clubs?**  
A: Edit the `gallery_and_events()` view in `public/views.py`.

**Q: Can multiple users have the same username?**  
A: No, Django enforces unique usernames.

---

For more detailed information, see `PUBLIC_WEBSITE_README.md`

**Last Updated:** January 2025
