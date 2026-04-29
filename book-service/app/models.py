from django.db import models
from django.core.validators import MinValueValidator


PRODUCT_TYPE_CHOICES = (
    ('book', 'Book'),
    ('electronics', 'Electronics'),
    ('fashion', 'Fashion'),
)


class Product(models.Model):
    """Base product entity. Each row maps 1:1 to exactly one of Book / Electronics / Fashion."""
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    category_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='book')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'[{self.product_type}] {self.name}'


class Book(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name='book_detail'
    )
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255, blank=True, default='')
    isbn = models.CharField(max_length=13, blank=True, default='')

    def __str__(self):
        return f'{self.product.name} — {self.author}'


class Electronics(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name='electronics_detail'
    )
    brand = models.CharField(max_length=100)
    warranty_months = models.IntegerField(default=12, validators=[MinValueValidator(0)])

    def __str__(self):
        return f'{self.product.name} ({self.brand})'


class Fashion(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name='fashion_detail'
    )
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50, blank=True, default='')
    material = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return f'{self.product.name} ({self.size}/{self.color})'
