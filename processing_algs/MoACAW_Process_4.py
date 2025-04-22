from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm, QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterField, 
                       QgsFeature, QgsField)
from qgis import processing
from .channelflowlib.openchannellib import IrregularSection

from qgis.PyQt.QtGui import QIcon
import os
pluginPath = os.path.dirname(__file__)

#CulvertHydraulics
class Process4(QgsProcessingAlgorithm):
    CULVERT_POINTS = 'CULVERT_POINTS'
    #LFP = 'LFP'
    CN = 'CN'
    S_LFP = 'S_LFP'
    B_AREA = 'B_AREA'
    Q_P = 'Q_P'
    #C_H = 'C_H'
    #LS ='L_S'
    #TC = 'TC'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.CULVERT_POINTS,
                self.tr('Culvert Points'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.CN,
                self.tr('Curve Number'),
                '',
                self.CULVERT_POINTS
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.S_LFP,
                self.tr('Slope of Longest Flow Path, ft/ft'),
                '',
                self.CULVERT_POINTS
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.B_AREA,
                self.tr('Culvert Basin Area, acre'),
                '',
                self.CULVERT_POINTS
            )
        )
    
        self.addParameter(
            QgsProcessingParameterField(
                self.Q_P,
                self.tr('Culvert Design Discharge, CFS'),
                '',
                self.CULVERT_POINTS
            )
        )
        
    def processAlgorithm(self, parameters, context, feedback):
        culvert_points = self.parameterAsVectorLayer(parameters, self.CULVERT_POINTS, context)
        s_lfp_name = self.parameterAsString(parameters, self.S_LFP, context)
        b_area_name = self.parameterAsString(parameters, self.B_AREA, context)
        q_p_name = self.parameterAsString(parameters, self.Q_P, context)
        ls_name = 'LS'
        h_name = 'Height'
        w_name = 'Width'
        tw_name = 'Tw'
        hh_name = 'HH'
        us_invert_name = 'us_invert'
        ds_invert_name = 'ds_invert'
        crown_name = 'crown'
        overtop_name= 'overtop?'
                
        culvert_points.startEditing()       
        culvert_points.dataProvider().addAttributes([QgsField(h_name, QVariant.Double)])
        culvert_points.dataProvider().addAttributes([QgsField(w_name, QVariant.Double)])
        culvert_points.dataProvider().addAttributes([QgsField(ls_name, QVariant.Double)])
        culvert_points.dataProvider().addAttributes([QgsField(tw_name, QVariant.Double)])
        culvert_points.dataProvider().addAttributes([QgsField(hh_name, QVariant.Double)])
        culvert_points.dataProvider().addAttributes([QgsField(overtop_name, QVariant.Bool)])
        culvert_points.updateFields()
              
        for feature in culvert_points.getFeatures():
            q_p=feature[q_p_name]
            crown = feature[crown_name]
            us_invert = feature[us_invert_name]
            s_lfp = feature[s_lfp_name]
            b_area = feature[b_area_name]
            ds_invert = feature[ds_invert_name]


            if ((crown - ds_invert)*3.28084) - 1.0>12:
                h =  12

            elif ((crown - ds_invert)*3.28084) - 1.0>3:
                h =  ((crown - ds_invert)*3.28084) - 1.0
            else:
                h= 3           

            if 4.612 - 0.779 * s_lfp - 0.004 * b_area + 0.002 * ((b_area * 43560) ** 0.5)>4:
                w = 4.612 - 0.779 * s_lfp - 0.004 * b_area + 0.002 * ((b_area * 43560) ** 0.5)
            else:
                w = 4

            '''
            if (us_invert-ds_invert)*3.28084>2.0:
                ls = 2.0       
            elif (us_invert-ds_invert)*3.28084>0:
                ls = (us_invert-ds_invert)*3.28084
            else:
                ls = 0.001 
            '''
            ls=0.6
            tw = self.twAlgo(q_p, s_lfp/3.0, h/2.0, w*1.5) 
            hh = self.culCap(q_p, h, w, tw, ls)  

            if (h)+1.2>hh:
                otp=False
            else:
                otp=True

            culvert_points.changeAttributeValue(feature.id(), culvert_points.fields().indexOf(h_name), h)   
            culvert_points.changeAttributeValue(feature.id(), culvert_points.fields().indexOf(w_name), w)       
            culvert_points.changeAttributeValue(feature.id(), culvert_points.fields().indexOf(ls_name), ls)
            culvert_points.changeAttributeValue(feature.id(), culvert_points.fields().indexOf(tw_name), tw)
            culvert_points.changeAttributeValue(feature.id(), culvert_points.fields().indexOf(hh_name), hh)
            culvert_points.changeAttributeValue(feature.id(), culvert_points.fields().indexOf(overtop_name), otp) 
    
        culvert_points.commitChanges()

        return ()
    
    def twAlgo(self, Q, S, ch, cw, css=3, pss=25, pw=600, n=0.05):
        
        pts = (
            (0.0, 100),
            (0.0, (0.5*pw)/pss),
            ((0.5*pw)-(0.5*cw)-(ch*css), ch),
            ((0.5*pw)-(0.5*cw),0.0),
            ((0.5*pw)+(0.5*cw),0.0),
            ((0.5*pw)+(0.5*cw)+(ch*css), ch),
            (pw, (0.5*pw)/pss),
            (pw, 100)
        )

        channel = IrregularSection(pts)
        channel.set_average_rougness(n)
        channel.set_bed_slope(S)

        max_elev = 100
        min_elev = 0.1
        interval = 0.1
        intervals = ((max_elev - min_elev) / interval)

        elevs = [0]
        discharges = [0]

        for i in range(int(intervals) + 1):
            elev = min_elev + (i * interval)

            channel.set_water_elevation(elev)
            channel.analyze()

            discharge = channel.discharge

            elevs.append(elev)
            discharges.append(discharge)
        
        import numpy as np

        elevs=np.array(elevs)
        discharges=np.array(discharges)
        rc=np.array([elevs,discharges])
        rc=np.transpose(rc)
        idx=(np.abs(discharges-Q)).argmin()
        wse=elevs[idx]
        wse=float(wse)
        
        return (wse)
        
    def culCap(self, Q, D, B, TW, LS, N=0.013, L=30):
        '''
        Computes the Estimated Culvert Capacity using HDS-5 Methodology

        <li>value1= flow rate, cfs</li>
        <li>value2= height of barrel, ft</li>
        <li>value3= #width of barrel, ft</li>
        <li>value4= #length of barrel, ft</li>
        <li>value5= drop through barrel, ft</li>
        <li>value6= tailwater depth, ft</li>
      
        Simplistic Culvert capacity Analysis using HDS-5 methodology, specifically the equations from appendix A.
        Author: Aaron Sprague, Water Resources Solutions LLC
        Date: September 2024
        Contact: asprague@wrs-rc.com

        variable list-
        HWi= Headwater depth above inlet control section invert, ft =
        D= Interior height of culvert barrel, ft =
        dc= crital depth, ft =  (q^2g)^(1/3)
        q=unit discharge box culvert full flow, cfs ft = D
        Vc= Velocity at critical depth, ft/s 
        Hc= Specific head at critical depth,ft = dc + Vc^2/2g
        Qc= Ap(gYh)^0.5
        Ap= Area of flow prism, ft^2
        g= 32.17
        Q= Discharge, ft^3/s =
        A= Full cross sectional area of culvert barrel, ft^2 =
        S= Culvert barrel slope, ft/ft =
        K,M,c,Y = Constants from Tables A.1 A.2 A.3 = 0.061, 0.75, 0.0423, 0.82 
        Ku= Unit conversion = 1
        Ks= Slope correction = -0.5
        N = mannings n
        b = Width of culvert, ft
        culvert_flow = (1.49 / mannings_n) * D * (culvert_height / (2*D ** (2/3)) * (slope_ft_per_ft ** 0.5)
        '''

        '''inlet control'''
        #acceleration due to gravity ft/s^2
        g= 32.17
        #Unit and Slope Correction HDS-5 A.2.1 Pg 191
        Ku, Ks=1,-0.5 
        #Constants from HDS-5 Third Edition Table A-1 
        K,M,c,Y=0.061,0.75,0.0423,0.82
        #Q= flow rate cfs, placeholder get from GIS
        #D= height of barrel, placeholder get from GIS
        #B= width of barrel, placeholder get from GIS
        #L= length of barrel, placeholder get from GIS
        A= D*B      #cross sectional area of full barell
        #N= manning friction factor
        S= 0.02 #slope of barrel, ft/ft 
        
        q=Q/B                   #unit flow rate aka 'little q'
        dc=(q**2/g)**(1/3)      #critical depth
        Vc= (g*dc)**(1/2)       #critical velocity using Froude
        Hc= dc+((Vc**2)/(2*g))  #Specific head at critical depth
        Q_AD=Q/(A*D**0.5)       #ratio for applicability of equations

        if Q_AD <= 3.5:
            #HDS-5 EQ A.1
            HWi_D=((Hc/D)+K*(Ku*Q/(A*D**0.5))**M)+Ks*S
        elif Q_AD>=4.0:
            #HDS-5 EQ A.3
            HWi_D= c*(Ku*Q/(A*D**0.5))**2+Y+Ks*S
        else:
            #linear interpolation between equations A.1 and A.3
            HWi_D=1.109*Q_AD+0.1185
        HW=HWi_D/D #flow depth above upstream culvert invert

        print("Q_AD is", Q_AD)
        print("HWi_D is", HWi_D)

        '''outlet control'''
        #full flow
        #TW= tailwater depth above the outlet invert, ft optain from manning for downstream channel
        #LS= drop through culvert
        ke=0.5      #enterance loss coefficient
        Ku=29       #unit constant USC:29 SI:19.63

        V=Q/A       #barrel velocity
        Hv=(V**2)/(2*g) #velocity head
        He=ke*Hv    #enterance loss
        Hf= ((Ku*(N**2)*L)/(A/(2*D+2*B))**1.33)*Hv #friction loss in barrel
        #Ho=Hv
        H=2*Hv+He+Hf #total barrel losses
        LS=L*S
        if ((dc+D)/2)>TW:
            HW0=((dc+D)/2)+H-LS
        else:
            HW0= TW +H-LS

        if HW0>HW:
            HH=HW0
        else:
            HH=HW
        
        return HH

    def name(self):
        return 'culverthydraulics'

    def displayName(self):
        return self.tr('Process 4: Culvert Hydraulics')

    def group(self):
        return self.tr('Automated Culvert Analysis Workflow')

    def groupId(self):
        return 'Automated Culvert Analysis Workflow'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons/Mo.svg'))

    def svgIconPath(self):
        return os.path.join(pluginPath, "icons", "Mo.svg")


    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">This proccessing algorithm calculates the hydraulic parameters for the culverts identified in Process 2 with Hydrology attributes from Process 3. Computed Hydraulic attributes are added to the input layer attribute table.</p>
<h2>Input parameters</h2>
<h3>Culvert Points</h3>
<p>Output point layer from Process 3: Culvert Hydrology</p>
<h3>Curve Number</h3>
<p>Curve Number attribute field.</p>
<h3>Slope of the Longest Flow Path</h3>
<p>Longest flow path slope, attribute field.</p>
<h3>Cuvert Basin Area, acre</h3>
<p>Culver Basin Area in acres, attribute field.</p>
<h3>Culvert Design Discharge, CFS</h3>
<p>Culvert design discharge in CFS, attribute field.</p>
<p>Time of concentration in hours, attribute field.</p>
<br><p align="right">Algorithm author: Aaron Sprague, Water Resources Solutions</p><p align="right">Help author: Aaron Sprague, Water Resources Solutions</p></body></html>"""

    def createInstance(self):
        return Process4()
#<h3>Longest Flow Path, ft</h3>
#<p>Longest Flow path attribute field in feet.</p>
#<h3>Time of Concentration, hr</h3>