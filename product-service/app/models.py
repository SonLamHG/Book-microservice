from django.db import models
from django.core.validators import MinValueValidator


class Category(models.Model):
    """Book category — maps to ai-service category.slug / category.name"""
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Unified Product model wrapping Books for ai-service consumption.
    ai-service expects: { id, name, price, description, category: {slug, name}, updated_at }
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    category = models.ForeignKey(
        Category, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="products"
    )
    # Book-specific metadata
    author = models.CharField(max_length=255, blank=True, default="")
    isbn = models.CharField(max_length=20, blank=True, default="")
    publisher = models.CharField(max_length=255, blank=True, default="")
    published_year = models.IntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, blank=True, default="vi")
    pages = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name