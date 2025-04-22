from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterFile, QgsProcessingParameterFolderDestination
import processing
import glob
import os

class PolygonizeFolder(QgsProcessingAlgorithm):
    INPUT_FOLDER = 'INPUT_FOLDER'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'

    def initAlgorithm(self, config=None):
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
        inpath = self.parameterAsFile(parameters, self.INPUT_FOLDER, context)
        outpath = self.parameterAsFile(parameters,self.OUTPUT_FOLDER, context)

        input_files = glob.glob(os.path.join(inpath, "*.tif"))

        for input_file in input_files:
            output_file = os.path.join(outpath, os.path.basename(input_file) + ".shp")

            processing.run("gdal:polygonize", {
                'INPUT': input_file,
                'BAND': 1,
                'FIELD': 'OID',
                'EIGHT_CONNECTEDNESS': True,
                'EXTRA': '',
                'OUTPUT': output_file
            }, context=context, feedback=feedback)

        return {}

    def name(self):
        return 'polygonize_folder'

    def displayName(self):
        return 'Polygonize folder'

    def group(self):
        return 'Sub Algorithms'

    def groupId(self):
        return 'subalgs'

    def createInstance(self):
        return PolygonizeFolder()