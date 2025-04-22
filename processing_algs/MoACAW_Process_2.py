"""
Model exported as python.
Name : Process 2: Culvert Locations and Attributes
Group : Automated Culvert Analysis Workflow
With QGIS : 33603
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
import processing

from qgis.PyQt.QtGui import QIcon
import os
pluginPath = os.path.dirname(__file__)

#CulvertLocationsAndAttributes
class Process2(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterNumber('culvert_buffer_distance', 'Culvert Buffer Distance', type=QgsProcessingParameterNumber.Double, defaultValue=12))
        self.addParameter(QgsProcessingParameterRasterLayer('dem', 'DEM', defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('roads', 'Roads', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('stream_buffer_distance', 'Stream Buffer Distance', type=QgsProcessingParameterNumber.Double, defaultValue=3))
        self.addParameter(QgsProcessingParameterVectorLayer('streams', 'Streams', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        #self.addParameter(QgsProcessingParameterNumber('units_1_for_meters_2_for_feet', 'Units, 1 for meters 2 for feet.', type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=2, defaultValue=1))
        self.addParameter(QgsProcessingParameterFeatureSink('Process2CulvertPoints', 'Process 2 Culvert Points', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(11, model_feedback)
        results = {}
        outputs = {}

        # Culvert Points
        alg_params = {
            'INPUT': parameters['roads'],
            'INPUT_FIELDS': [''],
            'INTERSECT': parameters['streams'],
            'INTERSECT_FIELDS': [''],
            'INTERSECT_FIELDS_PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CulvertPoints'] = processing.run('native:lineintersections', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Delete duplicate geometries
        alg_params = {
            'INPUT': outputs['CulvertPoints']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DeleteDuplicateGeometries'] = processing.run('native:deleteduplicategeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Add autoincremental field
        alg_params = {
            'FIELD_NAME': 'OID',
            'GROUP_FIELDS': [''],
            'INPUT': outputs['DeleteDuplicateGeometries']['OUTPUT'],
            'MODULUS': 0,
            'SORT_ASCENDING': True,
            'SORT_EXPRESSION': None,
            'SORT_NULLS_FIRST': False,
            'START': 1,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddAutoincrementalField'] = processing.run('native:addautoincrementalfield', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Culverts Buffered
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': parameters['culvert_buffer_distance'],
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['AddAutoincrementalField']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CulvertsBuffered'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Stream Zone Clip
        alg_params = {
            'INPUT': parameters['streams'],
            'OVERLAY': outputs['CulvertsBuffered']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StreamZoneClip'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Streams Buffer
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': parameters['stream_buffer_distance'],
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['StreamZoneClip']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StreamsBuffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Culvert Zone Clip
        alg_params = {
            'INPUT': outputs['CulvertsBuffered']['OUTPUT'],
            'OVERLAY': outputs['StreamsBuffer']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CulvertZoneClip'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Culvert Zones
        alg_params = {
            'INPUT': outputs['CulvertZoneClip']['OUTPUT'],
            'LINES': parameters['roads'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CulvertZones'] = processing.run('native:splitwithlines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Culvert Zone Stats
        alg_params = {
            'COLUMN_PREFIX': '_',
            'INPUT': outputs['CulvertZones']['OUTPUT'],
            'INPUT_RASTER': parameters['dem'],
            'RASTER_BAND': 1,
            'STATISTICS': [5,6],  # Minimum,Maximum
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CulvertZoneStats'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Aggregate
        alg_params = {
            'AGGREGATES': [{'aggregate': 'first_value','delimiter': ',','input': '"OID"','length': 0,'name': 'OID','precision': 0,'sub_type': 0,'type': 2,'type_name': 'integer'},{'aggregate': 'maximum','delimiter': ',','input': 'if( @dem_vertical_units_1_for_meters_2_for_feet is 1,"_min"*3.28084,"_min")','length': 0,'name': 'us_invert','precision': 0,'sub_type': 0,'type': 6,'type_name': 'double precision'},{'aggregate': 'minimum','delimiter': ',','input': 'if( @dem_vertical_units_1_for_meters_2_for_feet is 1,"_min"*3.28084,"_min")','length': 0,'name': 'ds_invert','precision': 0,'sub_type': 0,'type': 6,'type_name': 'double precision'},{'aggregate': 'maximum','delimiter': ',','input': 'if( @dem_vertical_units_1_for_meters_2_for_feet is 1,"_max"*3.28084,"_max")','length': 0,'name': 'crown','precision': 0,'sub_type': 0,'type': 6,'type_name': 'double precision'}],
            'GROUP_BY': 'OID',
            'INPUT': outputs['CulvertZoneStats']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Aggregate'] = processing.run('native:aggregate', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Join attributes by field value
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'OID',
            'FIELDS_TO_COPY': [''],
            'FIELD_2': 'OID',
            'INPUT': outputs['AddAutoincrementalField']['OUTPUT'],
            'INPUT_2': outputs['Aggregate']['OUTPUT'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': None,
            'OUTPUT': parameters['Process2CulvertPoints']
        }
        outputs['JoinAttributesByFieldValue'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Process2CulvertPoints'] = outputs['JoinAttributesByFieldValue']['OUTPUT']
        return results

    def name(self):
        return 'Process 2: Culvert Locations and Attributes'

    def displayName(self):
        return 'Process 2: Culvert Locations and Attributes'

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
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:18pt; font-weight:600;">Process 2: Culvert Locations and Elevation Attributes</span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">This Model identifies culvert locations and assigns elevation attributes from DEM data, it is the second process in the Automated Culvert Analysis Workflow.</p></body></html></p>
<h2>Input parameters</h2>
<h3>Culvert Buffer Distance</h3>
<p>Search distance for culvert elevation attributes from culvert point.</p>
<h3>DEM</h3>
<p>Preprocessed elevation DEM.</p>
<h3>Roads</h3>
<p>Roads Layer, should be filtered to only include roadways of interest.</p>
<h3>Stream Buffer Distance</h3>
<p>Search distance for culvert elevation attributes from stream centerline</p>
<h3>Streams</h3>
<p>Vector Streams from Process 1.</p>
<br></body></html>"""

    def createInstance(self):
        return Process2()
#<h3>Units, 1 for meters 2 for feet.</h3>
#<p>For unit conversion, note: All layers should be in same CRS.</p>