#!/usr/bin/env python

"""
Unit tests for PSF classes.
"""

import sys
import os
import numpy as N
import unittest

from specter.psf import load_psf
from specter.test import test_data_dir

class TestPSF(unittest.TestCase):
    """
    Wrapper for testing any PSF class
    """

    def wrap_wave_test(self, fn):
        """Test wavelength or loglam"""
        #- Scalar ispec + Unspecified y -> array with nwave elements
        tmp = fn(0, None)
        self.assertTrue(len(tmp) == self.psf.nwave)
        
        #- Scalar ispec and scalar y -> float
        tmp = fn(0, y=0)
        self.assertTrue(isinstance(tmp, float))

        #- Scalar ispec + y array -> wave array
        yy = N.linspace(0, self.psf.nwave)
        tmp = fn(0, y=yy)
        self.assertTrue(len(tmp) == len(yy))
        
        #- Unspecified ispec and unspecified y : full wave/loglam grid
        self.assertTrue(fn().shape == (self.psf.nspec, self.psf.nwave))
        
        #- ispec >= nspec should raise an error
        with self.assertRaises(IndexError):
            fn(self.psf.nspec)

    #- Test psf.loglam() options
    def test_loglam(self):
        self.wrap_wave_test(self.psf.loglam)

    #- Test psf.wavelength() options
    def test_wavelength(self):
        self.wrap_wave_test(self.psf.wavelength)
        
    #- Make sure that dimensions are set
    def test_dimensions(self):
        self.assertTrue(self.psf.npix_x > 0)
        self.assertTrue(self.psf.npix_y > 0)
        self.assertTrue(self.psf.nspec > 0)
        self.assertTrue(self.psf.nwave > 0)
        
    #- Test xsigma
    def test_xsigma(self):
        yy = (20, self.psf.npix_y/2, self.psf.npix_y-20)
        for ispec in (0, self.psf.nspec/2, self.psf.nspec-1):
            ww = self.psf.wavelength(ispec, y=yy)
            #- Get xsigma for several wavelengths at once
            xsig1 = self.psf.xsigma(ispec, ww)
            self.assertTrue(len(xsig1) == len(ww))
            self.assertTrue(N.min(xsig1) > 0.0)                
            
            #- Call it again to make sure cached results agree
            xsig2 = self.psf.xsigma(ispec, ww)
            self.assertTrue(N.all(xsig1 == xsig2))
            
        #- Make sure it works for single wavelengths too
        ispec = 0
        ww = self.psf.wavelength(ispec, y=yy)
        xsig1 = self.psf.xsigma(ispec, ww)
        for i in range(len(ww)):
            xsig = self.psf.xsigma(ispec, ww[i])
            self.assertTrue(xsig == xsig1[i])
        
    #- Test wdisp
    def test_wdisp(self):
        yy = (20, self.psf.npix_y/2, self.psf.npix_y-20)
        for ispec in (0, self.psf.nspec/2, self.psf.nspec-1):
            ww = self.psf.wavelength(ispec, y=yy)
            #- Get wdisp for several wavelengths at once
            xsig1 = self.psf.wdisp(ispec, ww)
            self.assertTrue(len(xsig1) == len(ww))
            self.assertTrue(N.min(xsig1) > 0.0)                
            
            #- Call it again to make sure cached results agree
            xsig2 = self.psf.wdisp(ispec, ww)
            self.assertTrue(N.all(xsig1 == xsig2))
            
        #- Make sure it works for single wavelengths too
        ispec = 0
        ww = self.psf.wavelength(ispec, y=yy)
        xsig1 = self.psf.wdisp(ispec, ww)
        for i in range(len(ww)):
            xsig = self.psf.wdisp(ispec, ww[i])
            self.assertTrue(xsig == xsig1[i])
        
    #- Get PSF pixel image at several locations;
    #- Just test that we get a 2D array back
    def test_pix(self):
        ww = self.psf.wavelength()
        wtest = list()
        wtest.append(N.min(ww[:, 0]))
        wtest.append(N.max(ww[:, 0]))
        wtest.append(N.min(ww[:, -1]))
        wtest.append(N.max(ww[:, -1]))
        wtest.append(N.mean(wtest))
        
        for i in (0, self.psf.nspec/2, self.psf.nspec-1):
            for w in wtest:
                pix = self.psf.pix(i, w)
                self.assertEquals(pix.ndim, 2)  

    #- Get PSF pixel image and where to put it on the CCD
    #- Confirm that image size matches ranges
    def test_xypix(self):
        ww = self.psf.wavelength()
        wtest = list()
        wtest.append(N.min(ww[:, 0]))
        wtest.append(N.max(ww[:, 0]))
        wtest.append(N.min(ww[:, -1]))
        wtest.append(N.max(ww[:, -1]))
        wtest.append(N.mean(wtest))
        wtest.append(N.min(ww)-100)
        
        for i in (0, self.psf.nspec/2, self.psf.nspec-1):
            for w in wtest:
                xx, yy, pix = self.psf.xypix(self.psf.nspec/2, w)
                shape = (yy.stop-yy.start, xx.stop-xx.start)
                msg = "%s != %s at (i=%d, w=%.1f)" % (str(pix.shape), str(shape), i, w)
                self.assertEqual(pix.shape, shape, msg)
                
    #- Test psf.xypix() using CCD pixel xmin/xmax, ymin/ymax options
    #- Doesn't test every possibility
    def test_xypix_range(self):
        w = N.mean(self.psf.wavelength())
        i = self.psf.nspec/2
        x0, y0, pix = self.psf.xypix(i, w)
        xx, yy, pix = self.psf.xypix(i, w, xmin=x0.start)
        self.assertTrue(xx.start == 0)
        self.assertTrue(yy.start == y0.start)
        xx, yy, pix = self.psf.xypix(i, w, ymin=y0.start)
        self.assertTrue(xx.start == x0.start)
        self.assertTrue(yy.start == 0)
        xx, yy, pix = self.psf.xypix(i, w, xmax=x0.stop-1)
        self.assertTrue(xx.start == x0.start)
        self.assertTrue(xx.stop == x0.stop-1)
        xx, yy, pix = self.psf.xypix(i, w, ymax=y0.stop-1)
        self.assertTrue(yy.start == y0.start)
        self.assertTrue(yy.stop == y0.stop-1)
        xx, yy, pix = self.psf.xypix(i, w, xmin=x0.start, ymin=y0.start)
        self.assertTrue(xx.start == 0)
        self.assertTrue(yy.start == 0)
        
    #- Test requests for PSFs off the edge of the requested xyrange
    #- Helper function
    def check_xypix_edges(self, ispec, wavelength, xyrange):
        xx, yy, pix = self.psf.xypix(ispec, wavelength=wavelength, **xyrange)
        nx = xx.stop - xx.start
        ny = yy.stop - yy.start
        msg = 'xx=' + str(xx) + ' yy=' + str(yy) + ' ' + str(pix.shape)
        self.assertEqual(ny, pix.shape[0], msg)
        self.assertEqual(nx, pix.shape[1], msg)
    
    #- The actual test
    def test_xypix_edges(self):
        psf = self.psf
        #- Pick a range within the CCD
        imin = psf.nspec/2 - 5
        imax = psf.nspec/2 + 5
        wmin = psf.wavelength(imin, y=int(psf.npix_y*0.4))
        wmax = psf.wavelength(imax, y=int(psf.npix_y*0.6))
        wmid = 0.5*(wmin + wmax)

        xmin, xmax, ymin, ymax = psf.xyrange((imin, imax), (wmin, wmax))
        xyrange = dict(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)

        for i in (imin-1, imin, imax, imax+1):
            for w in (wmin-3, wmin, wmid, wmax, wmax+3):
                self.check_xypix_edges(i, w, xyrange)
        
    #- Test projection of 1D spectrum with 1D wavelength vector
    def test_project11(self):
        ww = self.psf.wavelength(0)[0:10]
        phot = N.random.uniform(0,100,len(ww))
        img = self.psf.project(phot, ww, verbose=False)
        self.assertEquals(img.shape, (self.psf.npix_y, self.psf.npix_x))
    
    #- Test projection of 2D spectrum with shared 1D wavelength vector
    def test_project12(self):
        ww = self.psf.wavelength(0)[0:10]
        phot = N.random.uniform(0,100,len(ww))
        phot = N.tile(phot, 5).reshape(5, len(ww))
        img = self.psf.project(phot, ww, verbose=False)
        self.assertEquals(img.shape, (self.psf.npix_y, self.psf.npix_x))

    #- Test projection of 2D spectrum with 2D wavelength vector
    def test_project22(self):
        nw = 10
        ww = self.psf.wavelength(0)[0:nw]
        ww = N.tile(ww, 5).reshape(5, nw)
        phot = N.random.uniform(0,100,nw)
        phot = N.tile(phot, 5).reshape(5, nw)
        img = self.psf.project(phot, ww, verbose=False)
        self.assertEquals(img.shape, (self.psf.npix_y, self.psf.npix_x))
    
    #- Test projection starting at specmin != 0
    def test_project_specmin(self):
        ww = self.psf.wavelength(0)[0:10]
        phot = N.random.uniform(0,100,len(ww))
        img = self.psf.project(phot, ww, specmin=1, verbose=False)
        self.assertEquals(img.shape, (self.psf.npix_y, self.psf.npix_x))
        
        #- specmin >= nspec should raise an error
        with self.assertRaises(IndexError):
            i = self.psf.nspec
            img = self.psf.project(phot, ww, specmin=i, verbose=False)

    #- Test projecting to a subgrid of CCD pixels
    def test_project_xyrange(self):
        nspec = 5
        nw = 10
        ww = self.psf.wavelength(0)[0:nw]
        phot = N.random.uniform(0,100,nw)               #- 1D
        phot = N.tile(phot, nspec).reshape(nspec, nw)   #- 2D
        
        spec_range = (0, nspec)
        
        xyrange = xmin,xmax,ymin,ymax = self.psf.xyrange(spec_range, ww)
        img = self.psf.project(phot, ww, verbose=False)
        subimg = self.psf.project(phot, ww, xyrange=xyrange, verbose=False)

        #- Does subimage match corresponding range for full image?
        self.assertTrue(N.all(subimg == img[ymin:ymax, xmin:xmax]))

        #- Clear subimage region and test that everything is 0
        img[ymin:ymax, xmin:xmax] = 0.0
        self.assertTrue(N.all(img == 0.0))
        
    #- Test the projection matrix gives same answer as psf.project()
    def test_projection_matrix(self):
        nspec = 5
        nw = 20
        w_edge = 10  #- avoid edge effects; test that separately
        phot = N.random.uniform(100,1000, size=(nspec, nw))
        for specmin in (0, self.psf.nspec/2, self.psf.nspec-nspec-1):
            specrange = (specmin, specmin+nspec)
            wspec = self.psf.wavelength(specmin, [0, self.psf.npix_y])
            for wmin in (wspec[0]+w_edge, 0.5*(wspec[0]+wspec[1]), wspec[1]-nw-w_edge):
                ww = N.arange(wmin, wmin+nw)
                waverange = (ww[0], ww[-1])
                xmin, xmax, ymin, ymax = xyrange = self.psf.xyrange(specrange, waverange)
                nx = xmax-xmin
                ny = ymax-ymin

                img1 = self.psf.project(phot, ww, xyrange=xyrange, \
                                        specmin=specmin, verbose=False)

                A = self.psf.projection_matrix(specrange, ww, xyrange)
                img2 = A.dot(phot.ravel()).reshape((ny, nx))                    
                
                self.assertTrue(N.all(img1==img2))
        
    #- Test xyrange with scalar vs. tuple spec_range
    def test_xyrange_ispec(self):
        ispec = 0
        ww = self.psf.wavelength(ispec, y=N.arange(0, 10))
        xyr1 = self.psf.xyrange(ispec, ww)
        xyr2 = self.psf.xyrange((ispec, ispec+1), ww)
        self.assertTrue(xyr1 == xyr2)
    
    #- Test projection matrix with scalar vs. tuple spec_range
    def test_projmat_ispec(self):
        ispec = 0
        ww = self.psf.wavelength(ispec, y=N.arange(0, 10))
        xyrange = self.psf.xyrange(ispec, ww)
        A = self.psf.projection_matrix(ispec, ww, xyrange)
        B = self.psf.projection_matrix((ispec, ispec+1), ww, xyrange)

        self.assertTrue(A.shape == B.shape)
        self.assertTrue(N.all(A.data == B.data))
        
    #- Test shift of PSF xy solution
    def test_shift_xy(self):
        dx, dy = 0.1, 0.2
        x0 = self.psf.x(0).copy()
        y0 = self.psf.y(0).copy()
        self.psf.shift_xy(dx, dy)
        self.assertTrue(N.all(self.psf.x(0) == x0+dx))
        self.assertTrue(N.all(self.psf.y(0) == y0+dy))
    
    #- Test multiple options for getting x centroid
    def test_x(self):
        #- Grid of x positions
        x = self.psf.x()
        self.assertEqual(x.ndim, 2)
        self.assertEqual(x.shape[0], self.psf.nspec)
        self.assertEqual(x.shape[1], self.psf.nwave)

        #- x for fiber 0
        x = self.psf.x(0)
        self.assertEqual(x.ndim, 1)
        self.assertEqual(len(x), self.psf.nwave)
        
        #- x for fiber 0 at a specific wavelength
        w = N.mean(self.psf.wavelength(0))
        x = self.psf.x(0, w)
        self.assertTrue(isinstance(x, float))
        
        #- x for all fibers at a fixed wavelength
        x = self.psf.x(None, w)
        self.assertEqual(x.ndim, 1)
        self.assertEqual(len(x), self.psf.nspec)
        
        #- x for fiber 0 at a range of wavelengths
        w = self.psf.wavelength(0)[0:10]
        x = self.psf.x(0, w)
        self.assertEqual(x.shape, w.shape)

        #- x for all fibers at a range of wavelengths
        x = self.psf.x(None, w)
        self.assertEqual(x.shape, (self.psf.nspec, len(w)))

    #- Test multiple options for getting y centroid
    def test_y(self):
        #- Grid of y positions
        y = self.psf.y()
        self.assertEqual(y.ndim, 2)
        self.assertEqual(y.shape[0], self.psf.nspec)
        self.assertEqual(y.shape[1], self.psf.nwave)

        #- y for fiber 0
        y = self.psf.y(0)
        self.assertEqual(y.ndim, 1)
        self.assertEqual(len(y), self.psf.nwave)
        
        #- y for fiber 0 at a specific wavelength
        w = N.mean(self.psf.wavelength(0))
        y = self.psf.y(0, w)
        #- FAILS: returns 0dim array !?!
        self.assertTrue(isinstance(y, float))
        
        #- y for all fibers at a fixed wavelength
        y = self.psf.y(None, w)
        self.assertEqual(y.ndim, 1)
        self.assertEqual(len(y), self.psf.nspec)
        
        #- y for fiber 0 at a range of wavelengths
        w = self.psf.wavelength(0)[0:10]
        y = self.psf.y(0, w)
        self.assertEqual(y.shape, w.shape)

        #- y for all fibers at a range of wavelengths
        y = self.psf.y(None, w)
        self.assertEqual(y.shape, (self.psf.nspec, len(w)))

    #- Ensure that pix requests outside of wavelength range are blank
    def test_waverange_pix(self):
        for ispec in (0, 1, self.psf.nspec/2, self.psf.nspec-1):
            xx, yy, pix = self.psf.xypix(ispec, self.psf.wmin-1)
            self.assertTrue(xx.start == xx.stop == 0)
            self.assertTrue(yy.start == yy.stop == 0)
            self.assertTrue(pix.shape == (0,0))

            xx, yy, pix = self.psf.xypix(ispec, self.psf.wmax+1)
            self.assertTrue(xx.start == xx.stop == 0)                            
            self.assertTrue(yy.start == yy.stop == self.psf.npix_y)
            self.assertTrue(pix.shape == (0,0))
            
        
    #- Test getting x and y at the same time
    def test_xy(self):
        x = self.psf.x(0)
        y = self.psf.y(0)
        xy = self.psf.xy(0)
        self.assertTrue(N.all(xy[0] == x))
        self.assertTrue(N.all(xy[1] == y))
        
    #- Test getting x and y and wavelength at the same time
    def test_xyw(self):
        x = self.psf.x(0)
        y = self.psf.y(0)
        w = self.psf.wavelength(0)
        xyw = self.psf.xyw(0)
        self.assertTrue(N.all(xyw[0] == x))
        self.assertTrue(N.all(xyw[1] == y))
        self.assertTrue(N.all(xyw[2] == w))
    
    #- Test getting xy pixel range where spectra would project
    def test_xyrange(self):
        ww = self.psf.wavelength(0)[0:10]
        spec_range = [0,10]
        xmin,xmax,ymin,ymax = self.psf.xyrange(spec_range, ww)

        #- Test all wavelengths for first and last spectrum
        for i in range(spec_range[0], spec_range[-1]):
            for w in ww:
                xx, yy, pix = self.psf.xypix(i, w)
                if pix.shape == (0,0):  #- off edge of CCD
                    continue
                    
                self.assertGreaterEqual(xx.start, xmin)
                self.assertLessEqual(xx.stop, xmax)
                self.assertGreaterEqual(yy.start, ymin)
                self.assertLessEqual(yy.stop, ymax)

        #- Test all spectra for min and max wavelengths
        for i in range(spec_range[0], spec_range[-1]):
            for w in (ww[0], ww[-1]):
                xx, yy, pix = self.psf.xypix(i, w)
                if pix.shape == (0,0):  #- off edge of CCD
                    continue
                    
                self.assertGreaterEqual(xx.start, xmin)
                self.assertLessEqual(xx.stop, xmax)
                self.assertGreaterEqual(yy.start, ymin)
                self.assertLessEqual(yy.stop, ymax)

#- Test Pixellated PSF format
class TestPixPSF(TestPSF):
    def setUp(self):
        self.psf = load_psf(test_data_dir() + "/psf-pix.fits")

#- Test SpotGrid PSF format
class TestSpotPSF(TestPSF):
    def setUp(self):
        self.psf = load_psf(test_data_dir() + "/psf-spot.fits")

#- Test SpotGrid PSF format
class TestMonoSpotPSF(TestPSF):
    def setUp(self):
        self.psf = load_psf(test_data_dir() + "/psf-monospot.fits")
        
if __name__ == '__main__':
        
    # unittest.main()           
    s1 = unittest.defaultTestLoader.loadTestsFromTestCase(TestPixPSF)
    s2 = unittest.defaultTestLoader.loadTestsFromTestCase(TestSpotPSF)
    s2 = unittest.defaultTestLoader.loadTestsFromTestCase(TestMonoSpotPSF)
    suite = unittest.TestSuite([s1, s2])
    unittest.TextTestRunner(verbosity=2).run(suite)
    # suite = unittest.TestSuite()
    # suite.addTest(TestPixPSF())
    # suite.addTest(TestSpotPSF())
    # suite.run(unittest.TestResult())
