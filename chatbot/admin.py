from django.contrib import admin
from .models import ChatConversation, ChatMessage, TrainingFeedback


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('content', 'is_bot', 'source', 'detected_intent', 'feedback', 'timestamp')
    fields = ('is_bot', 'content', 'source', 'detected_intent', 'feedback', 'timestamp')
    can_delete = False
    max_num = 0


class TrainingFeedbackInline(admin.TabularInline):
    model = TrainingFeedback
    extra = 0
    fields = ('message', 'correct_response', 'notes', 'reviewed')


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'user', 'message_count', 'created_at', 'last_updated')
    list_filter = ('created_at', 'last_updated')
    search_fields = ('session_id', 'user__username', 'user__email')
    inlines = [ChatMessageInline]

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = 'Mensajes'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
    'id', 'get_session_id', 'is_bot', 'content_preview', 'source', 'detected_intent', 'feedback_status', 'timestamp')
    list_filter = ('is_bot', 'source', 'detected_intent', 'feedback', 'timestamp')
    search_fields = ('content', 'conversation__session_id')
    readonly_fields = (
    'conversation', 'is_bot', 'content', 'source', 'detected_intent', 'detected_entities', 'timestamp')

    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')

    content_preview.short_description = 'Contenido'

    def get_session_id(self, obj):
        return obj.conversation.session_id if obj.conversation else '-'

    get_session_id.short_description = 'Session ID'

    def feedback_status(self, obj):
        if obj.feedback is None:
            return 'Sin feedback'
        return 'Positivo' if obj.feedback else 'Negativo'

    feedback_status.short_description = 'Feedback'


@admin.register(TrainingFeedback)
class TrainingFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'created_at', 'reviewed')
    list_filter = ('reviewed', 'created_at')
    search_fields = ('message__content', 'notes', 'correct_response')
    readonly_fields = ('message', 'created_at')