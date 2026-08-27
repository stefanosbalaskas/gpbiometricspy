from __future__ import annotations
from _shared import *
bio=pd.DataFrame({'participant':['P01','P01'],'time':[0.,1.],'GSR_US':[1.,1.2]}); gaze=pd.DataFrame({'participant':['P01','P01'],'time':[0.,1.],'FPOGX':[.2,.3],'FPOGY':[.4,.5]})
try: joined=gp.join_gazepoint_biometrics_to_gp3tools(bio,gaze,by=['participant','time'])
except TypeError: joined=gp.join_gazepoint_biometrics_to_gp3tools(bio,gaze)
finish('gp3tools-compatibility',joined=joined)
