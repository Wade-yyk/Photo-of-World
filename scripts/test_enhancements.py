import unittest
import numpy as np
from PIL import Image
from enhancements import detect_crop, gradient_align, white_balance, contrast, colour_mapping
from test_alignment import shifted


class EnhancementTests(unittest.TestCase):
    def test_detects_asymmetric_borders(self):
        rng = np.random.default_rng(9)
        center = (rng.uniform(.25, .7, (170, 210, 3))*255).astype('uint8')
        canvas = np.zeros((200, 240, 3), dtype='uint8')
        canvas[:] = 255
        canvas[12:182, 9:219] = center
        box = detect_crop(Image.fromarray(canvas))
        for found, expected in zip(box, (9, 12, 219, 182)):
            self.assertLessEqual(abs(found-expected), 3)

    def test_no_automatic_fixed_crop(self):
        image = Image.new('RGB', (320, 240), (120, 130, 140))
        self.assertEqual(detect_crop(image), (0, 0, 320, 240))

    def test_white_balance_reduces_known_cast(self):
        gray = np.linspace(.15, .5, 100).reshape(10, 10, 1)
        cast = gray * np.array([1.3, .9, .8])
        balanced, gains = white_balance(cast, (0, 0, 10, 10))
        means = balanced.mean(axis=(0, 1))
        self.assertLess(np.ptp(means), 1e-6)
        self.assertTrue(np.isfinite(gains).all())

    def test_constant_contrast_is_finite(self):
        image = np.full((15, 20, 3), .4)
        result, levels = contrast(image, (0, 0, 20, 15))
        np.testing.assert_array_equal(result, image)

    def test_matrix_preserves_neutral_pixels(self):
        image = Image.new('RGB', (10, 10), (127, 127, 127))
        result, matrix = colour_mapping(image)
        np.testing.assert_array_equal(np.asarray(image), np.asarray(result))
        np.testing.assert_allclose(np.array(matrix).sum(axis=1), 1.)

    def test_gradient_shift(self):
        image = np.random.default_rng(11).random((257, 301), dtype=np.float32)
        moving = shifted(image, 8, -5)*.6+.1
        offset, trace = gradient_align(image, moving)
        self.assertEqual(offset, (-8, 5))


if __name__ == '__main__':
    unittest.main()
