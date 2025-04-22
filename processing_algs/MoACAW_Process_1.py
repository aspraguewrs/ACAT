"""
Model exported as python.
Name : Process 1: Hydroconditioning and Stream Creation
Group : Automated Culvert Analysis Workflow
With QGIS : 33603
"""
from qgis.core import QgsProcessingParameterRasterDestination 
from qgis.PyQt.QtCore import QCoreApplication

from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer, QgsProcessingParameterRasterDestination,
    QgsProcessingParameterVectorDestination,QgsProcessingParameterNumber,
    QgsProcessingException, QgsProcessingMultiStepFeedback)

import processing

from qgis.PyQt.QtGui import QIcon
import os
pluginPath = os.path.dirname(__file__)

#HydroconditioningAndStreamCreation
class Process1(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    BREACH = 'BREACH'
    LC_BREACH = 'OUTPUT_LC_BREACH'
    D8_POINTER ='D8_POINTER'
    D8_FLOW_ACCUM ='D8_FLOW_ACCUM'
    RASTER_STREAMS ='RASTER_STREAMS'

    def initAlgorithm(self, config=None):
        # Input Terrain DEM resampled to desired cell size, 
        # 2 meters is a good lower limit on cell size.
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                'Input DEM Layer',
                defaultValue=None
            )
        )

        # Distance in cells algorithm will
        # search to find a breach path.
        # Should be a length at least as large as the
        # expected roadway enbankment length,
        # e.g. 40 feet for 2 lane road. 
        self.addParameter(
            QgsProcessingParameterNumber(
                'search_distance', 'Search Distance',
                type=QgsProcessingParameterNumber.Integer,
                minValue=1, maxValue=50, defaultValue=5
            )
        )

        # This is the maximum depth the algorithm will breach the DEM.
        # Should be set to at least the maximum expected imbankment height.
        self.addParameter(
            QgsProcessingParameterNumber(
                'maximum_breach_cost_z_units', 'Maximum Breach Cost Z Units',
                type=QgsProcessingParameterNumber.Integer, minValue=1,
                maxValue=50, defaultValue=10
            )
        )
        
        # Channelization Threshold sets the minimum contribiting area
        # required for the algorithm to designate a given raster cell
        # as a stream cell. Area is in number of raster cells.
        # I have found that an area of 5 acres generally works pretty well. 
        self.addParameter(
            QgsProcessingParameterNumber(
                'channelization_threshold', 'Channelization Threshold',
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=200000
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.BREACH, 'Least Cost Breached DEM',
                createByDefault=True, defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.LC_BREACH, 'Double Breached DEM',
                createByDefault=True, defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.D8_POINTER, 'D8 Pointer',
                createByDefault=True, defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.D8_FLOW_ACCUM, 'D8 Flow Accumulation',
                createByDefault=True, defaultValue=''
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.RASTER_STREAMS, 'Raster Streams',
                createByDefault=True, defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorDestination(
                'StreamLines', 'Stream Lines',
                type=QgsProcessing.TypeVectorLine,
                createByDefault=True, defaultValue=None
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(6, model_feedback)
        results = {}
        outputs = {}

        dem =           self.parameterAsRasterLayer(
                            parameters, self.INPUT, context
                        )

        breach =        self.parameterAsOutputLayer(
                            parameters, self.BREACH, context
                        )

        lc_breach =     self.parameterAsOutputLayer(
                            parameters, self.LC_BREACH, context
                        )

        d8_pointer =    self.parameterAsOutputLayer(
                            parameters, self.D8_POINTER, context
                        )

        d8_flow_accum = self.parameterAsOutputLayer(
                            parameters, self.D8_FLOW_ACCUM, context
                        )

        raster_streams = self.parameterAsOutputLayer(
                            parameters, self.RASTER_STREAMS, context
                        )

        # BreachDepressionsLeastCost
        alg_params = {
            'dem': dem,
            'dist': parameters['search_distance'],
            'fill': False,
            'flat_increment': None,
            'max_cost': parameters['maximum_breach_cost_z_units'],
            'min_dist': True,
            'output': breach
        }
        outputs['Breachdepressionsleastcost'] = (
            processing.run(
                'wbt:BreachDepressionsLeastCost', alg_params, context=context,
                feedback=feedback, is_child_algorithm=True
            )
        )
        results['LeastCostBreachedDem'] = outputs['Breachdepressionsleastcost']['output']

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # BreachDepressions
        alg_params = {
            'dem': breach,
            'fill_pits': True,
            'flat_increment': None,
            'max_depth': None,
            'max_length': None,
            'output': lc_breach
        }
        outputs['Breachdepressions'] = (
            processing.run(
                'wbt:BreachDepressions', alg_params, context=context,
                feedback=feedback, is_child_algorithm=True
            )
        )
        results['DoubleBreachedDem'] = outputs['Breachdepressions']['output']

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # D8Pointer
        alg_params = {
            'dem': lc_breach,
            'esri_pntr': False,
            'output': d8_pointer
        }
        outputs['D8pointer'] = (
            processing.run(
                'wbt:D8Pointer', alg_params, context=context,
                feedback=feedback, is_child_algorithm=True
            )
        )
        results['D8Pointer'] = outputs['D8pointer']['output']

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # D8FlowAccumulation
        alg_params = {
            'clip': False,
            'esri_pntr': False,
            'input': d8_pointer,
            'log': False,
            'out_type': 2,  # specific contributing area
            'pntr': True,
            'output': d8_flow_accum
        }
        outputs['D8flowaccumulation'] = (
            processing.run(
            'wbt:D8FlowAccumulation', alg_params, context=context,
            feedback=feedback, is_child_algorithm=True
            )
        )
        results['D8FlowAccumulation'] = outputs['D8flowaccumulation']['output']

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # ExtractStreams
        alg_params = {
            'flow_accum': d8_flow_accum,
            'threshold': parameters['channelization_threshold'],
            'zero_background': False,
            'output': raster_streams
        }
        outputs['Extractstreams'] = (
            processing.run(
                'wbt:ExtractStreams', alg_params, context=context,
                feedback=feedback, is_child_algorithm=True
            )
        )
        results['RasterStreams'] = outputs['Extractstreams']['output']

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # RasterStreamsToVector
        alg_params = {
            'd8_pntr': outputs['D8pointer']['output'],
            'esri_pntr': False,
            'streams': outputs['Extractstreams']['output'],
            'output': parameters['StreamLines']
        }
        outputs['Rasterstreamstovector'] = (
            processing.run(
                'wbt:RasterStreamsToVector', alg_params, context=context,
                feedback=feedback, is_child_algorithm=True
            )
        )
        results['StreamLines'] = outputs['Rasterstreamstovector']['output']

        return results

    def name(self):
        return 'Process 1: Hydroconditioning and Stream Creation'

    def displayName(self):
        return 'Process 1: Hydroconditioning and Stream Creation'

    def group(self):
        return 'Automated Culvert Analysis Workflow'

    def groupId(self):
        return 'Automated Culvert Analysis Workflow'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons/Mo.svg'))

    def svgIconPath(self):
        return os.path.join(pluginPath, "icons", "Mo.svg")

    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">This model will generate the hydroconditioned raster layers and vector streams layer needed for culvert analysis. This model is a combination of 6 whitebox tools processing algorithms and is the first process in the Automated Culvert Analysis Workflow. Project Projection should be EPSG:26915</p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">   </p></body></html></p>
<h2>Input parameters</h2>
<h3>Terrain DEM</h3>
<p>Input Terrain DEM resampled to desired cell size, 2 meters is a good lower limit on cell size.</p>
<h3>Search Distance</h3>
<p>Distance in cells the BreachDepressionsLeastCost algorithm will search to find a breach path. Should be at lest the length of the widest expected roadway embankment.</p>
<h3>Maximum Breach Cost Z Units</h3>
<p>The maximum depth the BreachDepressionsLeastCost algorithm will breach the DEM. Should be set to at least the maximum expected imbankment height.</p>
<h3>Channelization Threshold</h3>
<p>Channelization Threshold sets the minum contributing area flowing into a cell for the ExtractStreams algorithm to recognize it as a stream cell. Area is in number of cells. Generally about 5 acres works well.</p>
<h2>Outputs</h2>
<h3>D8 Flow Accumulation</h3>
<p>Output flow accumulation raster
</p>
<h3>D8 Pointer</h3>
<p>Output D8 Pointer raster</p>
<h3>Raster Streams</h3>
<p>Output Raster Streams</p>
<h3>Stream Lines</h3>
<p>Final output: Vectorized Streams Polylines.</p>
<br><p align="right">Algorithm author: Aaron Sprague, Water Resources Solutions</p><p align="right">Help author: Aaron Sprague, Water Resources Solutions</p></body></html>"""

    def helpUrl(self):
        return 'www.wrs-rc.com'

    def createInstance(self):
        return Process1()
'''<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-style:italic;">Note: User must select an output file path for all outputs. Model will not work if save to temporary layer is selected.</span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-style:italic;">   </span></p>'''