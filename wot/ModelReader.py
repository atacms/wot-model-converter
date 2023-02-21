""" SkaceKamen (c) 2015-2016 """

#####################################################################
# Thanks Coffee_ for discovering the primitives format
# and writing original script that did the unpacking. This is
# just rewritten script to python.



#####################################################################
# imports

from wot.XmlUnpacker import XmlUnpacker
from wot.VertexTypes import *
import xml.etree.ElementTree as ET
from struct import unpack
from io import BytesIO
from sys import version_info
isSkinnedFile = False
import numpy
import binascii


if version_info < (3, 0, 0):
	range = xrange



#####################################################################
# functions

def unp(format, data):
	return unpack(format, data)[0]



def readBool(item):
	value = item.strip().lower()
	if value == 'true' or value == '1':
		return 1
	return 0



def readInt(item):
	if item is None:
		return 0
	return int(item)



#####################################################################
# ModelReader

class ModelReader:
	debug = False

	def __init__(self,debug=False):
		self.debug = debug

	def out(self, text):
		if self.debug:
			print(text)

	def read(self, primitives_fh, visual_fh):
		# Read visual file
		xmlr = XmlUnpacker()
		visual = xmlr.read(visual_fh)

		# Makes core short
		f = primitives_fh

		# Load sections table
		# Starts from back
		f.seek(-4, 2)
		table_start = unp('I', f.read(4))
		f.seek(-4-table_start, 2)

		# Position of section starts from 4
		position = 4

		self.out('== SECTIONS')

		# Read sections
		sections = {}
		while True:
			# Read section size
			data = f.read(4)

			if data == None or len(data) != 4:
				break

			section_size = unp('I', data)

			# Skip bytes with unknown purpose
			if len(f.read(16)) != 16:
				break

			# Read section name
			section_name_length = unp('I', f.read(4))
			section_name = f.read(section_name_length).decode('UTF-8')

			# Section informations
			section = {
				'position': position,
				'size': section_size,
				'name': section_name,
				'data': None
			}

			self.out('%s position %X size %X' % (section_name, section['position'], section['size']))

			sections[section_name] = section

			# Round to 4
			position += section_size
			if section_size % 4 > 0:
				position += 4 - section_size % 4

			if section_name_length % 4 > 0:
				f.read(4 - section_name_length % 4)

		# Read sections data
		for name, section in sections.items():
			f.seek(section['position'])
			section['data'] = BytesIO(f.read(section['size']))

		# Read visual data
		nodes = {}
		nodes['Scene Root'] = self.readNode(visual.find('node'))
		boundingBox = [
			[float(v) for v in visual.find('boundingBox').find('min').text.split(' ')],
			[float(v) for v in visual.find('boundingBox').find('max').text.split(' ')]
		]

		# Load render sets
		sets = []
		for render_set in visual.findall('renderSet'):
			isSkinnedSet = False	#this will be known when actually seen the first material in the set
			# Nodes - nodes associated with this set. 
			#    static render in static visual:  default to a single 'scene root'
			#    static render in skinned visual: parent node
			#    skinned render in skinned visual: bones used in the skinning. sequence matters.
			set_nodes = [v.text for v in render_set.findall('node')]

			# Names of sections used in this render set
			vertices_name = render_set.find('geometry').find('vertices').text.strip()
			indices_name = render_set.find('geometry').find('primitive').text.strip()
			stream_name = None
			if render_set.find('geometry').find('stream') is not None:
				stream_name = render_set.find('geometry').find('stream').text.strip()

			# Load render set data
			vertices = self.readVertices(sections[vertices_name]['data'])
			indices, groups = self.readIndices(sections[indices_name]['data'])

			# Load stream data
			# For some reason this section can be missing
			uv2 = None
			colour = None
			if stream_name and stream_name in sections:
				print 'found stream: %s'%stream_name
				print sections[stream_name]
				data, type = self.readStream(sections[stream_name])
				if type == 'colour':
					colour = data
				elif 'uv2' in type:
					uv2 = data


			# Apply stream data
			if uv2 or colour:
				for index, vertex in enumerate(vertices):
					if uv2:
						vertex.uv2 = uv2[index]
					if colour:
						vertex.colour = colour[index]

			# Split data into groups
			primitive_groups = []
			for group in render_set.find('geometry').findall('primitiveGroup'):
				material = self.readMaterial(group.find('material'))
#				print material.fx
				if 'skinned' in material.fx:
					isSkinnedSet = True
				origin = group.find('groupOrigin')
				if origin is not None:
					origin = tuple(map(float, origin.text.strip().split(' ')))
				index = int(group.text.strip())

				i_from = groups[index]['startIndex']
				i_to = i_from + groups[index]['primitivesCount']*3
				v_from = groups[index]['startVertex']
				v_to = v_from + groups[index]['verticesCount']

				self.out('group indices %d / %d (%d - %d)' % ((i_to - i_from), len(indices), i_from, i_to))
				self.out('group vertices %d / %d (%d - %d)' % ((v_to - v_from), len(vertices), v_from, v_to))

#reverse triangle order for skinned objects
				'''
				if isSkinned:
					print 'skinned. reversing triangle order in reading'
					indices = [v - groups[index]['startVertex'] for v in indices[i_from:i_to]]
					indicesRev = []
					tmp = numpy.array(indices)
					tmp.shape = (-1,3)
					for ele in tmp:
						indicesRev.append(ele[2])
						indicesRev.append(ele[1])
						indicesRev.append(ele[0])
					primitive_groups.append(PrimitiveGroup(
							origin = origin,
							material = material,
							vertices = vertices[v_from:v_to],
							indices = indicesRev
					))
					print indices[0:10]
					print indicesRev[0:10]
				else:
				'''
				if True:
						primitive_groups.append(PrimitiveGroup(
						origin = origin,
						material = material,
						vertices = vertices[v_from:v_to],
						indices = [v - groups[index]['startVertex'] for v in indices[i_from:i_to]]
						))

			# Save render set
			sets.append(RenderSet(
				nodes = set_nodes,
				groups = primitive_groups,
				isSkinned = isSkinnedSet
			))

		return Primitive(
			renderSets = sets,
			nodes = nodes,
			boundingBox = boundingBox
		)

	def readMaterial(self, element):
		material = Material()

		# @TODO: Material has more properties ...
		for item in element:
			item_text = item.text.strip()
			if item.tag == 'fx':
				material.fx = item_text
			elif item.tag == 'collisionFlags':
				material.collisionFlags = item_text
			elif item.tag == 'materialKind':
				material.materialKind = item_text
			elif item.tag == 'identifier':
				material.ident = item_text
			elif item.tag == 'property':
				if item_text == 'diffuseMap':
					material.diffuseMap = item.find('Texture').text.strip().replace('.tga', '.dds')
				elif item_text == 'diffuseMap2':
					material.diffuseMap2 = item.find('Texture').text.strip().replace('.tga', '.dds')
				elif item_text == 'specularMap':
					material.specularMap = item.find('Texture').text.strip().replace('.tga', '.dds')
				elif item_text == 'normalMap':
					material.normalMap = item.find('Texture').text.strip().replace('.tga', '.dds')
				elif item_text == 'doubleSided':
					material.doubleSided = readBool(item.find('Bool').text)
				elif item_text == 'alphaReference':
					material.alphaReference = readInt(item.find('Int').text)

		return material

	def readVertices(self, data):
		self.out('== VERTICES')

		vertices = []

		type = data.read(64).split(b'\x00')[0].decode('UTF-8')
		subtype = None
		count = unp('I', data.read(4))

		if 'BPVT' in type:
			subtype = data.read(64).split(b'\x00')[0].decode('UTF-8')
			count = unp('I', data.read(4))

		# Decide correct type
		vtype = self.getVertType(type, subtype)

		self.out('type %s subtype %s count %d stride %d' % (type, subtype, count, vtype.SIZE))

		for i in range(count):
			vertices.append(self.readVertice(data, vtype))

		return vertices

	def getVertType(self, type, subtype):
		if subtype is not None:
			if subtype == vt_SET3_XYZNUVIIIWWTBPC.V_TYPE:
				return vt_SET3_XYZNUVIIIWWTBPC
			elif subtype == vt_SET3_XYZNUVTBPC.V_TYPE:
				return vt_SET3_XYZNUVTBPC
			elif subtype == vt_SET3_XYZNUVPC.V_TYPE:
				return vt_SET3_XYZNUVPC
		else:
			if type == vt_XYZNUVIIIWWTB.V_TYPE:
				return vt_XYZNUVIIIWWTB
			elif type == vt_XYZNUVTB.V_TYPE:
				return vt_XYZNUVTB
			elif type == vt_XYZNUV.V_TYPE:
				return vt_XYZNUV

	def readVertice(self, data, vtype):
		global isSkinnedFile
		vert = Vertex()
		x1=data.tell()

		# Load basic info - xyznuv
		(x, z, y) = unpack('<3f', data.read(12))
		if vtype.IS_SKINNED:	#invert Y here seems to be causing trouble for some subtype of skinned parts. WG is roughly unaffected. customized export without invert face is wrong. with invert faces is not tested
			isSkinnedFile = True
			y = -y		#maybe to move this mechanism to obj export module to protect the integrity of main data repository.
		vert.position = (x, y, z)
		vert.normal = self.readNormal(data, vtype.IS_NEW)
		(u, v) = unpack('<2f', data.read(8))
		vert.uv = (u, 1-v)

		# Unpack remaining values
		if vtype.V_TYPE in (vt_SET3_XYZNUVTBPC.V_TYPE, vt_XYZNUVTB.V_TYPE):
			vert.tangent = unp('<I', data.read(4))
			vert.binormal = unp('<I', data.read(4))
		elif vtype.V_TYPE == vt_SET3_XYZNUVIIIWWTBPC.V_TYPE:
			(index3, index2, index1) = unpack('3B', data.read(3))
			(index1, index2, index3) = (index1//3, index2//3, index3//3)
			vert.index = (index1, index2, index3)
			vert.index2 = unpack('2B', data.read(2)) # extended weight index, not used by WG for the moment
			(weight2, weight1) = unpack('2B', data.read(2))
			(weight1, weight2) = (weight1/255.0, weight2/255.0)
			weight3 = 1.0 - weight1 - weight2
			data.read(1)
			if 0:
#			if index3 != 1:
#			if bool(weight1>0 and weight1<1) or bool(weight2>0 and weight2<1):
				x2 = data.tell()
				data.seek(x1+24)
				print (vert.position)
				print (vert.index)
				print (binascii.hexlify(data.read(vtype.SIZE-24)))
				print ('\n weight1=%f, weight2=%f '%(weight1,weight2))
				raw_input('intermediate weight. anykey to continue')
				data.seek(x2)
				
			vert.weight = (weight1, weight2, weight3)
			vert.tangent = unp('<I', data.read(4))
			vert.binormal = unp('<I', data.read(4))
		elif vtype.V_TYPE == vt_XYZNUVIIIWWTB.V_TYPE:
			(index1, index2, index3) = unpack('3B', data.read(3))
			(index1, index2, index3) = (index1//3, index2//3, index3//3)
			(weight1, weight2) = unpack('2B', data.read(2))
			(weight1, weight2) = (weight1/255.0, weight2/255.0)
			weight3 = 1.0 - weight1 - weight2
			vert.index = (index1, index2, index3)
			vert.weight = (weight1, weight2, weight3)
			vert.tangent = unp('<I', data.read(4))
			vert.binormal = unp('<I', data.read(4))

		return vert

	def readNormal(self, data, IS_NEW):
		packed = unp('I', data.read(4))
		if IS_NEW:
			pkz = (int(packed)>>16)&0xFF^0xFF
			pky = (int(packed)>>8)&0xFF^0xFF
			pkx = int(packed)&0xFF^0xFF

			if pkx > 0x7f:
				x = -float(pkx&0x7f)/0x7f
			else:
				x = float(pkx^0x7f)/0x7f
			if pky > 0x7f:
				y = -float(pky&0x7f)/0x7f
			else:
				y = float(pky^0x7f)/0x7f
			if pkz >0x7f:
				z = -float(pkz&0x7f)/0x7f
			else:
				z = float(pkz^0x7f)/0x7f
			return (x, z, y)
		else:
			pkz = (int(packed) >> 22) & 0x3FF
			pky = (int(packed) >> 11) & 0x7FF
			pkx = int(packed) & 0x7FF

			if pkx > 0x3ff:
				x = -float((pkx&0x3ff^0x3ff)+1)/0x3ff
			else:
				x = float(pkx)/0x3ff
			if pky > 0x3ff:
				y = -float((pky&0x3ff^0x3ff)+1)/0x3ff
			else:
				y = float(pky)/0x3ff
			if pkz > 0x1ff:
				z = -float((pkz&0x1ff^0x1ff)+1)/0x1ff
			else:
				z = float(pkz)/0x1ff
			return (x, z, y)

	def readIndices(self, data):
		self.out('== INDICES')

		# Prepare informations
		indices = []
		groups = []

		# Read type (ended by 0)
		type = data.read(64).split(b'\x00')[0].decode('UTF-8', 'ignore')

		# One indice length
		stride = 2
		format = '<3H'

		if type == 'list32':
			stride = 4
			format = '<3I'

		# Read totals
		count = unp('<I', data.read(4))
		groups_count = unp('<I', data.read(4))

		self.out('groups %d indices %d stride %d type %s' % (groups_count, count, stride, type))

		# Read indices
		for i in range(count//3):
			i3, i2, i1 = unpack(format, data.read(stride*3))
			indices += [i1, i2, i3]

		# Read groups
		for i in range(groups_count):
			ints = unpack('4I', data.read(16))
			groups.append({
				'id': i,
				'startIndex': ints[0],
				'primitivesCount': ints[1],
				'startVertex': ints[2],
				'verticesCount': ints[3]
			})

		return (indices, groups)

	def readStream(self, section):
		data = section['data']
		stream_name = section['name']
		size = section['size']
		self.out('== STREAM')
		result = []

		# Read type (ended by \x00)
		try:
			type = data.read(64).split(b'\x00')[0].decode('UTF-8')
			subtype = None
			count = unp('I', data.read(4))

			if 'BPV' in type:
				subtype = data.read(64).split(b'\x00')[0].decode('UTF-8')
				count = unp('I', data.read(4))

			self.out('stream type (%s %s) count %d' % (type, subtype, count))
		except:		#data type header is not present. the entire section is raw data
			print "!!!invalid stream data format header."
			print "Most likely this model is made by old BW SDK (2.1.x) which can not specify stream format"
			print "will treat the entire stream as raw data"
			data.seek(0)
			if '.uv2' in stream_name:
				type = 'uv2'
				subtype = 'uv2'
				count = size/8
			elif '.colour' in stream_name:
				type = 'colour'
				subtype = 'colour'
				count = size/4
			

		for i in range(count):
			if subtype == 'colour':
				result.append(unpack('4B', data.read(4)))
			elif 'uv2' in subtype:
				result.append(unpack('2f', data.read(8)))

		return result, subtype if subtype is not None else type

	def readNode(self, element):
		element_transform = element.find('transform')
		if element_transform.text.strip():
			rows = element_transform.text.strip().split(' ')
		else:
			rows = element_transform.find('row0').text.strip().split(' ') + \
				element_transform.find('row1').text.strip().split(' ') + \
				element_transform.find('row2').text.strip().split(' ') + \
				element_transform.find('row3').text.strip().split(' ')
		node = {
			'transform': [float(v) for v in rows],
			'children': {}
		}

		for child in element.findall('node'):
			node['children'][child.find('identifier').text.strip()] = self.readNode(child)

		return node



#####################################################################
# Primitive

class Primitive:
	renderSets = None
	nodes = None
	boundingBox = None

	def __init__(self, renderSets, nodes, boundingBox):
		self.renderSets = renderSets
		self.nodes = nodes
		self.boundingBox = boundingBox



#####################################################################
# RenderSet

class RenderSet:
	nodes = None
	groups = None
	isSkinned = False

	def __init__(self, nodes, groups, isSkinned):
		self.nodes = nodes
		self.groups = groups
		self.isSkinned = isSkinned



#####################################################################
# PrimitiveGroup

class PrimitiveGroup:
	origin = None
	material = None
	vertices = None
	indices = None

	def __init__(self, origin, material, vertices, indices):
		self.origin = origin
		self.material = material
		self.vertices = vertices
		self.indices = indices



#####################################################################
# Material

class Material:
	shader = None
	collisionFlags = None
	materialKind = None
	identifier = None
	diffuseMap = None
	diffuseMap2 = None
	doubleSided = None
	specularMap = None
	alphaReference = None
	normalMap = None



#####################################################################
# Vertex

class Vertex:
	position = None
	normal = None
	uv = None
	uv2 = None
	colour = None
	index = None
	index2 = None
	index3 = None
	weight = None
	weight2 = None
	tangent = None
	binormal = None

	def __eq__(self, other):
		return (
			self.position == other.position and
			self.normal == other.normal and
			self.uv == other.uv and
			self.uv2 == other.uv2 and
			self.colour == other.colour and
			self.index == other.index and
			self.index2 == other.index2 and
			self.index3 == other.index3 and
			self.weight == other.weight and
			self.weight2 == other.weight2 and
			self.tangent == other.tangent and
			self.binormal == other.binormal)
