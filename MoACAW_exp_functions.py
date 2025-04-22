from qgis.core import *
from qgis.gui import *

#Peak Flow Rate
@qgsfunction(args="auto",group="Automated Culvert Analysis Workflow")
def Qp(value1, value2, value3, value4, value5, feature, parent):
    """
    Calculates the sum of the two parameters value1 and value2.
    value1=Ia (0.2)
    value2=cn
    value3=design rainfall, inch
    value4=Tc, Hr
    value5-basin area, acre
    <h2>Example usage:</h2>
    <ul>
      <li>my_sum(5, 8) -> 13</li>
      <li>my_sum("field1", "field2") -> 42</li>
    </ul>
    """
    S= (1000 / value2) - 10
    Ia=value1*S
    
    if value3 <= Ia:
        r=0
    else:
        r=(value3 - Ia) ** 2 / (value3 - Ia + S)
    
    
    #Qp= ((484/value4)*r*value5)/ 144
    Qp= 0.208*((value5/247.1)*(r*25.4)/(0.7*value4))
    #Qp=r*(1.007*(value5/0.67*value4)*0.75)
    #Tp=0.7Tc, Qp=0.208(are*r)/Tp
    
    return Qp

#Time of Concentration
@qgsfunction(args="auto",group="Automated Culvert Analysis Workflow")
def Tc(lfp_length, CN, lfp_slope, units, feature, parent):
    """
    Calculates the sum of the two parameters value1 and value2.
    lfp_length=longest flow path length, ft
    CN=Curve Number
    lfp_slope=average slope of longest flowpath
    units='ft' for feet, 'm' for meters 
    """
    if units=='ft':
        Tc=((lfp_length**0.8*((1000/CN)-10)+1)**0.7)/(1140* lfp_slope**0.5)
    if units=='m':
        Tc=(((lfp_length*3.28084)**0.8*((1000/CN)-10)+1)**0.7)/(1140* lfp_slope**0.5)
    return Tc