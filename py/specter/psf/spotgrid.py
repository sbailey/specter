#!/usr/bin/env python
"""
SpotGridPSF - Linear interpolate hi-res sampled spots to model PSF

Stephen Bailey
Fall 2012
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import os
import numpy as np
from astropy.io import fits
from specter.psf import PSF
from specter.util import LinearInterp2D, rebin_image, sincshift
import scipy.interpolate
import time

class SpotGridPSF(PSF):
    """
    Model PSF with a linear interpolation of high resolution sampled spots
    """
    def __init__(self, filename):
        """
        Initialize SpotGridPSF from input file
        
        See specter.psf.PSF for futher details
        """
        #- Use PSF class to Load Generic PSF values (x, y, wavelength, ...)
        PSF.__init__(self, filename)
        
        #- Load extensions specific to this PSF type
        fx = fits.open(filename, memmap=False)
        self._spots = fx['SPOTS'].data        #- PSF spots
        # self._spotx  = fx['SPOTX'].data     #- X location of spots
        # self._spoty  = fx['SPOTY'].data     #- Y location of spots
        self._fiberpos = fx['FIBERPOS'].data  #- Location of fibers on slit
        self._spotpos = fx['SPOTPOS'].data    #- Slit loc of sampled spots
        self._spotwave = fx['SPOTWAVE'].data  #- Wavelengths of spots
        
        #- 2D linerar interpolators
        pp = self._spotpos
        ww = self._spotwave
        self._fspot = LinearInterp2D(pp, ww, self._spots)
        # self._fx    = LinearInterp2D(pp, ww, self._spotx)
        # self._fy    = LinearInterp2D(pp, ww, self._spoty)
        
        #- Read spot vs. CCD pixel scales from header
        hdr = fx[0].header
        self.CcdPixelSize = hdr['CCDPIXSZ']  #- CCD pixel size in mm
        self.SpotPixelSize = hdr['PIXSIZE']  #- Spot pixel size in mm
        
        fx.close()
        
    def _xypix(self, ispec, wavelength):
        """
        Return xslice, yslice, pix for PSF at spectrum ispec, wavelength
        """
        return self._xypix_interp(ispec, wavelength)
    
    def _xypix_interp(self, ispec, wavelength):
        """
        Return xslice, yslice, pix for PSF at spectrum ispec, wavelength
        """
        #add timer for whole function ---------------------------------------------
        xypix_interp_t0=time.time()
        
        #- Ratio of CCD to Spot pixel sizes
        #rebinning timer ------------------------------
        rebin_t0=time.time()
        rebin = int(self.CcdPixelSize / self.SpotPixelSize)
        
        p, w = self._fiberpos[ispec], wavelength
        pix_spot_values=self._fspot(p, w)
        nx_spot=pix_spot_values.shape[1]
        ny_spot=pix_spot_values.shape[0]
        nx_ccd=nx_spot//rebin+1 # add one bin because of resampling
        ny_ccd=ny_spot//rebin+1 # add one bin because of resampling
        
        xc, yc = self.xy(ispec, wavelength) # center of PSF in CCD coordinates
        
        rebin_t1=time.time()
        rebin_elapsed_t=rebin_t1-rebin_t0
        #done timing rebinning -----------------------------
        #print("rebin_interp elapsed time is %s s" %(rebin_elapsed_t))
                
        #timer for pixel offset --------------------
        offset_t0=time.time()
                
        # fraction pixel offset requiring interpolation
        dx=xc*rebin-int(np.floor(xc*rebin)) # positive value between 0 and 1
        dy=yc*rebin-int(np.floor(yc*rebin)) # positive value between 0 and 1
        # weights for interpolation
        w00=(1-dy)*(1-dx)
        w10=dy*(1-dx)
        w01=(1-dy)*dx
        w11=dy*dx        
        # now the rest of the offset is an integer shift
        dx=int(np.floor(xc*rebin))-int(np.floor(xc))*rebin # positive integer between 0 and 14
        dy=int(np.floor(yc*rebin))-int(np.floor(yc))*rebin # positive integer between 0 and 14
        
        offset_t1=time.time()
        offset_elapsed_t=offset_t1-offset_t0
        #done timing offset -----------------------
        #print("offset elapsed time is %s s" %(offset_elapsed_t))
        
        #start timer for resampling grid -----------------------
        resample_t0=time.time()
        
        # resampled spot grid      
        resampled_pix_spot_values=np.zeros((ny_spot+rebin,nx_spot+rebin))            
        resampled_pix_spot_values[dy:ny_spot+dy,dx:nx_spot+dx]         += w00*pix_spot_values
        resampled_pix_spot_values[dy+1:ny_spot+dy+1,dx:nx_spot+dx]     += w10*pix_spot_values
        resampled_pix_spot_values[dy:ny_spot+dy,dx+1:nx_spot+dx+1]     += w01*pix_spot_values
        resampled_pix_spot_values[dy+1:ny_spot+dy+1,dx+1:nx_spot+dx+1] += w11*pix_spot_values
        #add shape check to see what we're dealing with
        print("dimensions of pix_spot_values %s" %(pix_spot_values.shape))
        
        resample_t1=time.time()
        #done timing resample ------------------------------
        resample_elapsed_t=resample_t1-resample_t0
        #print("resample elapsed time is %s s" %(resample_elapsed_t))
            
        #start timing ccd_rebin -------------------------------
        ccd_rebin_t0=time.time()
        # rebinning
        ccd_pix_spot_values=resampled_pix_spot_values.reshape(ny_spot+rebin,nx_ccd,rebin).sum(2).reshape(ny_ccd,rebin,nx_ccd).sum(1)
        # make sure it's positive
        ccd_pix_spot_values[ccd_pix_spot_values<0]=0.
        # normalize
        norm = np.sum(ccd_pix_spot_values)
        if norm > 0 :
            ccd_pix_spot_values /= norm
            
        ccd_rebin_t1=time.time()
        #done timing ccd_rebin ----------------------------------
        ccd_rebin_elapsed_t=ccd_rebin_t1-ccd_rebin_t0
        #print("ccd_rebin elapsed time is % s" %(ccd_rebin_elapsed_t))
        
        #start timing ccd_slice ------------------------------
        ccd_slice_t0=time.time()

        x_ccd_begin = int(np.floor(xc))-nx_ccd//2+1  # begin of CCD coordinate stamp
        y_ccd_begin = int(np.floor(yc))-ny_ccd//2+1  # begin of CCD coordinate stamp
        xx = slice(x_ccd_begin, (x_ccd_begin+nx_ccd))
        yy = slice(y_ccd_begin, (y_ccd_begin+ny_ccd))
        
        ccd_slice_t1=time.time()
        #done timing ccd_slice -------------------------------
        ccd_slice_elapsed_t=ccd_slice_t1-ccd_slice_t0
        #print("ccd_slice elapsed time is % s" %(ccd_slice_elapsed_t))
        

        #add final timer
        xypix_interp_t1=time.time()
        xypix_elapsed_t=xypix_interp_t1-xypix_interp_t0
        
        #done timing -------------------------------------------------------
        #print("_xypix_interp elapsed time is %s s" %(xypix_elapsed_t))
        
        #now compute fraction of time each part of xypix_interp each time block takes
        rebin_frac=rebin_elapsed_t/xypix_elapsed_t
        offset_frac=offset_elapsed_t/xypix_elapsed_t
        resample_frac=resample_elapsed_t/xypix_elapsed_t
        ccd_rebin_frac=ccd_rebin_elapsed_t/xypix_elapsed_t
        ccd_slice_frac=ccd_slice_elapsed_t/xypix_elapsed_t
        #for a sanity check, check total fraction tracked
        total_frac=rebin_frac + offset_frac + resample_frac + ccd_rebin_frac + ccd_slice_frac
        
        print("rebin fraction used is %s" %(rebin_frac))
        print("offset fraction used is %s" %(offset_frac))
        print("resample fraction used is %s" %(resample_frac))
        print("ccd_rebin fraction used is %s" %(ccd_rebin_frac))
        print("ccd_slice fraction used is %s" %(ccd_slice_frac))
        print("total fraction tracked is %s"%(total_frac))
        
        return xx,yy,ccd_pix_spot_values

        
        
        
    def _value(self, x, y, ispec, wavelength):

        """
        return PSF value (same shape as x and y), NOT integrated, for display of PSF.

        Arguments:
          x: x-coordinates baseline array
          y: y-coordinates baseline array (same shape as x)
          ispec: fiber
          wavelength: wavelength
        """

        
        p, w = self._fiberpos[ispec], wavelength
        pix_spot_values=self._fspot(p, w)
        nx_spot=pix_spot_values.shape[1]
        ny_spot=pix_spot_values.shape[0]
        x_spot=(np.arange(nx_spot)-nx_spot//2)
        y_spot=(np.arange(ny_spot)-ny_spot//2)
        spline=scipy.interpolate.RectBivariateSpline(x_spot,y_spot,pix_spot_values,kx=2, ky=2, s=0)
        
        xc, yc = self.xy(ispec, wavelength) # center of PSF in CCD coordinates
        ratio=self.CcdPixelSize/self.SpotPixelSize
        
        xr=x.ravel()
        yr=y.ravel()
        
        #img=spline((x-xc)*ratio,(y-yc)*ratio)
        #return img/np.sum(img)
        img=np.zeros(xr.shape)
        for i in range(xr.size) :
            img[i]=spline((xr[i]-xc)*ratio,(yr[i]-yc)*ratio)
        return img.reshape(x.shape)


        
        
        
