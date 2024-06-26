from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Avg



class User(AbstractUser):
    name = models.CharField(max_length=200, null=True)
    email = models.EmailField(unique=True, null=True)
    bio = models.TextField(null=True)

    avatar = models.ImageField(null=True, default="avatar.svg")

    ROLE_CHOICES = (
        ('eleve', 'Élève'),
        ('professeur', 'Professeur'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='eleve')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username


class Topic(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Room(models.Model):
    host = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    participants = models.ManyToManyField(
        User, related_name='participants', blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    rating = models.FloatField(default=0.0)
    paye = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Ajout du champ price
    payees = models.ManyToManyField(User, related_name='paid_rooms')
    file = models.FileField(upload_to='room_files/', blank=True, null=True)



    def update_rating(self):
        ratings = self.ratings.all().aggregate(Avg('rating'))
        self.rating = ratings['rating__avg'] or 0.0
        self.save()

    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return self.name
    

class RoomRating(models.Model):
    room = models.ForeignKey(Room, related_name='ratings', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.room.update_rating()


class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    body = models.TextField()
    file = models.FileField(upload_to='message_files/', null=True, blank=True)  # Chemin où les fichiers seront stockés
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return self.body[0:50]