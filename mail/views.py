import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render

# Create your views here.
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from mail.models import User, Email






def index(request):
    if request.user.is_authenticated:
        return render(request, 'mail/inbox.html')
    else:
        return HttpResponseRedirect(reverse('login'))


@csrf_exempt
@login_required
def compose(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Request POST required'},
                            status=400)
    data = json.loads(request.body)
    emails = [email.strip() for email in data.get('recipients').split(',')]
    if emails == ['']:
        return JsonResponse({'error': 'At least 1 recipent required'},
                            status=400)
    recipients = []
    for email in emails:
        try:
            user = User.objects.get(email=email)
            recipients.append(user)
        except User.DoesNotExist:
            return JsonResponse({'error': f'user with email: {email} does not exist'},
                                status=400)
    subject = data.get('subject', '')
    body = data.get('body', '')

    users = set()
    users.add(request.user)
    users.update(recipients)
    for user in users:
        email = Email(
            user = user,
            sender = request.user,
            subject=subject,
            body=body,
            read=user==request.user
        )
        email.save()
        for recipient in recipients:
            email.recipients.add(recipient)
        email.save()
    return JsonResponse({'message': 'Email send successfully', 'status': 201},
                        status=201)

@login_required
def mailbox(request, mailbox):
    if mailbox == 'inbox':
        emails = Email.objects.filter(user=request.user, recipients=request.user, archived=False)
    elif mailbox == 'sent':
        emails = Email.objects.filter(user=request.user, sender=request.user)
    elif mailbox == 'archive':
        emails = Email.objects.filter(user=request.user, recipients=request.user, archived=True)
    else:
        return JsonResponse({'error': 'Invalid mailbox'},
                            status=400)
    emails = emails.order_by('-timestamp').all()
    return JsonResponse([email.serialize() for email in emails ], safe=False)


@csrf_exempt
@login_required
def email(request, email_id):
    try:
        email = Email.objects.get(user=request.user, id=email_id)
    except Email.DoesNotExist:
        return JsonResponse({'error': 'Email not found'},
                            status=404)
    if request.method == 'GET':
        return JsonResponse(email.serialize())

    elif request.method == 'PUT':
        data = json.loads(request.body)
        if data.get('read') is not None:
            email.read = data['read']
        if data.get('archived') is not None:
            email.archived = data['archived']
        email.save()
        return HttpResponse(status=204)
    else:
        return JsonResponse({'error': 'Request method PUT or GET required'},
                            status=400)



def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        email = request.POST["email"]
        password = request.POST["password"]
        user = authenticate(request, username=email, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "mail/login.html", {
                "message": "Invalid email and/or password."
            })
    else:
        return render(request, "mail/login.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))

def register(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        confirmation = request.POST['confirmation']

        if password != confirmation:
            return render(request, 'mail/register.html', {
                'message': 'Passwords must match.'
            })
        try:
            user = User.objects.create_user(email, email, password)
            user.save()
        except IntegrityError:
            return render(request, 'mail/register.html', {
                'message': 'Email already exist'
            })
        login(request, user)
        return HttpResponseRedirect(reverse('index'))
    else:
        return render(request, 'mail/register.html')



