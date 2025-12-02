import toolbox


class Paw:
    def __init__(self, url):
        self.url = url
        self.platform = toolbox.get_platform(self.url)
        self.video_id = toolbox.get_platform_video_id(self.url)

    