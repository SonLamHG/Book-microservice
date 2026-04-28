from rest_framework import serializers
from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name"]


class ProductSerializer(serializers.ModelSerializer):
    """
    Output format compatible with ai-service:
    { id, name, price, description, category: {slug, name}, updated_at }
    """
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price", "stock",
            "category", "category_id",
            "author", "isbn", "publisher", "published_year",
            "language", "pages",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]