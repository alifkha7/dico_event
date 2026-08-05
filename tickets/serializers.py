from rest_framework import serializers
from rest_framework.reverse import reverse
from events.models import Event
from tickets.models import Ticket


class TicketSerializer(serializers.HyperlinkedModelSerializer):
    _links = serializers.SerializerMethodField()
    event = serializers.CharField(source='event.name', read_only=True)
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        write_only=True,
        source='event'
    )

    class Meta:
        model = Ticket
        fields = [
            'id', 'event', 'event_id', 'name', 'price', 'sales_start', 'sales_end', 'quota', '_links']

    def get__links(self, obj):
        request = self.context.get('request')
        return [
            {
                "rel": "self",
                "href": reverse('ticket-list', request=request),
                "action": "POST",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('ticket-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "GET",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('ticket-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "PUT",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('ticket-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "DELETE",
                "types": ["application/json"]
            }
        ]
