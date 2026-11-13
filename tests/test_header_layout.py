import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import unittest

from ui.header_layout import header_rectangles, layout_header
from ui.theme import Theme, init_fonts


class HeaderLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_fonts()
        cls.theme = Theme()

    def test_header_rectangles_fit_without_overlap_at_reference_and_small_widths(self):
        for size, screen in (((1240, 620), "index"), ((900, 620), "index"),
                             ((1240, 544), "workbench"), ((900, 544), "workbench")):
            with self.subTest(size=size, screen=screen):
                layout = layout_header(self.theme, size, screen, "Press Esc for power menu",
                                       "CHECK FOR UPDATES [U]", "vabcdef1")
                rects = header_rectangles(layout)
                for rect in rects:
                    self.assertGreaterEqual(rect.left, 0)
                    self.assertLessEqual(rect.right, size[0])
                for i, rect in enumerate(rects):
                    for other in rects[i + 1:]:
                        self.assertFalse(rect.colliderect(other), (size, screen, rect, other))
                self.assertTrue(all(rect.left >= 16 for rect in rects))


if __name__ == "__main__":
    unittest.main()
