from django.db import models
import uuid


class Shipment(models.Model):
    METHOD_CHOICES = [
        ('STANDARD', 'Standard'),
        ('EXPRESS', 'Express'),
    ]
    STATUS_CHOICES = [
        ('RESERVED', 'Reserved'),
        ('PENDING', 'Pending'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
    ]
    order_id = models.IntegerField()
    address = models.TextField()
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='STANDARD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    tracking_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = f"TRK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Shipment for Order #{self.order_id} - {self.status}"
