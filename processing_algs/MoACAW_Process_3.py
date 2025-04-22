"""
*****Missouri Automated Culvert Analysis Workflow****

Created By: Aaron Sprague
Date:       09/19/2024
Email:      asprague@wrs-rc.com
QGIS Ver:   33603
"""
import os
import glob
import shutil
import processing
import tempfile
from pathlib import PureWindowsPath
from qgis.core import(
    QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback, QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterLayer, QgsProcessingParameterNumber,
    QgsProcessingParameterFile, QgsProcessingParameterFeatureSink,
    QgsProcessingFeedback, QgsExpression, QgsCoordinateReferenceSystem,
    QgsProcessingParameterBoolean
)

from qgis.PyQt.QtGui import QIcon
import os
pluginPath = os.path.dirname(__file__)

#CulvertHydrology
class Process3(QgsProcessingAlgorithm):
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    KEEP_INTERMEDIATE = 'KEEP_INTERMEDIATE'
    
    
    def initAlgorithm(self, config = None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
            'culvert_points',
            'Culvert Points',
            types = [QgsProcessing.TypeVectorPoint], 
            defaultValue = None
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
            'rainfall_point_depth',
            'Rainfall Point Depth',
            defaultValue = None
            )
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
            'rainfall_conversion_factor',
            'Rainfall Conversion Factor',
            type=QgsProcessingParameterNumber.Integer,
            defaultValue = 1000
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
            'd8_pointer',
            'D8 Pointer',
            defaultValue = None
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
            'double_breached_dem',
            'Double Breached DEM',
            defaultValue = None
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
            'cn_raster',
            'CN Raster',
            defaultValue = None
            )
        )
        
        '''
        self.addParameter(
            QgsProcessingParameterFile(
            self.OUTPUT_FOLDER,
            'Output Folder',
            behavior = QgsProcessingParameterFile.Folder,
            fileFilter = 'All files (*.*)',
            defaultValue = None
            )
        )
        '''

        self.addParameter(
            QgsProcessingParameterFeatureSink(
            'ResultCulvertBasins',
            'Result Culvert Basins',
            type=QgsProcessing.TypeVectorAnyGeometry,
            createByDefault = True,
            supportsAppend = True, 
            defaultValue = None
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
            'ResultCulvertLFP',
            'Result Culvert LFP',
            type=QgsProcessing.TypeVectorAnyGeometry,
            createByDefault = True,
            supportsAppend = True, 
            defaultValue = None
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
            'ResultCulvertPoints',
            'Result Culvert Points',
            type=QgsProcessing.TypeVectorAnyGeometry,
            createByDefault = True,
            supportsAppend = True, 
            defaultValue = None
            )
        )

        '''
        self.addParameter(
            QgsProcessingParameterBoolean(
            self.KEEP_INTERMEDIATE,
            'Keep Intermediate Basin Files?',
            defaultValue = False
            )
        )
        '''

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child
        #algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(14, model_feedback)
        results = {}
        outputs = {}
        
        keep_inter=self.parameterAsBoolean(parameters,self.KEEP_INTERMEDIATE, context)
        # Create directories
        if keep_inter is False:
            out_path = tempfile.mkdtemp()
        else:
                out_path = PureWindowsPath(
                self.parameterAsFile(
                parameters, self.OUTPUT_FOLDER, context
                )
            )
            
        
        basin_path=PureWindowsPath(out_path, "basins")
        lfp_path=PureWindowsPath(out_path, "lfp")
        
        # Check if directories already exist
        if os.path.exists(basin_path) is False:
            os.makedirs(basin_path)
            os.makedirs(lfp_path)
        else:
            alg_params = {
                'CONDITION': '',
                'MESSAGE': 'clean output folder'
            }
            outputs['RaiseException'] = processing.run(
                                                    'native:raiseexception',
                                                    alg_params,
                                                    context=context,
                                                    feedback=feedback,
                                                    is_child_algorithm=True
                                        )
                                        
        #path strings for use in script        
        basin_path_str=str(basin_path)
        out_path_str=str(out_path)
        lfp_path_str=str(lfp_path)

        # Deliniate Culvert Basins
        alg_params = {
            'd8_pntr': parameters['d8_pointer'],
            'esri_pntr': False,
            'output': basin_path_str + '/basins.tif',
            'pour_pts': parameters['culvert_points'],
        }
        
        outputs['Unnestbasins'] = (
            processing.run(
                'wbt:UnnestBasins',
                alg_params, 
                context=context, 
                feedback=feedback, 
                is_child_algorithm = True
            )
        )

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Convert Raster Basins to Vector
        alg_params = {
            'INPUT_FOLDER': basin_path_str,
            'OUTPUT_FOLDER': basin_path_str
        }
        
        outputs['Polygonize Folder'] = (
            processing.run(
                'MoACAW:polygonize_folder', 
                alg_params, 
                context = context,
                feedback = feedback, 
                is_child_algorithm = True
                )
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Merge Vector Basins into one file
        mvf_input = glob.glob(os.path.join(basin_path, "*.shp"))
        alg_params = {
            'CRS': None,
            'LAYERS':mvf_input,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['MergeVectorLayers'] = (
            processing.run(
                'native:mergevectorlayers',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )
        )

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        '''
        # Warp (reproject)
        alg_params = {
            'DATA_TYPE': 0,  # Use Input Layer Data Type
            'EXTRA': '',
            'INPUT': parameters['rainfall_point_depth'],
            'MULTITHREADING': False,
            'NODATA': None,
            'OPTIONS': '',
            'RESAMPLING': 0,  # Nearest Neighbour
            'SOURCE_CRS': QgsExpression(' layerCRS(@rainfall_point_depth)').evaluate(),
            'TARGET_CRS': QgsExpression(' layerCRS(@culvert_points)').evaluate(),
            'TARGET_EXTENT': None,
            'TARGET_EXTENT_CRS': None,
            'TARGET_RESOLUTION': None,
            'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT

        }
        outputs['WarpReproject'] = processing.run(
                                        'gdal:warpreproject', 
                                        alg_params, 
                                        context=context, 
                                        feedback=feedback, 
                                        is_child_algorithm=True
                                        )

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}
        '''

        # Get culvert design rainfall depth from rainfall raster
        alg_params = {
            'INPUT_RASTER': parameters['rainfall_point_depth'],
            'INPUT_VECTOR': parameters['culvert_points'],
            'RASTER_BAND':  1,
            'RAINFALL_CONVERSION': parameters['rainfall_conversion_factor'],
            'NEW_FIELD_NAME': 'prec_depth',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['RainfallDepth'] = (
            processing.run(
                'MoACAW:samplerastervalues',
                alg_params,
                context = context,
                feedback = feedback,
                is_child_algorithm = True
                )
        )
        
        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Get Culvert Basin Weighted CN
        alg_params = {
            'COLUMN_PREFIX': 'CN_',
            'INPUT': outputs['MergeVectorLayers']['OUTPUT'], #out_path_str+'/basins.shp',
            'INPUT_RASTER': parameters['cn_raster'],
            'RASTER_BAND': 1,
            'STATISTICS': [2],  # Mean
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['WeightedCn'] = (
            processing.run(
                'native:zonalstatisticsfb',
                alg_params,
                context = context,
                feedback = feedback,
                is_child_algorithm = True
            )
        )
        
        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}
            
        # Convert Basins OID to same datatype as culverts
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME':'OID1',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA':  'OID',
            'INPUT': outputs['WeightedCn']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['Oid1'] = (
            processing.run(
                'native:fieldcalculator',
                alg_params, context=context,
                feedback = feedback,
                is_child_algorithm = True
                )
            )

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}
            
        # Calculate culvert basin area in project units(should be acres)
        alg_params = {
            'FIELD_LENGTH': 9,
            'FIELD_NAME': 'area_ac',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 1,  # Integer (32 bit)
            'FORMULA': '$area',
            'INPUT': outputs['Oid1']['OUTPUT'],
            'OUTPUT':parameters['ResultCulvertBasins'] #out_path_str+'/basins.shp'
        }
        
        outputs['BasinArea'] = (
            processing.run(
                'native:fieldcalculator',
                alg_params,
                context = context,
                feedback = feedback,
                is_child_algorithm = True
            )
        )

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Join culvert basin attributes to culvert points
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'OID',
            'FIELDS_TO_COPY': [''],
            'FIELD_2': 'OID',
            'INPUT': outputs['RainfallDepth']['OUTPUT'],
            'INPUT_2':outputs['BasinArea']['OUTPUT'], #out_path_str+'/basins.shp',
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': 'b_',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['JoinBasinAttributes'] = (
            processing.run(
                'native:joinattributestable',
                alg_params, context = context,
                feedback=feedback,
                is_child_algorithm = True
            )
        )

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Calculate Longest Flow Paths (LFP)
        alg_params = {
            'DOUBLE_BREACHED_DEM': parameters['double_breached_dem'],
            'INPUT_FOLDER': basin_path_str,
            'OUTPUT_FOLDER': lfp_path_str
        }
        
        outputs['WbtLongestflowpathFromFolder'] = (
            processing.run(
                'MoACAW:wbt_folder_lfp',
                alg_params, context = context,
                feedback=feedback,
                is_child_algorithm = True
            )
        )

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Merge LFP Vectors
        mlfp_input = glob.glob(os.path.join(lfp_path, "*.shp"))
        alg_params = {
            'CRS': None,
            'LAYERS':mlfp_input,
            'OUTPUT':parameters['ResultCulvertLFP'] #out_path_str+'/lfp.shp'
        }
        
        outputs['MergeLfpFolder'] = (
            processing.run(
                'native:mergevectorlayers',
                alg_params,
                context = context,
                feedback = feedback,
                is_child_algorithm = True
            )
        )



        #Add Algorithm Here to get LFP in feet
        #     
        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Join LFP Attributes
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'b_OID1',
            'FIELDS_TO_COPY': [''],
            'FIELD_2': 'BASIN',
            'INPUT': outputs['JoinBasinAttributes']['OUTPUT'],
            'INPUT_2': outputs['MergeLfpFolder']['OUTPUT'], #out_path_str+'/lfp.shp',
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': 'l_',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['JoinLfpAttributes'] = (
            processing.run(
                'native:joinattributestable',
                alg_params,
                context = context,
                feedback = feedback,
                is_child_algorithm = True
            )
        )

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Calculate Time of Concentration
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'Tc',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': "Tc(l_LENGTH,b_CN_mean,l_AVG_SLOPE, 'm')",
            'INPUT': outputs['JoinLfpAttributes']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        
        outputs['Tc'] = (
            processing.run(
                'native:fieldcalculator',
                alg_params,
                context = context,
                feedback = feedback,
                is_child_algorithm = True
            )
        )

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # Calculate Design Flow Rate
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'Qp',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': 'Qp(0.2,b_CN_mean,prec_depth,Tc,b_area_ac)',
            'INPUT': outputs['Tc']['OUTPUT'],
            'OUTPUT': parameters['ResultCulvertPoints']
        }
        outputs['Qp'] = (
            processing.run(
                'native:fieldcalculator',
                alg_params,
                context = context,
                feedback = feedback,
                is_child_algorithm = True
            )
        )
        
        results['ResultCulvertPoints'] = outputs['Qp']['OUTPUT']
        
        #Delete intermediate
        """
        if self.KEEP_INTERMEDIATE is False:
            shutil.rmtree('G:\Shared drives\WRS Projects\2023\2023014 - UMKC - MoDOT - Asset Charcterization Using Automated Methods\Mapping\Test\ModelTestFull\Process 3\full\basins')
            shutil.rmtree(lfp_path_str)
        """
        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}
            
        return results
        
    def name(self):
        return 'Process 3: Culvert Hydrology Full'

    def displayName(self):
        return 'Process 3: Culvert Hydrology Full'

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
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">This proccessing algorithm calculates the hydrologic parameters for the culverts identified in Process 2.</p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-style:italic;">Be sure to save culvert layer after this process.  </span></p>
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">   </p></body></html></p>
<h2>Input parameters</h2>
<h3>Culvert Points</h3>
<p>Output point layer from Process 2: Culvert Locations and Attributes</p>
<h3>Rainfall Point Depth</h3>
<p>Rainfall point depth raster CRS should match CRS of culvert points layer.</p>
<h3>Rainfall Conversion Factor</h3>
<p>Factor to convert raster values to rainfall depth in inches 1000 if Atlas 14 raster.</p>
<h3>D8 Pointer</h3>
<p>D8 pointer raster from Process 1: Hydroconditioning and Stream Creation.</p>
<h3>Double Breached DEM</h3>
<p>Output Hydroconditioned (Double Breached) DEM from Process 1: Hydroconditioning and Stream Creation.</p>
<h3>CN Raster</h3>
<p>Curve Number Raster</p> 
<h2>Outputs</h2>
<h3>Result Culvert Basin</h3>
<p>Culvert Basin deliniation vector polygons.</p>
<h3>Result Culvert LFP</h3>
<p>Culvert Basin Longest Flow Path vector lines</p>
<h3>Result Culvert Points</h3>
<p>Culvert Points vector with computed hydrology attributes. This is the primary output of this processing algorithm.</p>
<br><p align="right">Algorithm author: Aaron Sprague, Water Resources Solutions</p><p align="right">Help author: Aaron Sprague, Water Resources Solutions</p></body></html>"""

    def createInstance(self):
        return Process3()
