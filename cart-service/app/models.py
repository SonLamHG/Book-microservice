from django.db import models
from django.core.validators import MinValueValidator


class Cart(models.Model):
    customer_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for customer {self.customer_id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    book_id = models.IntegerField()
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ('cart', 'book_id')

    def __str__(self):
        return f"Book {self.book_id} x{self.quantity}"
