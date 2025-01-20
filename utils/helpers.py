class GlobalHelpers:

    @staticmethod
    def remove_fields_from_payload(payload, fields):
        '''This function is used to remove elements from a dict and return updated dict'''
        return list(map(lambda field: payload.pop(field), fields))

    @staticmethod
    def add_fields_to_payload(payload, keys, values):
        '''This function is used to add and update elements to a dict and return updated dict'''
        return list(map(lambda key, value: payload.update({key: value}), keys, values)), payload