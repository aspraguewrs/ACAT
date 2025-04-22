from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingParameterFolderDestination
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsExpression
import processing
import glob
import os

class WbtLfpFolder(QgsProcessingAlgorithm):
    INPUT_DEM = 'DOUBLE_BREACHED_DEM'
    INPUT_FOLDER = 'INPUT_FOLDER'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterRasterLayer(
            self.INPUT_DEM,
            'Double Breached DEM',
            defaultValue=None
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                'Input folder',
                behavior=QgsProcessingParameterFile.Folder
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFile(
                self.OUTPUT_FOLDER,
                'Output folder',
                behavior=QgsProcessingParameterFile.Folder
            )
        )
        

    def processAlgorithm(self, parameters, context, feedback):
        indem = self.parameterAsFile(parameters, self.INPUT_DEM, context) 
        inpath = self.parameterAsFile(parameters, self.INPUT_FOLDER, context)
        outpath = self.parameterAsFile(parameters,self.OUTPUT_FOLDER, context)

        input_files = glob.glob(os.path.join(inpath, "*.tif"))

        for input_file in input_files:
            output_file = os.path.join(outpath, os.path.basename(input_file) + "-lfp.shp")


            processing.run("wbt:LongestFlowpath", {
                'dem': indem,
                'basins': input_file,
                'output': output_file
                }, context=context, feedback=feedback)
        return {}

    def name(self):
        return 'wbt_folder_lfp'

    def displayName(self):
        return 'WBT LongestFlowPath from Folder'

    def group(self):
        return 'Sub Algorithms'

    def groupId(self):
        return 'subalgs'

    def createInstance(self):
        return WbtLfpFolder()            