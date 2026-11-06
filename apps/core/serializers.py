from rest_framework import serializers


def _resolve_foreign_key(
    attrs,
    initial_data,
    instance,
    field_name,
    id_keys,
    model_class=None,
    queryset=None,
    default_fn=None,
    required_on_create=True,
    label=None,
    select_related=None,
    prefetch_related=None,
):
    """
    Resolve a foreign key from initial_data or attrs into a model instance.
    Model-agnostic helper per Coding Standard #2.
    """
    raw_val = None
    for k in id_keys:
        val = initial_data.get(k) if initial_data else None
        if val is None and attrs:
            val = attrs.get(k)
        if val is not None:
            raw_val = val
            break

    primary_id_key = id_keys[0]

    if queryset is not None:
        qs = queryset
        target_model = getattr(qs, "model", None)
    elif model_class is not None:
        target_model = model_class
        qs = model_class.objects
    else:
        raise ValueError("Either model_class or queryset must be provided to _resolve_foreign_key.")

    if select_related:
        qs = qs.select_related(*select_related)
    if prefetch_related:
        qs = qs.prefetch_related(*prefetch_related)

    if isinstance(target_model, type):
        model_name = target_model.__name__
    elif hasattr(target_model, "__name__") and not hasattr(target_model, "_mock_return_value"):
        model_name = str(target_model.__name__)
    else:
        model_name = label or "Object"

    display_label = label or model_name

    if raw_val is not None:
        if isinstance(target_model, type) and isinstance(raw_val, target_model):
            attrs[field_name] = raw_val
        else:
            try:
                attrs[field_name] = qs.get(id=raw_val)
            except Exception:
                raise serializers.ValidationError({primary_id_key: f"{display_label} not found."})
    elif instance is None and required_on_create:
        default_val = default_fn() if callable(default_fn) else None
        if default_val is not None:
            attrs[field_name] = default_val
        else:
            raise serializers.ValidationError({primary_id_key: f"{display_label} is required."})

    for k in id_keys:
        if k != field_name:
            attrs.pop(k, None)


class DualKeyModelSerializer(serializers.ModelSerializer):
    """
    Base serializer providing declarative dual-key (<field> and <field>_id) foreign key resolution
    and string serialization in to_representation.
    """

    dual_key_fields = {}

    def validate(self, attrs):
        attrs = super().validate(attrs)
        self.resolve_dual_keys(attrs)
        return attrs

    def resolve_dual_keys(self, attrs):
        request = self.context.get("request")
        for field_name, config in self.dual_key_fields.items():
            id_keys = config.get("id_keys", (f"{field_name}_id", field_name))
            model_class = config.get("model")
            queryset = config.get("queryset")
            select_related = config.get("select_related")
            prefetch_related = config.get("prefetch_related")
            required_on_create = config.get("required_on_create", True)
            label = config.get("label")

            default_fn = config.get("default_fn")
            if default_fn is None and config.get("default_to_request_user", False):

                def default_user():
                    return request.user if request and request.user and request.user.is_authenticated else None

                default_fn = default_user

            _resolve_foreign_key(
                attrs=attrs,
                initial_data=self.initial_data,
                instance=self.instance,
                field_name=field_name,
                id_keys=id_keys,
                model_class=model_class,
                queryset=queryset,
                default_fn=default_fn,
                required_on_create=required_on_create,
                label=label,
                select_related=select_related,
                prefetch_related=prefetch_related,
            )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if hasattr(instance, "id") and instance.id is not None:
            ret["id"] = str(instance.id)

        for field_name in self.dual_key_fields:
            # Check target id on instance (e.g. organizer_id or organizer.id)
            target_id = getattr(instance, f"{field_name}_id", None)
            if target_id is None:
                rel_obj = getattr(instance, field_name, None)
                if rel_obj is not None:
                    target_id = getattr(rel_obj, "id", None)
            if target_id is not None:
                ret[field_name] = str(target_id)
                ret[f"{field_name}_id"] = str(target_id)

        return ret
