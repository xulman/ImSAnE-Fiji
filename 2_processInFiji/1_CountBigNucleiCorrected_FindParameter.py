#@int(label="A nucleus is everything  BIGGER than (um^2)") areaMin
#@int(label="A nucleus is everything SMALLER than (um^2)") areaMax
#@boolean (label="Filter according to area") filterArea
#
#@float(label="A nucleus has a circularity  BIGGER than (lower value means higher circularity)") circularityMin
#@float(label="A nucleus has a circularity SMALLER than (lower value means higher circularity)") circularityMax
#@boolean (label="Filter according to circularity") filterCirc
#
#@boolean (label="Input image shows nuclei (checked) or membranes (unchecked) ") inputImageShowsNuclei
#@File (label="Pixel areas map:") aMapFile
#
#@boolean (label="Show sheet with analysis data") showRawData

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
sys.path.append(os.path.dirname(inspect.getfile(inspect.currentframe()))+"/lib")

# import our "library scripts"
from importsFromImSAnE import *
from chooseNuclei import *

# import the same Nucleus class to make sure the very same calculations are used
from Nucleus import Nucleus


# reads the area_per_pixel information, already in squared microns
realSizes = readRealSizes(aMapFile.getAbsolutePath());

imp = IJ.getImage()


def main():
	# test that sizes of realSizes and imp matches
	checkSize2DarrayVsImgPlus(realSizes, imp);

	backgroundPixelValue = 1 # in case of cell nuclei
	if (not inputImageShowsNuclei):
		backgroundPixelValue = 2 # in case of cell membranes

	# obtain list of all nuclei
	nuclei = findComponents(imp,backgroundPixelValue,realSizes,"")
	#nuclei = chooseNuclei(imp,backgroundPixelValue,realSizes, filterArea,areaMin,areaMax, filterCirc,circularityMin,circularityMax)

	# ------- analysis starts here -------
	circularitySum = 0
	sizesum = 0

	for nucl in nuclei:
		circularitySum += nucl.circularity
		sizesum += nucl.area

	print("Average Circularity: "+str(circularitySum/len(nuclei)))
	print("Average Area: "+str(sizesum/len(nuclei))+" square microns")

	print("Creating output image ...")
	OutputPixels = [[0 for y in range(imp.width)] for x in range(imp.height)]
	# green - fit both conditions
	# blue - does not fit area
	# white - does not fit circularity
	# red - fails both conditions
	#
	for nucl in nuclei:
		errCnt = 0
		if (filterCirc == True and (nucl.circularity < circularityMin or nucl.circularity > circularityMax)):
			errCnt += 1
		if (filterArea == True and (nucl.area < areaMin or nucl.area > areaMax)):
			errCnt += 2

		for pix in nucl.Pixels:
			OutputPixels[pix[1]][pix[0]] = colors[errCnt]

	OutputPixelsNew = reduce(lambda x,y :x+y ,OutputPixels)
	cp = ColorProcessor(imp.getWidth(),imp.getHeight(), OutputPixelsNew)
	OutputImg = ImagePlus("OutputImg", cp)
	OutputImg.show()


	if (showRawData):
		print("Populating table...")

		# create an output table with three columns: label, circularity, area, size, positionX, positionY
		rt = ResultsTable()

		# also create two hidden 1D images (arrays essentially) and ask to display their histograms later
		imgArea = []
		imgCirc = []

		for nucl in nuclei:
			rt.incrementCounter()
			rt.addValue("label"                            ,nucl.Color)
			rt.addValue("circularity (lower more roundish)",nucl.circularity)
			rt.addValue("area (um^2)"                      ,nucl.area)
			rt.addValue("area (px)"                        ,nucl.size)
			rt.addValue("centreX (px)"                     ,nucl.centreX)
			rt.addValue("centreY (px)"                     ,nucl.centreY)

			imgArea.append(nucl.area)
			imgCirc.append(nucl.circularity)

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


	print("Done.")


main()
