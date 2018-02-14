from ij import IJ
from ij import ImagePlus
from ij.process import ColorProcessor

from Nucleus import Nucleus

def findComponents(imp,bgPixelValue,realSizes,prefix):
	# obtain "handle" to the pixels
	ip = imp.getProcessor()

	# fix pixel values
	for x in range(imp.getWidth()):
		for y in range(imp.getHeight()):
			if (ip.getPixel(x, y) == bgPixelValue or ip.getPixel(x, y) == 0):
				ip.set(x,y,0)
			else:
				ip.set(x,y,255)

	#Detect Nuclei
	IJ.run(imp, "HMaxima local maximum detection (2D, 3D)", "minimum=1 threshold=0")
	labelMap = IJ.getImage()
	LPP = labelMap.getProcessor()

	#Detect all pixels belonging to one Color
	# (builds a list of lists of pixel coords -- pixelPerColor[label][0] = first coordinate
	pixelPerColor = {}
	for x in range(labelMap.width):
		for y in range(labelMap.height):
			MyColor = int(LPP.getf(x,y))
			if MyColor != 0:
				if MyColor in pixelPerColor:
					pixelPerColor[MyColor].append([x,y])
				else:
					#print "detected (1st run): "+str(MyColor)
					pixelPerColor[MyColor] = [[x,y]]
	labelMap.close()

	# a list of detected objects (connected components)
	components = []
	for Color in pixelPerColor:
		components.append(Nucleus(prefix+str(Color),pixelPerColor[Color],ip,realSizes))

	return components


def chooseNuclei(imp,bgPixelValue,realSizes, filterArea,areaMin,areaMax, filterCirc,circularityMin,circularityMax):
	# obtain list of all components that are found initially in the image
	components = findComponents(imp,bgPixelValue,realSizes,"1_")
	# obtain "handle" to the pixels
	ip = imp.getProcessor()

	# output list of nuclei
	nuclei = []
	areThereSomeObjectsLeft = False

	# initiate at first only with nicely passing nuclei
	# and remove pixels from the passing components from the initial/segmentation image
	# (so that pixels from non-passing components will be the only left there)
	for comp in components:
		if comp.doesQualify(filterArea,areaMin,areaMax, filterCirc,circularityMin,circularityMax) == True:
			#enlist
			nuclei.append(comp)
			#erase from input
			for pix in comp.Pixels:
				ip.setf(pix[0],pix[1], 0)
		else:
			areThereSomeObjectsLeft = True

	if areThereSomeObjectsLeft:
		# close (and slightly dilate) the original image
		IJ.run("Dilate (3D)", "1")
		IJ.run("Dilate (3D)", "1")
		IJ.run("Dilate (3D)", "1")
		IJ.run("Dilate (3D)", "1")
		IJ.run("Dilate (3D)", "1")
		IJ.run("Erode (3D)", "1")
		IJ.run("Erode (3D)", "1")
		IJ.run("Erode (3D)", "1")

		# find again the new components
		components = findComponents(imp,bgPixelValue,realSizes,"2_")

		# and filter again this new components
		for comp in components:
			if comp.doesQualify(filterArea,areaMin,areaMax, filterCirc,circularityMin,circularityMax) == True:
				#enlist
				nuclei.append(comp)

	return nuclei


def drawChosenNuclei(width,height, nuclei):
	# initial colour palette
	colors = [0x00FF00, 0xFFFFFF, 0x0000FF, 0xFF0000]
	colNo = len(colors)

	#initiate output pixel buffer
	OutputPixels = [[0 for y in range(width)] for x in range(height)]

	nuclCnt = 0
	for nucl in nuclei:
		nuclCnt = nuclCnt + 1
		color = colors[nuclCnt % colNo]
		for pix in nucl.Pixels:
			OutputPixels[pix[1]][pix[0]] = color

	OutputPixelsNew = reduce(lambda x,y :x+y ,OutputPixels)
	cp = ColorProcessor(width,height, OutputPixelsNew)
	OutputImg = ImagePlus("Viable Nuclei", cp)
	OutputImg.show()