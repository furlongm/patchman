from rest_framework import serializers

from patchman.hosts.models import Host, HostRepo


class HostSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Host
        fields = '__all__'


class HostRepoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HostRepo
        fields = '__all__'
