#@int(label="stop latest after this no. of rounds") maxRounds
#@int(label="stop if there was less than this no. of pixel changes") minPixelChanges
from ij import IJ


# returns a map of pixel values around this pixel,
# the pixel values are stored as keys in this map (and are hence unique),
# the pixel is given with its offset 'o' in the 2D image (array) 'i'
# whose width is 'w' and height is 'h'; the output map is actually
# a histogram of pixels in 8-neighborhood around the input pixel
def findUniqueNeighbors(i,o,w,h):
	values = []
	for x in [-1,0,1]:
		values.append( i[o-w+x] )
	for x in [-1,1]:
		values.append( i[o  +x] )
	for x in [-1,0,1]:
		values.append( i[o+w+x] )

	h = {}
	for v in values:
		if v in h:
			h[v] = h[v]+1
		else:
			h[v] = 1

	return h


def pseudoClosing(imp):
	i = imp.getProcessor().getPixels()
	w = imp.getWidth()
	h = imp.getHeight()

	# have a copy of the original so that "neighborhood computations"
	# are not affected by the on-going processing
	I = [ i[o] for o in range(len(i)) ]

	countChanges = 0

	for y in range(1,h-1):
		for x in range(1,w-1):
			# offset
			o = y*w + x

			if I[o] == 0:
				# found empty/black pixel,
				# is it surrounded only by the same non-zero colour?
				h = findUniqueNeighbors(I,o,w,h)

				v = h.keys()
				# one-bin histogram: surrounded by fg voxels?
				if len(v) == 1 and v[0] > 0:
					i[o] = v[0]
					countChanges = countChanges+1

				# two-bins histogram: surrounded by bg and in majority by single-fg voxels?
				if len(v) == 2 and v[0] == 0 and h[v[1]] > 4:
					i[o] = v[1]
					countChanges = countChanges+1

	return countChanges


def testing():
	imp = IJ.getImage()
	i = imp.getProcessor().getPixels()
	w = imp.getWidth()
	h = imp.getHeight()
	o = 69012
	print findUniqueNeighbors(i,o,w,h)

	o = 69011
	print findUniqueNeighbors(i,o,w,h)

	o = 69010
	print findUniqueNeighbors(i,o,w,h)


def pluginCode():
	imp = IJ.getImage()

	for i in range(maxRounds):
		cnt = pseudoClosing(imp)
		imp.updateAndRepaintWindow()

		print "done iteration #"+str(i+1)+", and saw "+str(cnt)+" changes"

		if cnt <= minPixelChanges:
			break;

	print "finito."


pluginCode()
