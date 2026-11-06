class PartialUpdateMixin:
    """Mixin for ModelViewSets that defaults PUT updates to partial=True per ADR-0001 / spec."""

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = kwargs.pop("partial", True)
        return super().update(request, *args, **kwargs)
