"""Small deterministic checks for sign, coarse-to-fine recovery, and valid cropping."""
import unittest
import numpy as np
from alignment import search,pyramid_align,compose,ncc_score

def shifted(a,dx,dy):
    out=np.zeros_like(a);h,w=a.shape
    x0,x1=max(0,dx),min(w,w+dx);y0,y1=max(0,dy),min(h,h+dy)
    out[y0:y1,x0:x1]=a[y0-dy:y1-dy,x0-dx:x1-dx]
    return out

class AlignmentTests(unittest.TestCase):
    def test_offset_sign_and_brightness(self):
        a=np.random.default_rng(3).random((100,130),dtype=np.float32)
        b=shifted(a,7,-4)*0.6+0.15
        offset,score=search(a,b,radius=10)
        self.assertEqual(offset,(-7,4));self.assertGreater(score,.9999)
    def test_large_shift_at_odd_dimensions(self):
        a=np.random.default_rng(8).random((641,769),dtype=np.float32)
        b=shifted(a,45,-31)
        offset,trace=pyramid_align(a,b)
        self.assertEqual(offset,(-45,31));self.assertGreater(len(trace),1)
    def test_common_overlap_has_no_wrapped_pixels(self):
        a=np.random.default_rng(10).random((100,120),dtype=np.float32)
        g=shifted(a,7,-4);r=shifted(a,-6,5)
        image,bounds=compose((a,g,r),(-7,4),(6,-5))
        rgb=np.asarray(image)
        self.assertEqual(bounds,(6,4,113,95))
        np.testing.assert_array_equal(rgb[:,:,0],rgb[:,:,1])
        np.testing.assert_array_equal(rgb[:,:,1],rgb[:,:,2])

if __name__=='__main__':unittest.main()
