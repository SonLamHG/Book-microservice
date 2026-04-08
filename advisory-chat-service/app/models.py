from django.db import models
from pgvector.django import VectorField, HnswIndex


class KnowledgeDocument(models.Model):
    """Stores KB documents with vector embeddings for RAG retrieval."""
    SOURCE_CHOICES = [
        ('policy', 'Store Policy'),
        ('faq', 'FAQ'),
        ('book_catalog', 'Book Catalog'),
        ('genre_guide', 'Genre Guide'),
    ]
    title = models.CharField(max_length=255)
    content = models.TextField()
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    embedding = VectorField(dimensions=384)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(
                name='kb_embedding_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            )
        ]

    def __str__(self):
        return f"[{self.source}] {self.title}"


class ChatSession(models.Model):
    customer_id = models.IntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session #{self.pk} (customer={self.customer_id})"


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    context_used = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class CustomerBehaviorSummary(models.Model):
    SEGMENT_CHOICES = [
        ('new', 'New Customer'),
        ('active', 'Active'),
        ('loyal', 'Loyal'),
        ('at_risk', 'At Risk'),
        ('churned', 'Churned'),
    ]
    customer_id = models.IntegerField(unique=True)
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    favorite_categories = models.JSONField(default=list)
    favorite_authors = models.JSONField(default=list)
    avg_rating_given = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    purchase_frequency_days = models.FloatField(null=True)
    last_order_date = models.DateTimeField(null=True)
    segment = models.CharField(max_length=20, choices=SEGMENT_CHOICES, default='new')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customer #{self.customer_id} [{self.segment}]"
