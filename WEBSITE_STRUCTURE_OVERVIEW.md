# 🎓 Matimbwa Secondary School - Website Structure Overview

## 🌍 Website Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  MATIMBWA SECONDARY SCHOOL WEBSITE                  │
│                     http://localhost:8000/                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────┬──────────┬┴─┬──────────┬──────────┬────────┐
        │              │          │  │          │          │        │
        ▼              ▼          ▼  ▼          ▼          ▼        ▼
    ┌────────┐    ┌────────┐  ┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │  HOME  │    │ ABOUT  │  │ PROGRAMS│ │ NEWS  │ │GALLERY │ │CONTACT │
    │   /    │    │/about/ │  │/programs│ │/news/ │ │/gallery│ │/contact│
    └────────┘    └────────┘  └─────────┘ └────────┘ └────────┘ └────────┘
        │              │          │         │          │          │
        │ Overview     │ History  │ Science │Announce- │ Events   │ Form
        │ Stats        │ Mission  │ Arts    │ments     │ Sports   │ FAQ
        │ Features     │ Values   │ Tech    │ Updates  │ Clubs    │ Info
        │ Links        │ Leadership         │ Calendar │ Activities
        │              │ Facilities         │ Events   │ Gallery


                    ┌──────────────────────┬──────────────────────┐
                    │   PROTECTED PAGES    │   EXTERNAL LINKS     │
                    │   (Authentication)   │   (Admin, etc.)      │
                    ├──────────────────────┼──────────────────────┤
                    │                      │                      │
                    ▼                      ▼                      ▼
                ┌────────┐            ┌──────────┐           ┌───────┐
                │ LOGIN  │            │ LOGOUT   │           │ ADMIN │
                │/login/ │            │/logout/  │           │/admin/│
                └────────┘            └──────────┘           └───────┘
                    │                      │
                    │ Authenticate         │ Redirect to Home
                    │                      │
                    ├──────────┬───────────┤
                    │          │           │
                    ▼          ▼           ▼
              Type 1 (HOD)  Type 2 (Staff)  Guest
                  │           │             │
                  ▼           ▼             ▼
              Dashboard    Dashboard    Public Site
```

---

## 📄 Page Structure & Navigation

### Page Hierarchy

```
ROOT (/)
│
├── Home (/) - Overview
│   ├── → About (link)
│   ├── → Programs (link)
│   └── → Contact (link)
│
├── About (/about/) - School Information
│   ├── History
│   ├── Mission & Vision
│   ├── Core Values
│   ├── Leadership
│   └── Facilities
│
├── Programs (/programs/) - Academic Offerings
│   ├── Science Stream
│   │   ├── Subjects
│   │   └── Careers
│   ├── Arts Stream
│   │   ├── Subjects
│   │   └── Careers
│   └── Technical Stream
│       ├── Subjects
│       └── Careers
│
├── News (/news/) - Updates & Events
│   ├── News Items (5)
│   ├── Announcements (6)
│   ├── Events (5)
│   └── Calendar
│
├── Gallery (/gallery/) - Events & Activities
│   ├── Featured Events (4)
│   ├── Campus Gallery (6 locations)
│   └── Activities
│       ├── Sports
│       ├── Clubs
│       ├── Community Service
│       ├── Cultural Events
│       ├── Academic Events
│       └── Student Leadership
│
├── Contact (/contact/) - Communication
│   ├── Contact Information
│   ├── Contact Form
│   ├── FAQ (6 items)
│   └── Map/Location
│
├── Login (/login/) - Authentication
│   ├── Username/Password
│   └── User Types
│       ├── HOD/Principal
│       └── Staff
│
└── Logout (/logout/) - Signout
    └── Redirect to Home
```

---

## 🎨 Design System

### Color Palette
```
┌─────────────────────────────────────────────────┐
│ Primary Blue          │ #1e3c72                 │ ████████
│ Secondary Blue        │ #2a5298                 │ ████████
│ Accent Gold           │ #ffd700                 │ ████████
│ Light Background 1    │ #f0f4f8                 │ ████████
│ Light Background 2    │ #f9f9f9                 │ ████████
│ Light Yellow          │ #fff3cd                 │ ████████
│ Light Blue            │ #d1ecf1                 │ ████████
│ Light Green           │ #d4edda                 │ ████████
│ Light Red             │ #f8d7da                 │ ████████
│ Light Gray            │ #e2e3e5                 │ ████████
└─────────────────────────────────────────────────┘
```

### Typography
```
Headings:      Bold, large sizes (1.3rem - 2.5rem)
Body Text:     Regular, 1rem - 1.1rem
Links:         Blue (#2a5298), underline on hover
Buttons:       Gold background, bold text
Form Labels:   Bold, dark blue
```

---

## 📊 Content Organization

### Homepage Content Flow
```
┌─────────────────────────────────────────┐
│         HERO SECTION                    │
│  Welcome Message + School Overview      │
│  CTA Buttons: Learn More | Explore      │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│      6 FEATURE CARDS                    │
│  Quality Ed. │ Modern Facilities        │
│  Expert Teachers │ Achievements         │
│  Student Support │ Holistic Dev.        │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│      STATISTICS SECTION                 │
│  850+ Students │ 120+ Staff             │
│  40+ Years │ 95% Pass Rate              │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│      CALL TO ACTION                     │
│  Ready to Join Us?                      │
│  [Contact Us Today Button]              │
└─────────────────────────────────────────┘
```

### About Page Structure
```
┌─────────────────────────────────────────┐
│      SCHOOL HISTORY                     │
│  40 years of service since 1985         │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│    MISSION & VISION                     │
│  Italicized statements                  │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│     CORE VALUES (6)                     │
│  Color-coded value cards                │
│  Integrity │ Excellence │ Respect       │
│  Responsibility │ Teamwork │ Innovation │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│    LEADERSHIP PROFILES (3)              │
│  Photos (icons) + Names + Titles        │
│  + Qualifications + Experience          │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│    SCHOOL FACILITIES (10+)              │
│  Checked list of all facilities         │
└─────────────────────────────────────────┘
```

---

## 🔐 Authentication Flow

### Login Process
```
User
  │
  ├─ Not Authenticated
  │   └─ Can access all PUBLIC pages
  │       (Home, About, Programs, News, Gallery, Contact)
  │
  ├─ Visits /login/
  │   └─ Enters username & password
  │       │
  │       ├─ Credentials VALID?
  │       │   ├─ YES → Check user_type
  │       │   │    ├─ Type 1 (HOD) → Admin Dashboard
  │       │   │    └─ Type 2 (Staff) → Staff Dashboard
  │       │   │
  │       │   └─ NO → Error Message (try again)
  │       │
  │       └─ User is_active = False? → Access Denied
  │
  └─ Authenticated User
      ├─ Can access PROTECTED pages (dashboard)
      ├─ Login button shows → "Welcome, [username]"
      ├─ Logout button available
      └─ Click Logout → Redirect to Home
```

---

## 📱 Responsive Breakpoints

### Layout Adaptation
```
MOBILE (< 768px)
│
├─ Single Column Layout
├─ Stacked Cards
├─ Full-Width Buttons
├─ Hamburger Menu (ready)
└─ Touch-Friendly Sizes

        ↓ (768px)

TABLET (768px - 1024px)
│
├─ 2 Column Grid
├─ Side-by-Side Cards
├─ Medium Buttons
└─ Optimized Spacing

        ↓ (1024px)

DESKTOP (> 1024px)
│
├─ 3+ Column Grid
├─ Full Layout
├─ Standard Buttons
└─ Maximum Content Width (1200px)
```

---

## 🛠️ Technical Stack Visualization

```
┌──────────────────────────────────────────────────┐
│              FRONTEND (HTML + CSS)               │
│  ├─ 8 HTML Templates                            │
│  ├─ Inline CSS (responsive)                     │
│  └─ Modern Semantics                            │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│          DJANGO FRAMEWORK (4.2.27)               │
│  ├─ URL Routing                                 │
│  ├─ View Functions (8)                          │
│  ├─ Template Rendering                          │
│  ├─ Form Handling                               │
│  ├─ Authentication System                       │
│  └─ Session Management                          │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│           PYTHON BACKEND LOGIC                   │
│  ├─ Data Processing                             │
│  ├─ User Authentication                         │
│  ├─ Form Validation                             │
│  └─ Business Logic                              │
└──────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────┐
│          DATABASE (MySQL)                        │
│  ├─ Users (CustomUser)                          │
│  ├─ Sessions                                    │
│  └─ Custom Data Models                          │
└──────────────────────────────────────────────────┘
```

---

## 📈 Traffic Flow

### User Journey - Public Visitor
```
Entry Point (/)
    ↓
Home Page
    ├─ Reads Overview
    ├─ Clicks Links
    └─ Options:
        ├─ Learn More → /about/
        ├─ See Programs → /programs/
        ├─ Check News → /news/
        ├─ View Activities → /gallery/
        ├─ Get Help → /contact/
        ├─ Sign In → /login/
        └─ Exit
```

### User Journey - Staff Login
```
Entry Point (/)
    ↓
Click Login → /login/
    ↓
Enter Credentials
    ├─ Username
    └─ Password
        ↓
    Validation
        ├─ Valid?
        │   └─ Check user_type
        │       ├─ Type 2 (Staff)
        │       └─ Redirect to Dashboard
        │
        └─ Invalid?
            └─ Show Error
                ├─ Retry Login
                └─ Contact Admin
```

---

## 🎯 Feature Distribution

### By Page
```
Home          │ ████████████ │ 12% - Overview & Navigation
About         │ ████████████ │ 12% - Information & Leadership
Programs      │ ████████████ │ 12% - Academic Details
News          │ ████████████ │ 12% - Updates & Calendar
Gallery       │ ████████████ │ 12% - Events & Activities
Contact       │ ████████████ │ 12% - Communication & Help
Login         │ ████████     │ 8%  - Authentication
Navigation    │ ███████████  │ 14% - Header & Footer
```

### By Content Type
```
Text Content  │ ███████████████████████ │ 45%
Forms         │ ████████                │ 10%
Navigation    │ ███████                 │ 15%
Information   │ █████████               │ 20%
Media (ready) │ ██                      │ 10%
```

---

## 🎓 Learning Resources

### Django Concepts Used
```
✓ URL Routing (urls.py patterns)
✓ View Functions (function-based views)
✓ Templates (template rendering)
✓ Static Files (CSS, images)
✓ Forms (form handling & validation)
✓ Authentication (login, logout)
✓ Sessions (user sessions)
✓ Models (database interaction)
✓ Middleware (request processing)
✓ CSRF Protection (security)
```

---

## 📞 Quick Reference

### URLs
```
/                    → public_home()
/about/              → about_school()
/programs/           → academic_programs()
/news/               → news_and_updates()
/gallery/            → gallery_and_events()
/contact/            → contact_school()
/login/              → public_login()
/logout/             → public_logout()
```

### Files
```
Views:        public/views.py
URLs:         public/urls.py
Templates:    templates/public/*.html
Settings:     config/settings.py
```

### Key Functions
```
public_home()              - 1 page
about_school()            - 1 page
academic_programs()       - 1 page + 3 streams
news_and_updates()        - 5 news + 5 events + calendar
gallery_and_events()      - 4 events + 6 gallery + 6 activities
contact_school()          - form + info + 6 FAQs
public_login()            - authentication
public_logout()           - sign out
```

---

## ✨ Summary

```
┌─────────────────────────────────────────────┐
│    MATIMBWA SECONDARY SCHOOL WEBSITE        │
├─────────────────────────────────────────────┤
│ 6 Public Pages         ✓ Accessible         │
│ 1 Login Page           ✓ Secure             │
│ 1 Logout Function      ✓ Session-based      │
│ 8 View Functions       ✓ Well-organized     │
│ 8 HTML Templates       ✓ Responsive         │
│ Contact Form           ✓ Working            │
│ Navigation System      ✓ Complete           │
│ Mobile Design          ✓ Optimized          │
│ Security               ✓ CSRF Protected     │
│ Documentation          ✓ Comprehensive      │
└─────────────────────────────────────────────┘
```

---

**Status:** ✅ Complete and Ready to Use  
**Last Updated:** January 2025  
**Version:** 1.0
