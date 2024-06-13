from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout

from studybud import settings
from .models import Room, Topic, Message, User, RoomRating
from .forms import RateForm, RoomForm, UserForm, MyUserCreationForm
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Avg
from paypalrestsdk import Payment, configure





def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)  

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Email or password is incorrect') 

    return render(request, 'base/login_register.html', {'page': 'login'})


def logoutUser(request):
    logout(request)
    return redirect('home')


def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error occurred during registration'+str(form.errors))

    return render(request, 'base/login_register.html', {'form': form})


def home(request):
    q = request.GET.get('q') if request.GET.get('q') is not None else ''

    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description__icontains=q)
    ).annotate(average_rating=Avg('ratings__rating'))  
    
    paid_rooms = Room.objects.none()
    unpaid_rooms = rooms.order_by('-created')

    
    if request.user.is_authenticated:
        paid_rooms = rooms.filter(payees=request.user).order_by('-created')
        unpaid_rooms = rooms.exclude(payees=request.user).order_by('-created')

    topics = Topic.objects.all()[0:5]
    room_count = rooms.count()
    room_messages = Message.objects.filter(
        Q(room__topic__name__icontains=q)
    )[0:3]

    context = {
        'paid_rooms': paid_rooms,
        'unpaid_rooms': unpaid_rooms,
        'topics': topics,
        'room_count': room_count,
        'room_messages': room_messages
    }
    return render(request, 'base/home.html', context)



@login_required(login_url="login")
def room(request, pk):
    room = get_object_or_404(Room, id=pk)
    if request.user not in room.payees.all():
        messages.error(request, "Vous devez payer pour accéder à cette room.")
        return redirect('home')

    room_messages = room.message_set.all()
    participants = room.participants.all()
    ratings = RoomRating.objects.filter(room=room)
    average_rating = ratings.aggregate(Avg('rating'))['rating__avg'] if ratings.exists() else "Pas encore notée"
    form = RateForm()

    if request.method == 'POST':
        if 'rate' in request.POST:
            form = RateForm(request.POST)
            if form.is_valid():
                rating = form.cleaned_data['rating']
                rating_obj, created = RoomRating.objects.update_or_create(
                    user=request.user,
                    room=room,
                    defaults={'rating': rating}
                )
                room.update_rating()
                messages.success(request, "Votre note a été enregistrée.")
                return redirect('room', pk=room.id)
        else:
            body = request.POST.get('body')
            message = Message(user=request.user, room=room, body=body)
            if 'file' in request.FILES:
                message.file = request.FILES['file']
            message.save()
            room.participants.add(request.user)
            return redirect('room', pk=room.id)

    context = {
        'room': room,
        'room_messages': room_messages,
        'participants': participants,
        'ratings': ratings,
        'average_rating': average_rating,
        'form': form
    }
    return render(request, 'base/room.html', context)


def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    topics = Topic.objects.all()
    context = {'user': user, 'rooms': rooms,
               'room_messages': room_messages, 'topics': topics}
    return render(request, 'base/profile.html', context)


@login_required(login_url='login')
def createRoom(request):
    if not request.user.is_authenticated or request.user.role != 'professeur':
        messages.error(request, "Vous n'avez pas accès à cette page.")
        return redirect("home")

    if request.method == "POST":
        form = RoomForm(request.POST, request.FILES)  
        if form.is_valid():
            topic_name = request.POST.get('topic')
            topic, created = Topic.objects.get_or_create(name=topic_name)
            
            room = form.save(commit=False)
            room.host = request.user
            room.topic = topic
            room.save()
            form.save_m2m()  
            room.payees.add(request.user)
            
            messages.success(request, "Room created successfully.")
            return redirect("home")
        else:
            messages.error(request, "Form is not valid.")
    else:
        form = RoomForm()
    
    topics = Topic.objects.all()
    context = {"form": form, "topics": topics}
    return render(request, "base/room_form.html", context)


@login_required(login_url='login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room, data=request.POST or None, files=request.FILES or None)  
    topics = Topic.objects.all()
    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        if form.is_valid():
            room = form.save(commit=False)
            room.topic = topic
            room.save()
            form.save_m2m()  
            return redirect('home')

    context = {'form': form, 'topics': topics, 'room': room}
    return render(request, 'base/room_form.html', context)


@login_required
def rate_room(request, room_id, rating):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        rating_obj, created = RoomRating.objects.update_or_create(
            user=request.user,
            room=room,
            defaults={'rating': rating}
        )
        room.update_rating()  
        messages.success(request, "Votre note a été enregistrée.")
        return redirect('room_detail', room_id=room_id)  
    return redirect('home' )


@login_required(login_url='login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HttpResponse('Your are not allowed here!!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': room})


@login_required(login_url='login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse('Your are not allowed here!!')

    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': message})


@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    return render(request, 'base/update-user.html', {'form': form})


def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    topics = Topic.objects.filter(name__icontains=q)
    return render(request, 'base/topics.html', {'topics': topics})


def activityPage(request):
    room_messages = Message.objects.all()
    return render(request, 'base/activity.html', {'room_messages': room_messages})




@login_required(login_url='login')
def process_payment(request):
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        room = Room.objects.get(id=room_id)

        
        configure({
            "mode": "sandbox",  
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_SECRET_KEY
        })

        
        payment = Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "http://localhost:8000/payment/execute",
                "cancel_url": "http://localhost:8000/"},
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": room.name,
                        "sku": room.id,
                        "price": str(float(room.price)),
                        "currency": "EUR",
                        "quantity": 1}]},
                "amount": {
                    "total": str(float(room.price)),
                    "currency": "EUR"},
                "description": f"Payment for room {room.name}."}]
        })

        try:
            if payment.create():
                for link in payment.links:
                    if link.method == "REDIRECT":
                        redirect_url = link.href
                        return redirect(redirect_url)
            else:
                messages.error(request, "Une erreur est survenue lors de la création du paiement.")
        except Exception as e:
            messages.error(request, f"Une erreur est survenue : {str(e)}")

    return redirect('home')

def execute_payment(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    configure({
        "mode": "sandbox", 
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_SECRET_KEY
    })

    try:
        payment = Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            room_id = payment.transactions[0].item_list.items[0].sku
            room = Room.objects.get(id=room_id)
            room.paye = True
            room.payees.add(request.user)
            room.save()

            messages.success(request, "Paiement réussi !")
            return redirect('room', pk=room.id)
        else:
            messages.error(request, "Le paiement a échoué.")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue : {str(e)}")

    return redirect('home')