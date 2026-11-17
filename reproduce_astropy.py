"""Run in the wheel environment. Reproduces negative-longitude interpolation failure."""
import numpy as np
import astropy.units as u
from astropy_healpix import HEALPix
from importlib.metadata import version
hp=HEALPix(nside=8,order='ring')
lo,la=hp.healpix_to_lonlat(np.arange(768))
values=2+np.cos(la.to_value(u.rad))*np.cos(lo.to_value(u.rad))
print('astropy-healpix',version('astropy-healpix'),'numpy',version('numpy'))
for longitude in [-177.5,182.5]:
    print(longitude,hp.interpolate_bilinear_lonlat(longitude*u.deg,-52.5*u.deg,values))
# The two requested longitudes represent exactly the same location.
