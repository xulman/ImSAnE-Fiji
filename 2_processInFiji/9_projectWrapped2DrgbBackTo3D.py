#@ImagePlus (label="Image to back-projected:") inImp
#@File (label="X coordinate map:") xMapFile
#@File (label="Y coordinate map:") yMapFile
#@File (label="Z coordinate map:") zMapFile
#@float (label="Pixel size (microns per 1px):") pxSize
#@float (label="Downscale factor:") dsRatio

#@int   (label="Thickness of the fade-out smoothing layer (pixels):", min="0") pxFadeThickness
#@float (label="Magnitude of variations in the fade-out smoothing layer:", min="0") alternationMagInFadeThickness
#@int   (label="Thickness of the outer main (image) layer (pixels):", min="1", description="The thicker it is, the less the rendering would \"see through it\".") pxThickness
#@int   (label="Thickness of the inner extra (blocking) layer (pixels):", min="0", description="Set to 0 to avoid creating this blocking inner layer.") pxExtraThickness
#@int (label="Red value to draw with the extra layer (0-255):", description="This value is not considered if the above is set to 0. To make it practically invisible, set this to some small number.")   valRExtraThickness
#@int (label="Green value to draw with the extra layer (0-255):", description="This value is not considered if the above is set to 0. To make it practically invisible, set this to some small number.") valGExtraThickness
#@int (label="Blue value to draw with the extra layer (0-255):", description="This value is not considered if the above is set to 0. To make it practically invisible, set this to some small number.")  valBExtraThickness

# This script creates a 3D image that displays the original image before
# it got wrapped/embedded into the input inImp 2D image.
# The input image can be any scalar voxel type, does NOT work for RGB well.

from ij import IJ
import ij.ImagePlus
import ij.ImageStack
from ij.process import ColorProcessor
import math
import os
import sys
import random

# this section adds a folder, in which this very script is living,
# to the current search paths so that we can import our "library script"
import sys.path
import os.path
import inspect
ScriptsRoot = os.path.dirname(os.path.dirname(sys.path[0]))+os.sep+"scripts"
ThisFile    = os.path.dirname(inspect.getfile(inspect.currentframe()))
sys.path.append(ScriptsRoot+os.sep+ThisFile+os.sep+"lib")
sys.path.append(ThisFile+os.sep+"lib")

# import our "library script"
from importsFromImSAnE import *


# reads the 3D coordinates for every pixel, coordinates are in units of microns
realCoords = readRealCoords(xMapFile.getAbsolutePath(),yMapFile.getAbsolutePath(),zMapFile.getAbsolutePath());

# test that sizes match:
checkSize2DarrayVsImgPlus(realCoords, inImp);

# make sure the 'thicknesses values' are sensible
if pxFadeThickness < 0:
	pxFadeThickness = 0
if pxThickness < 1:
	pxThickness = 1
if pxExtraThickness < -1:
	pxExtraThickness = 0
blockingValue = Color(valRExtraThickness, valGExtraThickness, valBExtraThickness)

# own rng generator for changes in the fade-out layer
fadeRandom = random.Random()

print("calculating the 3D image size...")
# search for min&max per axis, while scaling back to pixel units (from the original micron ones)
min=[+99999999999,+99999999999,+99999999999]
max=[-99999999999,-99999999999,-99999999999]
for x in range(0,inImp.width):
	for y in range(0,inImp.height):
		coord = realCoords[x][y]
		# first, scale to pixel units
		coord[0] = coord[0] / pxSize
		coord[1] = coord[1] / pxSize
		coord[2] = coord[2] / pxSize

		# second, update coordinate bounds
		if (coord[0] < min[0]):
			min[0]=coord[0];
		if (coord[1] < min[1]):
			min[1]=coord[1];
		if (coord[2] < min[2]):
			min[2]=coord[2];
		if (coord[0] > max[0]):
			max[0]=coord[0];
		if (coord[1] > max[1]):
			max[1]=coord[1];
		if (coord[2] > max[2]):
			max[2]=coord[2];

print("detected intervals:")
print("X: "+str(min[0])+" .. "+str(max[0]))
print("Y: "+str(min[1])+" .. "+str(max[1]))
print("Z: "+str(min[2])+" .. "+str(max[2]))

# create an output image of float type (as float can store also integers)
min[0]=math.floor(min[0] /dsRatio) -pxFadeThickness-1
min[1]=math.floor(min[1] /dsRatio) -pxFadeThickness-1
min[2]=math.floor(min[2] /dsRatio) -pxFadeThickness-1

max[0]=math.ceil(max[0] /dsRatio) +pxFadeThickness+1
max[1]=math.ceil(max[1] /dsRatio) +pxFadeThickness+1
max[2]=math.ceil(max[2] /dsRatio) +pxFadeThickness+1

# calc image size and downscale for the final output image
xSize = int(max[0]-min[0]+1)
ySize = int(max[1]-min[1]+1)
zSize = int(max[2]-min[2]+1)

print("creating 3D of sizes: "+str(xSize)+" x "+str(ySize)+" x "+str(zSize))
outRGBProcessors = [ ColorProcessor(xSize,ySize) for z in range(zSize) ]
# outRGBPixels = [ outRGBProcessors[z].getPixels() for z in range(len(outRGBProcessors)) ]

# progress bar ticks...
pbTicks = range(0,inImp.width,int(inImp.width/10))
pbTicksVal = 0

# sweep through the inImp and project pixels to outImp
print("populating the 3D image...")
totalX = float(inImp.width)
inIP = inImp.getProcessor();
for x in range(0,inImp.width):
	IJ.showProgress(float(x)/totalX)
	if x in pbTicks:
		print("progress: "+str(pbTicksVal)+" %")
		pbTicksVal = pbTicksVal+10

	for y in range(0,inImp.height):
		# orig unscaled 3D coords
		coord = realCoords[x][y]

		# normalized vector towards the coordinates centre
		dz = math.sqrt(coord[0]*coord[0] + coord[1]*coord[1] + coord[2]*coord[2]) /dsRatio
		dx = -coord[0] / dz
		dy = -coord[1] / dz
		dz = -coord[2] / dz

		# the fade-out outer main (image) layer -- to fight "moire-like" effect
		#
		# prefetch the value to be inserted
		origValue = inIP.getColor(x,y)
		#
		mult = fadeRandom.uniform(1.0-alternationMagInFadeThickness,1.0+alternationMagInFadeThickness)
		decreaserR = mult * origValue.getRed()   / (pxFadeThickness+1)
		decreaserG = mult * origValue.getGreen() / (pxFadeThickness+1)
		decreaserB = mult * origValue.getBlue()  / (pxFadeThickness+1)
		if decreaserR*pxFadeThickness > origValue.getRed():
			decreaserR = origValue.getRed()   / (pxFadeThickness+1)
		if decreaserG*pxFadeThickness > origValue.getGreen():
			decreaserG = origValue.getGreen() / (pxFadeThickness+1)
		if decreaserB*pxFadeThickness > origValue.getBlue():
			decreaserB = origValue.getBlue()  / (pxFadeThickness+1)
		#
		for t in range(1,pxFadeThickness+1):
			# orig coords (at various slices levels) (must be downscaled)
			px = coord[0] - t*dx
			py = coord[1] - t*dy
			pz = coord[2] - t*dz

			nx = int(math.floor((px +0.5) /dsRatio) -min[0])
			ny = int(math.floor((py +0.5) /dsRatio) -min[1])
			nz = int(math.floor((pz +0.5) /dsRatio) -min[2])

			newValue = Color( origValue.getRed() - int(decreaserR * float(t)), origValue.getGreen() - int(decreaserG * float(t)), origValue.getBlue() - int(decreaserB * float(t)) )
			ip = outRGBProcessors[nz]
			ip.setColor(newValue)
			ip.drawPixel(nx,ny)

		# the outer main (image) layer
		#
		# prefetch the value to be inserted
		origValue = inIP.getColor(x,y)
		for t in range(pxThickness):
			# orig coords (at various slices levels) (must be downscaled)
			px = coord[0] + t*dx
			py = coord[1] + t*dy
			pz = coord[2] + t*dz

			nx = int(math.floor((px +0.5) /dsRatio) -min[0])
			ny = int(math.floor((py +0.5) /dsRatio) -min[1])
			nz = int(math.floor((pz +0.5) /dsRatio) -min[2])

			ip = outRGBProcessors[nz]
			ip.setColor(origValue)
			ip.drawPixel(nx,ny)

		# the inner extra (blocking) layer
		#
		for t in range(pxThickness,pxThickness+pxExtraThickness):
			# orig coords (at various slices levels) (must be downscaled)
			px = coord[0] + t*dx
			py = coord[1] + t*dy
			pz = coord[2] + t*dz

			nx = int(math.floor((px +0.5) /dsRatio) -min[0])
			ny = int(math.floor((py +0.5) /dsRatio) -min[1])
			nz = int(math.floor((pz +0.5) /dsRatio) -min[2])

			ip = outRGBProcessors[nz]
			ip.setColor(blockingValue)
			ip.drawPixel(nx,ny)

print("constructing the 3D image...")
stack = ij.ImageStack(xSize,ySize)
for cp in outRGBProcessors:
	stack.addSlice(cp)

outImp = ij.ImagePlus("back-projected "+inImp.getTitle(), stack)

print("showing the 3D image, done afterwards")
outImp.show()
