import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
import random
import string

def generate_ext(length=10):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(length))

def generate_unique_ext(instance, length=10):
    """ Create unique ext_id of alphanumeric characters """
    ext_id = generate_ext(length)
    while not instance.__class__.objects.filter(ext_id=ext_id).exists():
        return ext_id
    return generate_unique_ext(instance, length)

class SoftDeleteManager(models.Manager):
    """
    Custom manager to filter out soft-deleted objects by default.
    """
    def get_queryset(self):
        # Only return objects where deleted_at is None
        return super().get_queryset().filter(deleted_at__isnull=True).order_by('id')
    

class BaseModel(models.Model):
    """
    Abstract base model to store common fields and handle soft deletion.
    """
    uid = models.UUIDField(default=uuid.uuid4, editable=False)
    ext_id = models.CharField(max_length=10, unique=True) #unique id 10 char length 
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set the time when an object is created.
    updated_at = models.DateTimeField(auto_now=True)      # Automatically set the time when an object is updated.
    deleted_at = models.DateTimeField(null=True, blank=True)  # Field for soft deletion timestamp
    created_user = models.ForeignKey(User, related_name='created_%(class)s_set', on_delete=models.SET_NULL, null=True)
    updated_user = models.ForeignKey(User, related_name='updated_%(class)s_set', on_delete=models.SET_NULL, null=True)
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['deleted_at']),  # Indexing the deleted_at field
        ]

    def save(self, *args, **kwargs):
        if not self.ext_id:
            self.ext_id = generate_unique_ext(self)
        super().save(*args, **kwargs)
        
    def delete(self, *args, **kwargs):
        """ Override the delete method to mark the object as deleted (soft delete) """
        user = kwargs.pop('user', None)
        if user is None:
            raise ValueError("User must be provided for logging delete action.")

        # Mark as deleted (soft delete)
        self.deleted_at = timezone.now()
        self.updated_user = user 
        self.log_action(user=self.updated_user, action_flag=DELETION, message="Object soft deleted", is_admin=False)
        self.save()


    def restore(self):
        """ Restore a soft deleted object """
        self.deleted_at = None
        self.save()
        self.log_action(user=self.updated_user, action_flag=CHANGE, message="Object restored", is_admin=False)


    def is_deleted(self):
        """ Check if the object is marked as deleted """
        return self.deleted_at is not None


    def all_logs(self):
        """
        Retrieve all logs related to this object using Django's LogEntry.
        """
        content_type = ContentType.objects.get_for_model(self)
        logs = LogEntry.objects.filter(content_type=content_type, object_id=self.pk).order_by('-action_time')

        return logs

    def log_action(self, user, action_flag, message=None, is_admin=False, code=None):
        """
        Logs an action using Django's LogEntry. 
        This method can be used across all models inheriting from BaseModel.
        """
        change_message = {
            'message': message if message else '',
            'is_admin': is_admin,
            'code': code,
        }

        LogEntry.objects.log_action(
            user_id=user.pk,
            content_type_id=ContentType.objects.get_for_model(self).pk,
            object_id=self.pk,
            object_repr=str(self),
            action_flag=action_flag,
            change_message=str(change_message)
        )


class Temple(BaseModel):
    name = models.CharField(max_length=255)
    overview = models.TextField()
    highlights = models.TextField()
    location_info = models.TextField()
    main_image_url = models.URLField()

    class Meta:
        verbose_name = "Temple"
        verbose_name_plural = "Temples"
        ordering = ['id']

    def __str__(self):
        return self.name

class TempleGalleryImage(BaseModel):
    temple = models.ForeignKey(Temple, related_name='gallery_images', on_delete=models.CASCADE)
    image_url = models.URLField()

    class Meta:
        verbose_name = "Temple Gallery Image"
        verbose_name_plural = "Temple Gallery Images"
        ordering = ['id']

    def __str__(self):
        return f"Gallery Image for {self.temple.name}"

class ArchitectureFeature(BaseModel):
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=500)
    full_description = models.TextField()

    class Meta:
        verbose_name = "Architecture Feature"
        verbose_name_plural = "Architecture Features"
        ordering = ['id']

    def __str__(self):
        return self.title

class Product(BaseModel):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image_url = models.URLField()

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['id']

    def __str__(self):
        return self.name
