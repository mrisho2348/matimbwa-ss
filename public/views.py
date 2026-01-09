from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import CustomUser, AdminHOD
from django.http import JsonResponse
from accounts.models import Staffs


def public_home(request):
    """Public home page for Matimbwa Secondary School"""
    context = {
        'page_title': 'Matimbwa Secondary School - Home'
    }
    return render(request, 'public/home.html', context)


def about_school(request):
    """About school page with history and mission"""
    context = {
        'page_title': 'About Matimbwa Secondary School'
    }
    return render(request, 'public/about.html', context)


def academic_programs(request):
    """Academic programs and curriculum"""
    programs = [
        {
            'name': 'Science Stream',
            'description': 'Physics, Chemistry, Biology, Mathematics',
            'subjects': ['Physics', 'Chemistry', 'Biology', 'Mathematics', 'English', 'Kiswahili']
        },
        {
            'name': 'Arts Stream',
            'description': 'History, Geography, Economics, Literature',
            'subjects': ['History', 'Geography', 'Economics', 'Literature in English', 'Kiswahili', 'Mathematics']
        },
        {
            'name': 'Technical Stream',
            'description': 'Woodwork, Metalwork, Electricity, Building Construction',
            'subjects': ['Woodwork', 'Metalwork', 'Electricity', 'Building Construction', 'Mathematics', 'Physics']
        }
    ]
    context = {
        'page_title': 'Academic Programs',
        'programs': programs
    }
    return render(request, 'public/academic_programs.html', context)


def news_and_updates(request):
    """News and updates from the school"""
    news_items = [
        {
            'date': 'January 2025',
            'title': 'New Computer Lab Opened',
            'content': 'Matimbwa Secondary School has officially opened a state-of-the-art computer laboratory with 50 modern computers to enhance ICT education.',
            'category': 'School News'
        },
        {
            'date': 'December 2024',
            'title': 'Science Fair 2024 Success',
            'content': 'Our students showcased innovative projects at the annual science fair. Congratulations to all participants.',
            'category': 'Academic'
        },
        {
            'date': 'November 2024',
            'title': 'Sports Day Tournament',
            'content': 'The inter-house sports competition was held successfully. Alpha house emerged as overall champions.',
            'category': 'Sports'
        },
        {
            'date': 'October 2024',
            'title': 'Environmental Conservation Project',
            'content': 'Students planted 500 trees in and around the school compound as part of environmental conservation.',
            'category': 'Environmental'
        },
        {
            'date': 'September 2024',
            'title': 'New Scholarship Program',
            'content': 'Matimbwa Secondary School announces a new scholarship program for needy but academically talented students.',
            'category': 'School News'
        }
    ]
    context = {
        'page_title': 'News and Updates',
        'news_items': news_items
    }
    return render(request, 'public/news.html', context)


def gallery_and_events(request):
    """School gallery, events and activities"""
    events = [
        {
            'name': 'Annual Speech Day',
            'date': 'December 15, 2024',
            'description': 'Celebration of academic excellence and school achievements',
            'image': 'event1.jpg'
        },
        {
            'name': 'Science Carnival',
            'date': 'November 20, 2024',
            'description': 'Interactive science demonstrations and activities',
            'image': 'event2.jpg'
        },
        {
            'name': 'Inter-School Debate',
            'date': 'October 30, 2024',
            'description': 'Debate competition between various secondary schools',
            'image': 'event3.jpg'
        },
        {
            'name': 'Career Day',
            'date': 'September 25, 2024',
            'description': 'Professional experts share career insights with students',
            'image': 'event4.jpg'
        }
    ]
    
    gallery_images = [
        {'title': 'School Main Building', 'image': 'gallery1.jpg'},
        {'title': 'Classroom Blocks', 'image': 'gallery2.jpg'},
        {'title': 'Library', 'image': 'gallery3.jpg'},
        {'title': 'Sports Field', 'image': 'gallery4.jpg'},
        {'title': 'Science Laboratory', 'image': 'gallery5.jpg'},
        {'title': 'Student Activities', 'image': 'gallery6.jpg'},
    ]
    
    context = {
        'page_title': 'Gallery and Events',
        'events': events,
        'gallery_images': gallery_images
    }
    return render(request, 'public/gallery.html', context)


def contact_school(request):
    """Contact information and form"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # You can implement email sending here
        messages.success(request, 'Thank you! Your message has been received. We will respond shortly.')
        return redirect('public_contact')
    
    contact_info = {
        'address': 'Matimbwa Secondary School, Makueni County, Kenya',
        'phone': '+254 712 345 678',
        'email': 'info@matimbwa.ac.ke',
        'principal': 'Mr. Samuel Mwalili',
        'deputy_principal': 'Mrs. Rose Kariuki',
        'office_hours': 'Monday - Friday: 8:00 AM - 5:00 PM'
    }
    
    context = {
        'page_title': 'Contact Us',
        'contact_info': contact_info
    }
    return render(request, 'public/contact.html', context)


def public_login(request):
    """
    Universal login view for HOD and Staff users
    """

    if request.user.is_authenticated:
        return redirect_user_by_type(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, "public/login.html")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid login credentials.")
            return render(request, "public/login.html")

        if not user.is_active:
            messages.error(request, "Your account is inactive. Contact administrator.")
            return render(request, "public/login.html")

        # STAFF VALIDATION
        if user.user_type == "2":
            if not hasattr(user, "staff"):
                messages.error(request, "Staff profile not found.")
                return render(request, "public/login.html")

            if not user.staff.role:
                messages.error(request, "Staff role not assigned.")
                return render(request, "public/login.html")

        login(request, user)
        messages.success(request, f"Welcome {user.get_username()}")

        return redirect_user_by_type(user)

    return render(request, "public/login.html")


def redirect_user_by_type(user):
    """
    Redirect users based on user_type and staff role
    """

    # ======================
    # HOD / ADMIN
    # ======================
    if user.user_type == "1":
        return redirect("admin_dashboard")

    # ======================
    # STAFF USERS
    # ======================
    if user.user_type == "2":
        staff = user.staff
        role = staff.role

        role_redirects = {
            "Academic": "academic_dashboard",
            "Secretary": "secretary_dashboard",
            "Headmaster": "headmaster_dashboard",
            "Accountant": "accountant_dashboard",
            "Librarian": "librarian_dashboard",
            "Administrator": "admin_staff_dashboard",
            "Staff": "staff_dashboard",
        }

        return redirect(role_redirects.get(role, "staff_dashboard"))

    # ======================
    # FALLBACK
    # ======================
    return redirect("public_home")




def public_logout(request):
    """Logout user and redirect to home"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('public_home')


def public_register(request):
    """Render registration page for staff to request/create account."""
    if request.method == 'GET':
        return render(request, 'public/register.html', {'page_title': 'Staff Registration'})


def public_register_check(request):
    """AJAX endpoint to check uniqueness of username, email and staff full name."""
    username = request.GET.get('username')
    email = request.GET.get('email')
    first_name = request.GET.get('first_name')
    middle_name = request.GET.get('middle_name')
    last_name = request.GET.get('last_name')

    data = {
        'username_available': True,
        'email_available': True,
        'staff_name_available': True,
    }

    if username:
        if CustomUser.objects.filter(username__iexact=username).exists():
            data['username_available'] = False

    if email:
        if CustomUser.objects.filter(email__iexact=email).exists():
            data['email_available'] = False

    if first_name and last_name:
        qs = Staffs.objects.filter(admin__first_name__iexact=first_name, admin__last_name__iexact=last_name)
        if middle_name:
            qs = qs.filter(middle_name__iexact=middle_name)
        if qs.exists():
            data['staff_name_available'] = False

    return JsonResponse(data)


def public_register_ajax(request):
    """AJAX endpoint to create staff account if not already registered."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    middle_name = request.POST.get('middle_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    password = request.POST.get('password', '')

    # Basic validation
    if not username or not email or not first_name or not last_name or not password:
        return JsonResponse({'success': False, 'message': 'Please provide all required fields.'}, status=400)

    if CustomUser.objects.filter(username__iexact=username).exists():
        return JsonResponse({'success': False, 'message': 'Username already taken.'}, status=400)

    if CustomUser.objects.filter(email__iexact=email).exists():
        return JsonResponse({'success': False, 'message': 'Email already registered.'}, status=400)

    qs = Staffs.objects.filter(admin__first_name__iexact=first_name, admin__last_name__iexact=last_name)
    if middle_name:
        qs = qs.filter(middle_name__iexact=middle_name)
    if qs.exists():
        return JsonResponse({'success': False, 'message': 'A staff with this full name already exists.'}, status=400)

    # create user
    try:
        user = CustomUser.objects.create_user(username=username, email=email, password=password, user_type=2)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # create Staffs profile
        Staffs.objects.create(admin=user, middle_name=middle_name)

        return JsonResponse({'success': True, 'message': 'Account created successfully. Please login.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error creating account: {str(e)}'}, status=500)
