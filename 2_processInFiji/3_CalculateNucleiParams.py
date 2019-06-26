#@int(label="A nucleus is everything  BIGGER than (um^2)") areaMin
#@int(label="A nucleus is everything SMALLER than (um^2)") areaMax
#@boolean (label="Filter according to area") filterArea
#
#@float(label="A nucleus has a circularity  BIGGER than (1 represents perfect circularity)") circularityMin
#@float(label="A nucleus has a circularity SMALLER than (1 represents perfect circularity)") circularityMax
#@boolean (label="Filter according to circularity") filterCirc
#
#-------disabled-------@boolean (label="Input image shows nuclei (checked) or membranes (unchecked)") inputImageShowsNuclei
#-------disabled-------@boolean (label="Nuclei detection: After 1st run, close left-out nuclei and re-run detection", value=False) postprocessNucleiImageFlag
#-------disabled-------@boolean (label="Membrane thinning: Input image should be up-scaled and membranes thinned", value=False) preprocessMembraneImageFlag
inputImageShowsNuclei = False
postprocessNucleiImageFlag = False
preprocessMembraneImageFlag = True

#
#@boolean (label="Polygon boundary straightening:", value=False) polyAsLargeSegments
#-------disabled-------@boolean (label="Polygon boundary smoothing: should do", value=False) polySmoothDo
#-------disabled-------@int     (label="Polygon boundary smoothing: smooth span in half-pixel units", value=10) polySmoothSpan
#-------disabled-------@float   (label="Polygon boundary smoothing: smooth sigma in half-pixel units", value=4) polySmoothSigma
polySmoothDo = False
polySmoothSpan = 10
polySmoothSigma = 4
#
#@File (style="directory", label="Folder with maps:") mapFolder
#@String (label="\"cylinder1\" vs. \"cylinder2\":", value="cylinder1") mapCylinder
class SimpleFile:
	def __init__(self,path):
		self.path = path
	def getAbsolutePath(self):
		return self.path

aMapFile = SimpleFile(mapFolder.getAbsolutePath()+"/"+mapCylinder+"_area.txt")
xMapFile = SimpleFile(mapFolder.getAbsolutePath()+"/"+mapCylinder+"coords_X.txt")
yMapFile = SimpleFile(mapFolder.getAbsolutePath()+"/"+mapCylinder+"coords_Y.txt")
zMapFile = SimpleFile(mapFolder.getAbsolutePath()+"/"+mapCylinder+"coords_Z.txt")

#
#@boolean (label="Show sheet with analysis data", value=True) showRawData
#@boolean (label="Show image with areas") showAreaImage
#@boolean (label="Show image with circularities") showCircImage
#@boolean (label="Show image with shape factors") showShapeFactorImage
#@boolean (label="Show image with neighbor counts") showNeigImage

# This script should be used to find suitable parameters for CountBigNucleiCorrected.py
# You'll see nuclei of various colors:
# green - fit both conditions      (area good, circularity good)
# white - does not fit circularity (area good, circularity bad)
# blue - does not fit area         (area bad,  circularity good)
# red - fails both conditions      (area bad,  circularity bad)
colors = [0x00FF00, 0xFFFFFF, 0x0000FF, 0xFF0000]

# Usage:
#	- Run Fiji
# 	- Make sure that the update site SCF-MPI-CBG is activated
#	- Open one representative image of your data
#	- Run this script
# 	- If you are not confident with the output, repeat with other parameters.

from ij import IJ
from ij import ImagePlus
from ij.process import ColorProcessor
from ij.process import FloatProcessor
from ij.measure import ResultsTable

# this section adds a folder, in which this very script is living,
# to the current search paths so that we can import our "library script"
import sys.path
import os.path
import inspect
ScriptsRoot = os.path.dirname(os.path.dirname(sys.path[0]))+os.sep+"scripts"
ThisFile    = os.path.dirname(inspect.getfile(inspect.currentframe()))
sys.path.append(ScriptsRoot+os.sep+ThisFile+os.sep+"lib")
sys.path.append(ThisFile+os.sep+"lib")

# import our "library scripts"
from importsFromImSAnE import *
from chooseNuclei import *
from properMeasurements import *

# import the same Nucleus class to make sure the very same calculations are used
from Nucleus import Nucleus

# VLADO PROPER CIRC DEBUG
# VLADO PIXEL CIRC DEBUG
import math


def main():
	print("wait until \"Done.\" (or error) appears...")
	originalImageName = IJ.getImage().getTitle()

	# FIX: we now assume membrane image to come; in this case, however, the script
	# assumes that membranes pixels store value of 2.0... but the current data use
	# value of 1.0 and so we have to fix it.....
	removeMeImg = IJ.getImage().duplicate()
	removeMeImg.show()
	IJ.run("Add...", "value=1");

	# reads the area_per_pixel information, already in squared microns
	realSizes = readRealSizes(aMapFile.getAbsolutePath())

	# read the 'real Coordinates', that take into account the different pixel sizes
	realCoordinates = readRealCoords(xMapFile.getAbsolutePath(),yMapFile.getAbsolutePath(),zMapFile.getAbsolutePath())

	backgroundPixelValue = 1 # in case of cell nuclei
	if (not inputImageShowsNuclei):
		backgroundPixelValue = 2 # in case of cell membranes
		if preprocessMembraneImageFlag == True:
			print("initial membrane preprocessing...")
			preprocessMembraneImage(realSizes)

	imp = IJ.getImage()

	# test that sizes of realSizes and imp matches
	checkSize2DarrayVsImgPlus(realSizes, imp)
	checkSize2DarrayVsImgPlus(realCoordinates, imp)

	print("extracting individual nuclei and their parameters...")
	# obtain list of all valid nuclei
	nuclei = chooseNucleiNew(imp,backgroundPixelValue,realSizes,realCoordinates, filterArea,areaMin,areaMax, filterCirc,circularityMin,circularityMax, postprocessNucleiImageFlag)
	# add list of all INvalid nuclei (since only invalid are left in the input image)
	#nuclei += findComponents(imp,255,realSizes,realCoordinates,"n_")

	# ------- analysis starts here -------
	if len(nuclei) == 0:
		print("No components found, quiting...")
		return

	circularitySum = 0
	shapeFactorSum = 0
	sizeSum = 0

	i = IJ.getImage().getProcessor().getPixels()
	w = IJ.getImage().getWidth()

	if polyAsLargeSegments == True:
		print("redesigning nuclei boundaries - fitting line segments...")
	if polySmoothDo == True:
		print("redesigning nuclei boundaries - smoothing it out...")
	if polyAsLargeSegments == True or polySmoothDo == True:
		print("recalculating nuclei parameters since boundaries have changed...")
	if (not inputImageShowsNuclei):
		print("calculating number of neighbors per cell...")

	drasticAreaChange = 0
	for nucl in nuclei:
		# should straightening happen?
		if polyAsLargeSegments == True:
			nucl.reshapeNucleusWithStraightenedBoundary(i,w)

		if polySmoothDo == True:
			nucl.smoothPolygonBoundary(polySmoothSpan,polySmoothSigma)

		if polyAsLargeSegments == True or polySmoothDo == True:
			# update everything that depends on a corrected area and perimeter length
			nucl.EdgeLength = properLength(nucl.Coords,realCoordinates)
			origArea = nucl.Area
			nucl.getBoundaryInducedArea(realSizes)
			nucl.updateCircularityAndSA()

			if nucl.Area/origArea < 0.90 or nucl.Area/origArea > 1.10:
				drasticAreaChange = drasticAreaChange+1

		circularitySum += nucl.Circularity
		shapeFactorSum += nucl.ShapeFactor
		sizeSum += nucl.Area
		if (not inputImageShowsNuclei):
			nucl.setNeighborsList(i,w)


	if polyAsLargeSegments == True and drasticAreaChange > 0:
		print("WARNING: "+str(drasticAreaChange)+"/"+str(len(nuclei))
		     +" cells have real area change larger than 10%.")

	print("Average Circularity: "+str(circularitySum/len(nuclei)))
	print("Average ShapeFactor: "+str(shapeFactorSum/len(nuclei)))
	print("Average Area: "+str(sizeSum/len(nuclei))+" square microns")

	if inputImageShowsNuclei:
		print("No. of neighborhood was not counted, works only with membrane images.")


	if polyAsLargeSegments == True or polySmoothDo == True:
		for nucl in nuclei:
			nucl.DrawValue = nucl.Label
		drawChosenNucleiValue(originalImageName+": NEW SHAPES", imp.getWidth(),imp.getHeight(), nuclei)

	if showCircImage:
		for nucl in nuclei:
			nucl.DrawValue = nucl.Circularity
		drawChosenNucleiValue(originalImageName+": Real circularities", imp.getWidth(),imp.getHeight(), nuclei)

	if showShapeFactorImage:
		for nucl in nuclei:
			nucl.DrawValue = nucl.ShapeFactor
		drawChosenNucleiValue(originalImageName+": Real shape factors", imp.getWidth(),imp.getHeight(), nuclei)

	if showAreaImage:
		for nucl in nuclei:
			nucl.DrawValue = nucl.Area;
		drawChosenNucleiValue(originalImageName+": Real areas", imp.getWidth(),imp.getHeight(), nuclei)

	if showNeigImage:
		for nucl in nuclei:
			nucl.DrawValue = len(nucl.NeighIDs);
		drawChosenNucleiValue(originalImageName+": Neighborhood counts", imp.getWidth(),imp.getHeight(), nuclei)


	if (showRawData):
		print("Populating table...")

		# create an output table with three columns: label, circularity, area, size, positionX, positionY
		rt = ResultsTable()

		# also create two hidden 1D images (arrays essentially) and ask to display their histograms later
		imgArea = []
		imgCirc = []
		imgNeig = []

		for nucl in nuclei:
			rt.incrementCounter()
			rt.addValue("label"                            ,nucl.Color)
			rt.addValue("circularity (higher more roundish)",nucl.Circularity)
			rt.addValue("circularity (pixel-based)"        ,nucl.DrawValue) # VLADO PIXEL CIRC DEBUG
			rt.addValue("shape factor"                     ,nucl.ShapeFactor)
			rt.addValue("area (um^2)"                      ,nucl.Area)
			rt.addValue("area (px)"                        ,nucl.Size)
			rt.addValue("perimeter (px)"                   ,nucl.EdgeSize)
			rt.addValue("perimeter (um)"                   ,nucl.EdgeLength)
			rt.addValue("neigbor count"                    ,len(nucl.NeighIDs))
			rt.addValue("centreX (px)"                     ,nucl.CentreX)
			rt.addValue("centreY (px)"                     ,nucl.CentreY)

			imgArea.append(nucl.Area)
			imgCirc.append(nucl.Circularity)
			imgNeig.append(len(nucl.NeighIDs))

		# show the image
		rt.showRowNumbers(False)
		rt.show("Nuclei properties")

		# show the histograms
		#imgArea = ImagePlus("areas of nuclei",FloatProcessor(len(nuclei),1,imgArea))
		imgArea = ImagePlus("nuclei_areas",FloatProcessor(len(nuclei),1,imgArea))
		IJ.run(imgArea, "Histogram", str( (imgArea.getDisplayRangeMax() - imgArea.getDisplayRangeMin()) / 10 ))

		#imgCirc = ImagePlus("circularities of nuclei",FloatProcessor(len(nuclei),1,imgCirc))
		imgCirc = ImagePlus("nuclei_circularities",FloatProcessor(len(nuclei),1,imgCirc))
		IJ.run(imgCirc, "Histogram", "20")

		imgNeig = ImagePlus("nuclei_neigborCount",FloatProcessor(len(nuclei),1,imgNeig))
		IJ.run(imgNeig, "Histogram", "10")

		# debug: what perimeter points are considered
		# writeCoordsToFile(nuclei[0].EdgePixels,"/Users/ulman/DATA/fp_coords_0.txt")
		# writeCoordsToFile(nuclei[1].EdgePixels,"/Users/ulman/DATA/fp_coords_1.txt")

	removeMeImg.changes = False
	removeMeImg.close()


def startSession(folder,tpFile):
	IJ.open(folder+"/"+tpFile)
	IJ.selectWindow(tpFile);

def closeSession(tpFile):
	IJ.selectWindow(tpFile+": NEW SHAPES");
	IJ.getImage().close();

	IJ.selectWindow("1_labelled_image");
	IJ.getImage().changes = False
	IJ.getImage().close();

	IJ.selectWindow("upScaledOrigImg.tif");
	IJ.getImage().changes = False
	IJ.getImage().close();

	IJ.selectWindow(tpFile);
	IJ.getImage().close();


def doOneTP(tpFile):
	print(tpFile+" Starting.............")
	startSession("/Users/ulman/p_Akanksha/curated/curated2/",tpFile)
	main()
	print(tpFile+" Done.")
	closeSession(tpFile)


# HAVE UNCOMMENTED EITHER THESE TWO LINES, OR ALL THE LINES UNDERNEATH THESE TWO
# single, currently opened image mode
main()
print("Done.")


# batch processing mode
#doOneTP("10.tif")
#doOneTP("310.tif")
#doOneTP("340.tif")
#doOneTP("425.tif")
#doOneTP("555.tif")