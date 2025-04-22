from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorLayer, QgsProcessingParameterField,
                       QgsProcessingParameterNumber, QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSink, QgsFeatureSink, QgsFeature, QgsPointXY,QgsField,QgsRaster)
from qgis import processing

class SampleRasterValues(QgsProcessingAlgorithm):
    INPUT_RASTER = 'INPUT_RASTER'
    INPUT_VECTOR = 'INPUT_VECTOR'
    RASTER_BAND = 'RASTER_BAND'
    RAINFALL_CONVERSION='RAINFALL_CONVERSION'
    NEW_FIELD_NAME = 'NEW_FIELD_NAME'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                self.tr('Input Raster Layer')
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_VECTOR,
                self.tr('Input Vector Layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.RASTER_BAND,
                self.tr('Raster Band to Sample'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=1
            )
        )
        
        self.addParameter(
            QgsProcessingParameterNumber(
            self.RAINFALL_CONVERSION,
            self.tr('Rainfall Conversion Factor'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=1000
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.NEW_FIELD_NAME,
                self.tr('New Field Name')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output Layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        vector_layer = self.parameterAsVectorLayer(parameters, self.INPUT_VECTOR, context)
        raster_band = self.parameterAsInt(parameters, self.RASTER_BAND, context)
        rainfall_conversion=self.parameterAsInt(parameters,self.RAINFALL_CONVERSION, context)
        new_field_name = self.parameterAsString(parameters, self.NEW_FIELD_NAME, context)

        if not raster_layer or not vector_layer:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT_RASTER if not raster_layer else self.INPUT_VECTOR))

        vector_layer.dataProvider().addAttributes([QgsField(new_field_name, QVariant.Double)])
        vector_layer.updateFields()
        
        #raster_data=raster_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results().values()

        #raster_data = raster_layer.dataProvider().block(raster_band, raster_layer.extent(), raster_layer.width(), raster_layer.height())
        new_features = []
        for feature in vector_layer.getFeatures():
            point = feature.geometry().asPoint()
            #value = raster_data.valueAt(point.x(), point.y())
            values = raster_layer.dataProvider().sample(point, raster_band)
            value=values[0]/rainfall_conversion
            new_feature = QgsFeature(feature)
            new_feature.setAttribute(new_field_name, value)
            new_features.append(new_feature)

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                                               vector_layer.fields(), vector_layer.wkbType(), vector_layer.sourceCrs())

        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        sink.addFeatures(new_features, QgsFeatureSink.FastInsert)

        return {self.OUTPUT: dest_id}

    def name(self):
        return 'samplerastervalues'

    
    def displayName(self):
        return self.tr('Sample Raster Values')

    def group(self):
        return 'Sub Algorithms'

    def groupId(self):
        return 'subalgs'
    

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
    

    def createInstance(self):
        return SampleRasterValues()
