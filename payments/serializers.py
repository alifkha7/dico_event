from rest_framework import serializers
from rest_framework.reverse import reverse
from registrations.models import Registration
from .models import Payment


class PaymentSerializer(serializers.HyperlinkedModelSerializer):
    _links = serializers.SerializerMethodField()
    registration = serializers.CharField(source='registration.id', read_only=True)
    registration_id = serializers.PrimaryKeyRelatedField(
        queryset=Registration.objects.all(),
        write_only=True,
        source='registration'
    )

    class Meta:
        model = Payment
        fields = [
            'id', 'registration', 'registration_id', 'payment_method', 'payment_status', 'amount_paid', '_links'
        ]

    def get__links(self, obj):
        request = self.context.get('request')
        return [
            {
                "rel": "self",
                "href": reverse('payment-list', request=request),
                "action": "POST",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('payment-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "GET",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('payment-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "PUT",
                "types": ["application/json"]
            },
            {
                "rel": "self",
                "href": reverse('payment-detail', kwargs={'pk': obj.pk}, request=request),
                "action": "DELETE",
                "types": ["application/json"]
            }
        ]
