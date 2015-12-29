from collections import OrderedDict
from django.utils.encoding import force_text
from rest_framework import serializers
from rest_framework.metadata import SimpleMetadata
from rest_framework_filters import RelatedFilter

DATETIME_LOOKUPS = ['exact', 'gte', 'gt', 'lte', 'lt', 'range', 'year',
                    'month', 'day', 'hour', 'minute', 'second']
DATE_LOOKUPS = DATETIME_LOOKUPS[:-3]
INTEGER_LOOKUPS = ['exact', 'gte', 'gt', 'lte', 'lt', 'range']
BASIC_TEXT_LOOKUPS = ['exact', 'iexact', 'startswith', 'istartswith',
                      'endswith', 'iendswith']
ALL_TEXT_LOOKUPS = BASIC_TEXT_LOOKUPS + ['contains', 'icontains']


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Instantiate the superclass normally
        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)
        if not self.context or not self.context.get('request'):
            # This happens during initialization.
            return
        fields = self.context['request'].query_params.get('fields')
        if fields is not None:
            fields = fields.split(',')
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class SimpleMetadataWithFilters(SimpleMetadata):

    def determine_metadata(self, request, view):
        metadata = super(SimpleMetadataWithFilters, self).determine_metadata(request, view)
        filters = OrderedDict()
        for filter_name, filter_type in view.filter_class.base_filters.items():
            filter_parts = filter_name.split('__')
            filter_name = filter_parts[0]
            attrs = OrderedDict()

            # Type
            attrs['type'] = filter_type.__class__.__name__

            # Lookup fields
            if len(filter_parts) > 1:
                # Has a lookup type (__gt, __lt, etc.)
                lookup_type = filter_parts[1]
                if filters.get(filter_name) is not None:
                    # We've done a filter with this name previously, just
                    # append the value.
                    attrs['lookup_types'] = filters[filter_name]['lookup_types']
                    attrs['lookup_types'].append(lookup_type)
                else:
                    attrs['lookup_types'] = [lookup_type]
            else:
                # Exact match or RelatedFilter
                if isinstance(filter_type, RelatedFilter):
                    model_name = filter_type.filterset.Meta.\
                        model._meta.verbose_name_plural.title()
                    attrs['lookup_types'] = "See available filters for '%s'" % \
                                            model_name
                else:
                    attrs['lookup_types'] = ['exact']

            # Do choices
            choices = filter_type.extra.get('choices', False)
            if choices:
                attrs['choices'] = [
                    {
                        'value': choice_value,
                        'display_name': force_text(choice_name, strings_only=True)
                    }
                    for choice_value, choice_name in choices
                ]

            # Wrap up.
            filters[filter_name] = attrs

        metadata['filters'] = filters
        return metadata
