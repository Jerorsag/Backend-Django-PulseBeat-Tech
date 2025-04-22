from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatConversation(models.Model):
    """Modelo para almacenar conversaciones completas"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_conversations'
    )
    session_id = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # Metadata adicional para mejorar la personalización
    user_location = models.CharField(max_length=100, blank=True, null=True)
    source_page = models.CharField(max_length=255, blank=True, null=True)
    browser_info = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"
        ordering = ['-last_updated']

    def __str__(self):
        username = self.user.username if self.user else "Anónimo"
        return f"Conversación {self.id} - {username} - {self.created_at.strftime('%d/%m/%Y')}"

    def get_context_summary(self):
        """Retorna un resumen del contexto de la conversación para análisis"""
        messages = self.messages.all().order_by('timestamp')

        # Extraer preguntas del usuario y productos mencionados
        user_queries = [msg.content for msg in messages if not msg.is_bot]
        product_mentions = []

        for msg in messages:
            if not msg.is_bot and any(kw in msg.content.lower() for kw in
                                      ['producto', 'auricular', 'altavoz', 'speaker']):
                product_mentions.append(msg.content)

        return {
            'total_messages': messages.count(),
            'user_queries': user_queries,
            'product_interest': product_mentions,
            'duration': (self.last_updated - self.created_at).total_seconds() // 60,
            'feedback_positive': self.messages.filter(is_bot=True, feedback=True).count(),
            'feedback_negative': self.messages.filter(is_bot=True, feedback=False).count(),
        }


class ChatMessage(models.Model):
    """Modelo para mensajes individuales en una conversación"""
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    content = models.TextField()
    is_bot = models.BooleanField(default=False)
    source = models.CharField(max_length=50, default='ollama')
    timestamp = models.DateTimeField(auto_now_add=True)

    # Campos para análisis y mejora
    detected_intent = models.CharField(max_length=100, blank=True, null=True)
    detected_entities = models.JSONField(blank=True, null=True)
    feedback = models.BooleanField(null=True, blank=True)  # True=positivo, False=negativo, None=sin feedback
    processing_time = models.FloatField(null=True, blank=True)  # Tiempo en segundos

    class Meta:
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"
        ordering = ['timestamp']

    def __str__(self):
        prefix = "Bot" if self.is_bot else "Usuario"
        return f"{prefix}: {self.content[:50]}"

    def save(self, *args, **kwargs):
        # Actualizar last_updated de la conversación al guardar
        if self.conversation:
            self.conversation.last_updated = timezone.now()
            self.conversation.save(update_fields=['last_updated'])
        super().save(*args, **kwargs)


class TrainingFeedback(models.Model):
    """Modelo para recopilar retroalimentación para mejorar el chatbot"""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='training_feedback')
    correct_response = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Retroalimentación para entrenamiento"
        verbose_name_plural = "Retroalimentaciones para entrenamiento"

    def __str__(self):
        return f"Feedback para mensaje {self.message.id}"