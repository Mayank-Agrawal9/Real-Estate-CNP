# django
from django.core.exceptions import ImproperlyConfigured

# rest framework
from rest_framework import (
    mixins,
    status,
    response,
    viewsets,
    permissions
)

# standard library
import re

# local import
from utils.helpers import GlobalHelpers


class BaseViewSetSetup(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_classes = {}
    default_serializer_class = None
    lookup_field = 'id'

    # this will enable single line response, you just have to set up with your action name and True/False
    enable_single_line_response = {
        'create': False,
        'update': False
    }
    # this setup is for handle the single line response message, you must have to define your function in your
    # model as @property and register with your action in 'single_line_response_functions'
    register_response_functions = {
        'create': 'object_created_message',
        'update': 'object_updated_message'
    }
    '''
    this is to check the unique constraint. sometimes we just want to create maximum one entry based on a specific 
    field(i.e. any unique field)
    "validate_unique" is to determine your decision that, do you want this feature or not. default it is False
    if you set it to True then you have to set the field name(on which it will check already exist or not)
    if you cannot access the field directly then you can setup the lookup. 
    Ex: unique_field_name="user" and you try to check based on username then you have to set the lookup = "lookup"
    and it will check like 
    >>> YourModel.objects.filter(user__username="your_username")
    "if_found_then_return" is to determine that if any object found then you return an error as the response or return
    the previous object
    If you want to return your previous stored object then you have to set the serializer, which will serialize the 
    previous_object
    * It will only work for create action
    '''
    unique_constraint_setup = {
        'enable': False,
        'unique_field_name': None,
        'lookup': 'id',
        'if_found_then_return': 'error',     # 'error/previous_response'
        'serializer': None
    }

    @property
    def unique_constraint_field(self):
        return self.unique_constraint_setup.get('unique_field_name')

    @property
    def default_unique_constraint_error_message(self):
        return 'One entry already exists for this %s' % self.unique_constraint_field

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def get_response_data(self):
        return {'detail': getattr(self.queryset.model(), self.register_response_functions.get(self.action))}

    def return_response(self, response_payload=None, extra_data=None, extra_data_key=None):
        # this function can be useful where, "CustomCreateMixin" is not inherited
        res = {}
        if self.enable_single_line_response.get(self.action):
            res = self.get_response_data()
        elif response_payload:
            res = response_payload

        # you can pass some extra_data along with the response
        # to do that, you just have to pass the 'extra_data_key' and 'extra_data'
        # ex: extra_data_key = 'token', extra_data = 'FSISKDJSOTDSAWXJHAXH'
        # so it will add with your response
        if extra_data and extra_data_key:
            res.update({extra_data_key: extra_data})

        return response.Response(res, status=status.HTTP_201_CREATED)

    def list_action_paginated_response(self, queryset, serializer_context=None, serializer_class=None):
        paginate = self.request.GET.get('paginate', '0')
        if not re.match("^[0-1]$", paginate):
            return response.Response({'detail': 'Invalid paginate value.'}, status=status.HTTP_400_BAD_REQUEST)
        ctx = serializer_context if serializer_context else {}
        if paginate == '1':
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = serializer_class(page, many=True, context=ctx) if serializer_class else\
                    self.get_serializer(page, many=True, context=ctx)
                return self.get_paginated_response(serializer.data)
        serializer = serializer_class(queryset, many=True, context=ctx) if serializer_class else \
            self.get_serializer(queryset, many=True, context=ctx)
        return response.Response(serializer.data)


class CustomCreateMixin(mixins.CreateModelMixin):
    '''
    before inherit this class into a child class, make sure you have already inherited 'BaseViewSetSetup' class
    '''

    def validate_unique_constraint_during_create(self, payload, serializer):
        if payload.get(self.unique_constraint_field) is None:
            raise ImproperlyConfigured('unique_constraint_setup["unique_field_name"] is not passed into payload')
        query = {f'{self.unique_constraint_field}__{self.unique_constraint_setup.get("lookup")}'
                 if self.unique_constraint_setup.get('lookup')
                 else self.unique_constraint_field: payload.get(self.unique_constraint_field)}
        previous_entry = self.get_queryset().filter(**query).last()
        if previous_entry:
            return_condition = self.unique_constraint_setup.get('if_found_then_return')
            if return_condition == 'error':
                return response.Response(
                    {'detail': self.default_unique_constraint_error_message}, status=status.HTTP_400_BAD_REQUEST)
            elif return_condition == 'previous_response':
                # return previous response
                serializer = self.unique_constraint_setup.get('serializer')
                if not serializer:
                    raise ImproperlyConfigured("unique_constraint_setup['if_found_then_return']='previous_response' "
                                               "but you did not setup serializer")
                return response.Response(serializer(previous_entry, many=False).data)
            else:
                raise ImproperlyConfigured(
                    f"unique_constraint_setup['if_found_then_return']={return_condition} is not valid action.")
        else:
            return self.create_instance(serializer=serializer)

    def create_instance(self, serializer):
        serializer.save()
        return self.return_response(response_payload=serializer.data)

    def get_create_method_payload(self):
        '''
        override this method into child class if you want to change the request data payload
        '''
        return self.request.data.dict()

    def create(self, request, *args, **kwargs):
        _, payload = GlobalHelpers.add_fields_to_payload(
            self.get_create_method_payload(), ('created_by', ), (request.user.id, ))

        serializer = self.get_serializer_class()(data=payload)
        serializer.is_valid(raise_exception=True)

        if self.unique_constraint_setup.get('enable'):
            try:
                return self.validate_unique_constraint_during_create(payload=payload, serializer=serializer)
            except Exception as e:
                return response.Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return self.create_instance(serializer=serializer)


class CustomUpdateMixin(mixins.UpdateModelMixin):

    def validate_unique_constraint_during_update(self, obj, payload, serializer):
        if payload.get(self.unique_constraint_field) is None:
            raise ImproperlyConfigured('unique_constraint_setup["unique_field_name"] is not passed into payload')
        query = {f'{self.unique_constraint_field}__{self.unique_constraint_setup.get("lookup")}'
                 if self.unique_constraint_setup.get('lookup')
                 else self.unique_constraint_field: payload.get(self.unique_constraint_field)}
        previous_entry = self.get_queryset().filter(**query).last()
        if previous_entry and obj.id != previous_entry.id:
            return_condition = self.unique_constraint_setup.get('if_found_then_return')
            if return_condition == 'error':
                return response.Response(
                    {'detail': self.default_unique_constraint_error_message}, status=status.HTTP_400_BAD_REQUEST)
            elif return_condition == 'previous_response':
                # return previous response
                serializer = self.unique_constraint_setup.get('serializer')
                if not serializer:
                    raise ImproperlyConfigured("unique_constraint_setup['if_found_then_return']='previous_response' "
                                               "but you did not setup serializer")
                return response.Response(serializer(previous_entry, many=False).data)
            else:
                raise ImproperlyConfigured(
                    f"unique_constraint_setup['if_found_then_return']={return_condition} is not valid action.")
        else:
            return self.create_instance(serializer=serializer)

    def update_instance(self, serializer):
        serializer.save()
        return self.return_response(response_payload=serializer.data)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()

        payload = request.data.dict()
        payload['updated_by'] = request.user.id

        serializer = self.get_serializer_class()(obj, payload, partial=True)
        serializer.is_valid(raise_exception=True)

        if self.unique_constraint_setup.get('enable'):
            try:
                return self.validate_unique_constraint_during_update(obj=obj, payload=payload, serializer=serializer)
            except Exception as e:
                return response.Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return self.update_instance(serializer=serializer)


class CustomListMixin(mixins.ListModelMixin):
    def list(self, request, *args, **kwargs):
        try:
            queryset = getattr(self, 'get_list_filter_queryset')()
        except:
            queryset = self.filter_queryset(self.get_queryset())

        paginate = request.GET.get('paginate', '0')
        if not re.match("^[0-1]$", paginate):
            return response.Response({'detail': 'Invalid paginate value.'}, status=status.HTTP_400_BAD_REQUEST)

        if paginate == '1':
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return response.Response(serializer.data)


class CustomDeleteMixin(mixins.DestroyModelMixin):
    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return response.Response({'message': 'Record deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
