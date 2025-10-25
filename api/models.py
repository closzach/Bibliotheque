from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
import os
from django.utils.timezone import now
from PIL import Image
from django.dispatch import receiver
from django.db.models.signals import pre_delete, pre_save
from django.core.validators import RegexValidator

class Auteur(models.Model):
    nom = models.CharField(max_length=100)
    date_naissance = models.DateField(null=True, blank=True)
    date_mort = models.DateField(null=True, blank=True)
    biographie = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nom
    
    class Meta:
        permissions = (
            ("creer_auteur", "Peut créer un auteur."),
            ("modifier_auteur", "Peut modifier un auteur."),
            ("supprimer_auteur", "Peut supprimer un auteur.")
        )

class Tag(models.Model):
    tag = models.CharField(max_length=100)
    pour_adulte = models.BooleanField()
    modifiable = models.BooleanField(default=True)

    def __str__(self):
        return self.tag
    
    class Meta:
        permissions = (
            ('creer_tag', 'Peut créer un tag.'),
            ('modifier_tag', 'Peut modifier un tag.'),
            ('supprimer_tag', 'Peut supprimer un tag.'),
        )

def renommer_image(instance, filename):
        extension = os.path.splitext(filename)[1]
        nouveau_nom = f"{instance.id}_{instance.nom}_{now().strftime('%Y%m%d%H%M%S')}{extension}"
        return os.path.join("livres", nouveau_nom)
class Livre(models.Model):
    nom = models.CharField(max_length=100)
    date_sortie = models.DateField()
    nombre_pages = models.IntegerField()
    synopsis = models.TextField()
    edition = models.CharField(max_length=100, blank=True, null=True)
    isbn = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d+$', 'Seuls les chiffres sont autorisés.')]
    )
    image = models.ImageField(
        upload_to=renommer_image,
        default="default.png",
        blank=True
    )

    auteurs = models.ManyToManyField(Auteur)
    tags = models.ManyToManyField(Tag)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            img_path = self.image.path
            with Image.open(img_path) as img:
                max_size = (800, 1200)
                img.thumbnail(max_size)
                img.save(img_path)

    def __str__(self):
        return self.nom

    class Meta:
        permissions = (
            ('creer_livre', 'Peut créer un livre.'),
            ('modifier_livre', 'Peut modifier un livre.'),
            ('suppression_livre', 'Peut supprimer un livre.')
        )

@receiver(pre_delete, sender=Livre)
def supprimer_image_livre(sender, instance, **kwargs):
    if instance.image and instance.image.name != "default.png":
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

@receiver(pre_save, sender=Livre)
def remplacer_image_livre(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien_livre = Livre.objects.get(pk=instance.pk)
            if ancien_livre.image and ancien_livre.image.name != "default.png" and (not instance.image or ancien_livre.image != instance.image):
                if os.path.isfile(ancien_livre.image.path):
                    os.remove(ancien_livre.image.path)
        except Livre.DoesNotExist:
            pass

class User(AbstractUser):
    date_naissance = models.DateField()
    cacher_pour_adulte = models.BooleanField(default=True)
    liste_de_souhaits = models.ManyToManyField(Livre)

    REQUIRED_FIELDS = ['date_naissance']

    def __str__(self):
        return self.username

class Lecture(models.Model):
    STATUT_CHOICES = [
        ('a lire', 'À lire'),
        ('lu', 'Lu'),
        ('en cours', 'En cours'),
        ('abandonne', 'Abandonné'),
        ('en pause', 'En pause'),
    ]

    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES)
    note = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(i, f"{i}") for i in range(1, 6)],
        verbose_name="Note"
    )
    marque_pages = models.PositiveIntegerField(null=True, blank=True)
    commentaire = models.TextField(null=True, blank=True)

    livre = models.ForeignKey(Livre, on_delete=models.CASCADE)
    lecteur = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['livre', 'lecteur'], name='unique_livre_lecteur')
        ]

    def save(self, *args, **kwargs):
        if self.statut == 'lu' and self.livre and hasattr(self.livre, 'nombre_pages'):
            self.marque_pages = self.livre.nombre_pages
        super().save(*args, **kwargs)
