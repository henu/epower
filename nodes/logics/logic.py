class Logic:

    def __init__(self, node):
        self.node = node

    def get_name(self):
        raise NotImplementedError()

    def get_description(self):
        raise NotImplementedError()

    def get_settings_fields(self):
        return {}

    def get_input_keys(self):
        return set()

    def get_output_keys(self):
        return set()

    def get_output_values(self):
        return {}

    def handle_inputs_changed(self, inputs):
        pass

    def handle_updated_prices(self, prices):
        pass

    def apply_state_to_devices(self):
        pass

    def get_settings_errors(self, settings):
        return {}
