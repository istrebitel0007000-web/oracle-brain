from rest_framework import serializers


class Serializer(serializers.Serializer):
    """
    Base serializer for all Oracle Brain serializers.
    All request/response serializers must inherit from this class.
    Never use ModelSerializer.
    """
    pass
