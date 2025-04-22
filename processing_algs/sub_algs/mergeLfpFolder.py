from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingParameterFolderDestination
import processing
import glob
import os
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingDestinationParameter

class MergeLfpFolder(QgsProcessingAlgorithm):
    INPUT_FOLDER = 'INPUT_FOLDER'
    OUTPUT_FILE = 'OUTPUT_FILE'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                'Input folder',
                behavior=QgsProcessingParameterFile.Folder
            )
        )

        
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT_FILE, 'Output FlowPaths',
                type=QgsProcessing.TypeVectorPolygon,
                createByDefault=True,
                defaultValue=None
            )
        )
        
    def processAlgorithm(self, parameters, context, feedback):
        inpath = self.parameterAsFile(parameters, self.INPUT_FOLDER, context)
        outfile = self.parameterAsOutputLayer(parameters, self.OUTPUT_FILE, context)

        input_files = glob.glob(os.path.join(inpath, "*-lfp.shp"))
        #output_file = os.path.join(outpath, "basinsss.shp")

        processing.run("native:mergevectorlayers", {
            'LAYERS': input_files,
            'CRS': None,
            'OUTPUT': outfile
        }, context=context, feedback=feedback)

        return {}

    def name(self):
        return 'mergelfpfolder'

    def displayName(self):
        return 'Merge LFP Folder'

    def group(self):
        return 'Sub Algorithms'

    def groupId(self):
        return 'subalgs'

    def createInstance(self):
        return MergeLfpFolder()