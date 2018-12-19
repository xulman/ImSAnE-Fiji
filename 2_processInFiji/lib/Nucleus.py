import math

# this section adds a folder, in which this very script is living,
# to the current search paths so that we can import our "library script"
import sys.path
import os.path
import inspect
ScriptsRoot = os.path.dirname(os.path.dirname(sys.path[0]))+os.sep+"scripts"
ThisFile    = os.path.dirname(inspect.getfile(inspect.currentframe()))
sys.path.append(ScriptsRoot+os.sep+ThisFile)
sys.path.append(ThisFile)

# import our "library scripts"
from properMeasurements import *


class Nucleus:

	def __init__(self,Color,Pixels,ip,realSizes,realCoords):
		# stringy label of the nuclei
		self.Color = Color

		# a scalar value to be used in chooseNuclei.drawChosenNucleiValue(),
		# one may save here an arbitrary visualization hint for the nuclei drawing
		self.DrawValue = 1

		# list of pixels that make up this nuclei (nuclei mask)
		self.Pixels = Pixels

		# object area in squared microns
		self.Area = 0.0
		# object area in pixel number
		self.Size = len(Pixels)

		# geometric centre in pixel coordinates
		self.CentreX = 0.0
		self.CentreY = 0.0

		# calculate real size and geometrical centre
		for pix in Pixels:
			self.Area += realSizes[pix[0]][pix[1]]
			self.CentreX += pix[0]
			self.CentreY += pix[1]

		# finish calculation of the geometrical centre
		self.CentreX /= len(Pixels)
		self.CentreY /= len(Pixels)

		# list of pixels that make up boundary of this nuclei (nuclei mask)
		self.EdgePixels = []

		# (approximate) length of the boundary in microns
		self.EdgeLength = 0.0

		# shortcut to the pixel values
		i = ip.getPixels()
		w = ip.getWidth()

		# integer label of the nuclei
		self.Label = i[w*Pixels[0][1] + Pixels[0][0]]
		thisColor = self.Label

		# offsets of pixels just outside this nucleus
		outterBgEdge = set()

		# determine boundary pixels
		for pix in Pixels:
			# pixel offset within the image
			o = w*pix[1] + pix[0]

			try:
				ColorAbove = i[ o-w ]
			except:
				ColorAbove = -1

			try:
				ColorLeft = i[ o-1 ]
			except:
				ColorLeft = - 1

			#thisColor = i[o]

			try:
				ColorRight = i[ o+1 ]
			except:
				ColorRight = -1

			try:
				ColorBelow = i[ o+w ]
			except:
				ColorBelow = -1

			# mimics 2D 4-neighbor erosion:
			# encode which neighbors are missing, and how many of them
			missNeig = 0
			cnt = 0;

			if thisColor != ColorLeft:
				missNeig += 1
				cnt += 1
			if thisColor != ColorAbove:
				missNeig += 2
				cnt += 1
			if thisColor != ColorRight:
				missNeig += 4
				cnt += 1
			if thisColor != ColorBelow:
				missNeig += 8
				cnt += 1

			if missNeig != 0:
				# found border-forming pixel, enlist it
				self.EdgePixels.append([pix[0],pix[1]])

				# Marching-cubes-like determine configuration of the border pixel,
				# and guess an approximate proper length of the boundary this pixels co-establishes
				coords = []

				# legend on bits used to flag directions:
				#
				#           2
				#          (y-)
				#           |
				#           |
				# 1 (x-) <--+--> (x+) 4
				#           |
				#           |
				#          (y+)
				#           8
				#

				if cnt == 1:
					# one neighbor is missing -> boundary is straight here
					if missNeig&1 or missNeig&4:
						# vertical boundary
						coords = [ [pix[0],pix[1]-1] , [pix[0],pix[1]] , [pix[0],pix[1]+1] ]
					else:
						# horizontal boundary
						coords = [ [pix[0]-1,pix[1]] , [pix[0],pix[1]] , [pix[0]+1,pix[1]] ]

				if cnt == 2:
					# two neighbors -> we're either a corner, or boundary is 1px thick
					if missNeig&5 == 5 or missNeig&10 == 10:
						# 1px thick boundary
						if missNeig&5 == 5:
							# 1px thick vertical boundary
							coords = [ [pix[0],pix[1]-1] , [pix[0],pix[1]] , [pix[0],pix[1]+1] , [pix[0],pix[1]] , [pix[0],pix[1]-1] ]
						else:
							# 1px thick horizontal boundary
							coords = [ [pix[0]-1,pix[1]] , [pix[0],pix[1]] , [pix[0]+1,pix[1]] , [pix[0],pix[1]] , [pix[0]-1,pix[1]] ]
					else:
						# missing neighbors are "neighbors" to each other too -> we're a corner
						if missNeig&6 == 6 or missNeig&9 == 9:
							# we're top-right corner, or bottom-left corner
							coords = [ [pix[0]-1,pix[1]-1] , [pix[0],pix[1]] , [pix[0]+1,pix[1]+1] ]

						if missNeig&12 == 12 or missNeig&3 == 3:
							# we're bottom-right corner, or top-left corner
							coords = [ [pix[0]-1,pix[1]+1] , [pix[0],pix[1]] , [pix[0]+1,pix[1]-1] ]

				if cnt == 3:
					# three neighbors -> we're "a blob or a spike" popping out from a straight boundary...
					if missNeig&7 == 7:
						# have only a neighbor below
						coords = [ [pix[0]-1,pix[1]+1] , [pix[0],pix[1]] , [pix[0]+1,pix[1]+1] ]

					if missNeig&11 == 11:
						# have only a neighbor right
						coords = [ [pix[0]+1,pix[1]-1] , [pix[0],pix[1]] , [pix[0]+1,pix[1]+1] ]

					if missNeig&13 == 13:
						# have only a neighbor above
						coords = [ [pix[0]-1,pix[1]-1] , [pix[0],pix[1]] , [pix[0]+1,pix[1]-1] ]

					if missNeig&14 == 14:
						# have only a neighbor left
						coords = [ [pix[0]-1,pix[1]-1] , [pix[0],pix[1]] , [pix[0]-1,pix[1]+1] ]

				if cnt == 4:
					# four neighbors -> we're an isolated pixel
					coords = [ [pix[0]-1,pix[1]] , [pix[0],pix[1]+1] , [pix[0]+1,pix[1]] , [pix[0],pix[1]-1] , [pix[0]-1,pix[1]] ]

				# calculate the proper length of the local boundary by sweeping
				# through a neighbor,myself,neighbor (giving us twice the required length)
				self.EdgeLength += properLength(coords,realCoords)   # / 2.0

#				#DEBUG VLADO REMOVE
#				a = coords[0]
#				b = coords[1]
#				c = coords[2]
#				for i in [0,1]:
#					a[i] = (float(a[i])+float(b[i]))/2.0
#					c[i] = (float(b[i])+float(c[i]))/2.0
#
#				print str(a[0])+" "+str(a[1])+" 1"
#				print str(b[0])+" "+str(b[1])+" 2"
#				print str(c[0])+" "+str(c[1])+" 1"
#				print ""

				# enlist background pixels surrounding this edge/border pixel
				for x in [-w-1,-w,-w+1, -1,1, +w-1,+w,+w+1]:
					if i[o+x] == 0:
						outterBgEdge.add(o+x)

		# finish the length of the boundary in microns
		self.EdgeLength /= 2.0

		# length of the boundary in pixel
		self.EdgeSize = len(self.EdgePixels)

		# circularity: higher value means higher circularity
		self.Circularity = (self.Area * 4.0 * math.pi) / (self.EdgeLength * self.EdgeLength)

		# set of labels touching this nuclei (component)
		self.NeighIDs = set([thisColor])

		# iterate over all just-outside-boundary pixels,
		# and check their surrounding values
		for oo in outterBgEdge:
			for x in [-w-1,-w,-w+1, -1,1, +w-1,+w,+w+1]:
				if i[oo+x] > 0:
					self.NeighIDs.add(i[oo+x])
		self.NeighIDs.remove(thisColor)


	# the same condition that everyone should use to filter out nuclei that
	# do not qualify for this study
	def doesQualify(self, areaConsidered,areaMin,areaMax, circConsidered,circMin,circMax):
		if (circConsidered == True and (self.Circularity < circMin or self.Circularity > circMax)):
			return False;
		if (areaConsidered == True and (self.Area < areaMin or self.Area > areaMax)):
			return False;
		return True;
