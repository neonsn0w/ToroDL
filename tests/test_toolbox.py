from unittest import TestCase
from toolbox import validate_url, get_platform_video_id

class Test(TestCase):
    TEST_URLS = {
        "https://www.youtube.com/watch?v=R4q-bxbxfXc&list=RDMM&start_radio=1" : "R4q-bxbxfXc",
        "https://x.com/lyanmyan/status/2008657476544327848?s=20" : "2008657476544327848"
    }

    def test_validate_url(self):
        self.assertEqual(validate_url('http://google.com'), False)

        for item in self.TEST_URLS:
            self.assertEqual(validate_url(item), True)

    def test_get_platform_video_id(self):
        for item in self.TEST_URLS:
            self.assertEqual(get_platform_video_id(item), self.TEST_URLS[item])

