




class BotState():
    def __init__(self):
        self.add_to_channel = True

    def toggle_add_to_channel(self):
        self.add_to_channel = not self.add_to_channel

    def get_add_to_channel(self):
        return self.add_to_channel