from rest_framework import serializers
from rest_framework.reverse import reverse
from core.models import User
from .models import Event, EventImage


class EventSerializer(serializers.HyperlinkedModelSerializer):
    _links = serializers.SerializerMethodField()
    organizer = serializers.CharField(source='organizer.username', read_only=True)
    organizer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        source='organizer'
    )

    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description', 'location', 'start_time', 'end_time',
            'status', 'quota', 'category', 'organizer', 'organizer_id', '_links'
        ]

    def get__links(self, obj):
        request = self.context.get('request')
        return [
            {
                "rel": "self",
                "href": reverse('event-list', request=request),
                "action": "POST",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('event-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "GET",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('event-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "PUT",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('event-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "DELETE",
                "types": ["application/json"]
            }
        ]


class EventPosterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ['id', 'event', 'image']

    def validate_image(self, value):
        max_size = 500 * 1024  # 500kB
        if value.size > max_size:
            raise serializers.ValidationError("Image size cannot exceed 500kB.")
        return value
