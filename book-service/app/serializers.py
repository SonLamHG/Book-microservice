from rest_framework import serializers
from .models import Product, Book, Electronics, Fashion


class ProductSerializer(serializers.ModelSerializer):
    """Generic product representation — returned by /products/ endpoints."""
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'stock', 'category_id',
                  'description', 'product_type', 'created_at']
        read_only_fields = ['created_at']


class BookSerializer(serializers.ModelSerializer):
    """Flattens Product + Book fields. Maintains the legacy /books/ contract:
    consumers receive {id, title, author, price, stock, category_id, isbn, description, created_at}.
    `id` is the Product PK, which equals book_id for downstream services (cart/order/review).
    """
    id = serializers.IntegerField(source='product.id', read_only=True)
    title = serializers.CharField(source='product.name')
    price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2)
    stock = serializers.IntegerField(source='product.stock', required=False, default=0)
    category_id = serializers.IntegerField(source='product.category_id', required=False, allow_null=True)
    description = serializers.CharField(source='product.description', required=False, allow_blank=True, default='')
    created_at = serializers.DateTimeField(source='product.created_at', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'publisher', 'isbn',
                  'price', 'stock', 'category_id', 'description', 'created_at']

    def create(self, validated_data):
        product_data = validated_data.pop('product', {})
        product = Product.objects.create(product_type='book', **product_data)
        return Book.objects.create(product=product, **validated_data)

    def update(self, instance, validated_data):
        product_data = validated_data.pop('product', {})
        for k, v in product_data.items():
            setattr(instance.product, k, v)
        instance.product.save()
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance


class ElectronicsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='product.id', read_only=True)
    name = serializers.CharField(source='product.name')
    price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2)
    stock = serializers.IntegerField(source='product.stock', required=False, default=0)
    category_id = serializers.IntegerField(source='product.category_id', required=False, allow_null=True)
    description = serializers.CharField(source='product.description', required=False, allow_blank=True, default='')
    created_at = serializers.DateTimeField(source='product.created_at', read_only=True)

    class Meta:
        model = Electronics
        fields = ['id', 'name', 'brand', 'warranty_months',
                  'price', 'stock', 'category_id', 'description', 'created_at']

    def create(self, validated_data):
        product_data = validated_data.pop('product', {})
        product = Product.objects.create(product_type='electronics', **product_data)
        return Electronics.objects.create(product=product, **validated_data)

    def update(self, instance, validated_data):
        product_data = validated_data.pop('product', {})
        for k, v in product_data.items():
            setattr(instance.product, k, v)
        instance.product.save()
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance


class FashionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='product.id', read_only=True)
    name = serializers.CharField(source='product.name')
    price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2)
    stock = serializers.IntegerField(source='product.stock', required=False, default=0)
    category_id = serializers.IntegerField(source='product.category_id', required=False, allow_null=True)
    description = serializers.CharField(source='product.description', required=False, allow_blank=True, default='')
    created_at = serializers.DateTimeField(source='product.created_at', read_only=True)

    class Meta:
        model = Fashion
        fields = ['id', 'name', 'size', 'color', 'material',
                  'price', 'stock', 'category_id', 'description', 'created_at']

    def create(self, validated_data):
        product_data = validated_data.pop('product', {})
        product = Product.objects.create(product_type='fashion', **product_data)
        return Fashion.objects.create(product=product, **validated_data)

    def update(self, instance, validated_data):
        product_data = validated_data.pop('product', {})
        for k, v in product_data.items():
            setattr(instance.product, k, v)
        instance.product.save()
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance
