""" SkaceKamen (c) 2015-2016 """



#####################################################################
# imports

import zlib
from wot.ModelWriter import ModelWriter
import pdb


#####################################################################
# ColladaModelWriter

def m12to16(a):
	ret = [a[0]]+[a[6]]+[a[3]]+[a[9]]+[a[1]]+[a[7]]+[a[4]]+[a[10]]+[-a[2]]+[-a[8]]+[-a[5]]+[-a[11]]+[0,0,0,1]
	return ret

def m12to16bind(a):
	ret = [a[0]]+[a[6]]+[a[3]]+[a[9]]+[-a[2]]+[-a[8]]+[-a[5]]+[a[11]]+[a[1]]+[a[7]]+[a[4]]+[a[10]]+[0,0,0,1]
	return ret

class ColladaModelWriter(ModelWriter):
	ext = '.dae'
	material = False
	normals = False
	uv = False
	scale = None
	textureBase = ''
	textureCallback = None
	compress = False
	textureCounter = 0

	def __init__(
			self,
			material=False,
			normals=False,
			uv=False,
			textureBase='',
			textureCallback=None,
			compress=False,
			scale=None):
		self.material = material
		self.normals = normals
		self.uv = uv
		self.textureBase = textureBase
		self.textureCallback = textureCallback
		self.compress = compress
		self.scale = scale

	def _getMatrixByName(self, inDict, name):
		import collada, numpy
		for ele in inDict['children']:
			if ele == name:	#we have a match, return child's matrix
				xarray = m12to16bind(inDict['children'][ele]['transform'])	#data here is a 16x1 list
				print xarray
				'''
				rmatrix = collada.scene.RotateTransform(1,0,0,90)
				rmatrix2 = collada.scene.RotateTransform(0,1,0,0)
				rmatrix3 = collada.scene.RotateTransform(0,0,1,0)
				bmatrix = collada.scene.MatrixTransform(numpy.array(xarray,dtype=numpy.float32))
				retmatrix = numpy.identity(4, dtype=numpy.float32)
				retmatrix = numpy.dot(retmatrix, rmatrix.matrix)
				retmatrix = numpy.dot(retmatrix, rmatrix2.matrix)
				retmatrix = numpy.dot(retmatrix, rmatrix3.matrix)
				retmatrix = numpy.dot(retmatrix, bmatrix.matrix)
				retlist = retmatrix.tolist()
				return retlist
				'''
				return xarray
			else:
				ret = self._getMatrixByName(inDict['children'][ele],name)
				if ret is not None:
					return ret
	
	def _readScene(self, name, inDict):
		import collada, numpy
		children = []
		xarray = m12to16(inDict['transform'])
		transforms=[]
		transforms.append(collada.scene.RotateTransform(1,0,0,90))
		transforms.append(collada.scene.MatrixTransform(numpy.array(xarray,dtype=numpy.float32)))
		xmlnode = None
		for ele in inDict['children']:
			if 'BlendBone' in ele:
				continue
			children += [self._readScene(ele,inDict['children'][ele])]
#node = collada.scene.Node('node0', children=node_children)
		return collada.scene.Node(name,children,transforms,xmlnode)
		
	
	def baseTextureCallback(self, texture, type):
		return self.textureBase + texture

	def multiply(self, vec1, vec2):
		tpl = False
		if isinstance(vec1, tuple):
			vec1 = list(vec1)
			tpl = True

		for i in range(len(vec1)):
			vec1[i] *= vec2[i]

		if tpl:
			vec1 = tuple(vec1)

		return vec1

	def createTexture(self, path):
		import collada

		img = collada.material.CImage('img_%d' % self.textureCounter, path)
		surface = collada.material.Surface('surface_%d' % self.textureCounter, img)
		sampler = collada.material.Sampler2D('sampler_%d' % self.textureCounter, surface)
		self.textureCounter += 1
		return img, surface, sampler, collada.material.Map(sampler, 'UV')

	def write(self, primitive, filename, filename_material=None):
		# Load required libs now, instead of requiring them for entire library
		import collada
		import numpy

		# Load basic options and use default values if required
		textureCallback = self.textureCallback
		scale = self.scale

		if textureCallback is None:
			textureCallback = self.baseTextureCallback
		if scale is None:
			scale = (1, 1, 1)


		# Create result mesh
		mesh = collada.Collada()
		node_children = []

		# Export all primitiveGroups in renderSets as separate obejcts
		for rindex, render_set in enumerate(primitive.renderSets):
			for gindex, group in enumerate(render_set.groups):
				material = group.material

				name = 'set_%d_group_%d' % (rindex, gindex)
				material_name = material.identifier if material.identifier is not None else name
				material_ref = '%s_ref' % material_name
				effect_name = '%s_effect' % material_name
				matnode = None

				# Create material if requested
				if self.material:
					effect = collada.material.Effect(
						effect_name, [], 'phong', diffuse=(0.5,0.5,0.0), specular=(0,0,0))
					mat = collada.material.Material(
						material_name, material_name, effect)
					matnode = collada.scene.MaterialNode(
						material_ref, mat, inputs=[])

					mesh.effects.append(effect)
					mesh.materials.append(mat)

					if material.diffuseMap:
						img, surface, sampler, effect.diffuse = self.createTexture(
							textureCallback(material.diffuseMap, 'diffuseMap'))
						mesh.images.append(img)
						effect.params.append(surface)
						effect.params.append(sampler)
					if material.specularMap:
						img, surface, sampler, effect.specual = self.createTexture(
							textureCallback(material.specularMap, 'specularMap'))
						mesh.images.append(img)
						effect.params.append(surface)
						effect.params.append(sampler)

					"""
					# How to assign normal map?
					if material.normalMap:
						effect.normal = textureCallback(material.normalMap, "normalMap")
					"""

				vert_values = []
				normal_values = []
				uv_values = []
				indices = []

				for value in group.indices:
					indices.append(value)
					indices.append(value)
					indices.append(value)

				# Add group vertices
				xc=0
				for vertex in group.vertices:
					vert_values.extend(self.multiply(vertex.position, scale))
					normal_values.extend(self.multiply(vertex.normal, scale))
					uv_values.extend(vertex.uv)
					xc+=1
				print 'position vector count:%d'%xc

				vert_src = collada.source.FloatSource(
					'%s_verts' % name,
					numpy.array(vert_values),
					('X', 'Y', 'Z'))
				normal_src = collada.source.FloatSource(
					'%s_normals' % name,
					numpy.array(normal_values),
					('X', 'Y', 'Z'))
				uv_src = collada.source.FloatSource(
					'%s_uv' % name,
					numpy.array(uv_values),
					('S', 'T'))

				input_list = collada.source.InputList()
				input_list.addInput(0, 'VERTEX', '#%s_verts' % name)
				input_list.addInput(1, 'NORMAL', '#%s_normals' % name)
				input_list.addInput(2, 'TEXCOORD', '#%s_uv' % name)

				geom = collada.geometry.Geometry(
					mesh,
					name,
					name,
					[vert_src, normal_src, uv_src])
				triset = geom.createTriangleSet(
					numpy.array(indices),
					input_list,
					material_ref)
				geom.primitives.append(triset)
				mesh.geometries.append(geom)

				if matnode is not None:
					geomnode = collada.scene.GeometryNode(geom, [matnode])
				else:
					geomnode = collada.scene.GeometryNode(geom, [])

				node_children.append(geomnode)

		sceneRootName = primitive.nodes.keys()[0]

		
		#asset info for WoT (1 unit/meter, Z_UP)
		from collada.asset import UP_AXIS
		mesh.assetInfo.unitname = 'meter'
		mesh.assetInfo.unitmeter = 1.0
		mesh.assetInfo.upaxis = UP_AXIS.Z_UP
		
		#skinned controllers
		
		for [idxRset, eleRset] in enumerate(primitive.renderSets):
				renderSet = primitive.renderSets[idxRset]
				if len(eleRset.nodes)>0 and eleRset.nodes[0]!='Scene Root':	#for each renderSet
					print 'skinned renderSet'
					print '# of primitiveGroups in this set: %d'%len(eleRset.groups)
					sourcebyid = {}
					sources = []
#					ch = source.Source.load(collada, {}, sourcenode)
#					ch = collada.source.Source

#source.py:82
					geoName = mesh.geometries[idxRset].id
					geometry = mesh.geometries[geoName]
					controllerName = geoName + 'Controller'
					sourceID_joints = controllerName+'-Joints'	#this is a 'Name_array' containing controller name
#					sourceArray = NameSource.load(collada, localscope, node)
#					sourceArray = collada.source.NameSource( sourceid, data, tuple(components), xmlnode=node )
#source.py:394
					boneListRaw = [v.strip() for v in renderSet.nodes ]
					boneListRaw2 = [v.split('_BlendBone')[0] for v in boneListRaw]
					if 'BlendBone' in boneListRaw2[0]:
						boneList = [v.split('BlendBone')[0] for v in boneListRaw2]
					else:
						boneList = boneListRaw2
					data = numpy.array(boneList, dtype = numpy.string_)
					components = ('JOINT',)
					source_joints = collada.source.NameSource(sourceID_joints, data, components, None)

#controller matrices is a float array
					data = []
					for ele in boneListRaw:
						m = self._getMatrixByName(primitive.nodes[sceneRootName],ele)
						if m is not None:
							data.append(m)
					strArray = str(data)
					strArray = strArray.replace(',',' ')
					strArray = strArray.replace('[','')
					strArray = strArray.replace(']','')
					data = numpy.fromstring(strArray,dtype=numpy.float32, sep=' ')
					data[numpy.isnan(data)] = 0
					data.shape=(-1,4,4)
					print 'size of matrics retrieved: %d'%len(data)
					sourceID_matrices = controllerName+'-Matrices'
					source_matrices = collada.source.FloatSource(sourceID_matrices ,data,(None,),None)

#controller weights is a float array
					data = []
					vcount = []
					v = []
					indicesFromCollada = geometry.primitives[0].indices
					indicesFromCollada.shape = (-1,3)
					vertexIndexFromCollada = []
					for i in indicesFromCollada:
						vertexIndexFromCollada.append(i[0])
					for [idxGroup, eleGroup] in enumerate(renderSet.groups):
						ptW = 0
						for idxV,vertex in enumerate(eleGroup.vertices):
#						for idxV in eleGroup.indices:
#							vertex = eleGroup.vertices[idxV]
#							print 'weight of vertex %d is %s' %(idxV,str(vertex.weight)) 
							vc=0
							lstBone = vertex.index
							lstWeight = vertex.weight
							for [idxW, w] in enumerate(lstWeight):
								if abs(w)>=0.001:
									data.append(w)
									v.append(lstBone[idxW])
									v.append(ptW)
									ptW += 1
									vc += 1
							vcount.append(vc)
					data = numpy.array(data,dtype=numpy.float32)
					sourceID_weights = controllerName+'-Weights'
					source_weights = collada.source.FloatSource(sourceID_weights ,data,('WEIGHT',),None)

#added sources to repo
					sources.append(source_joints)
					sources.append(source_matrices)
					sources.append(source_weights)
					sourcebyid[source_joints.id] = source_joints
					sourcebyid[source_matrices.id] = source_matrices
					sourcebyid[source_weights.id] = source_weights
#					pdb.set_trace()
					
# now mimic controller.Skin.load(collada, sourcebyid, controller, node)			
					
					print 'template dae has a strange shape matrix at -0.5,0.5,0'
					print 'use identity matrix as replacement for the time being'

					# bind_shape_mat is most probably the pivot location of the geometry 
					# It's important sometimes
					# because position matrix probably based their coordinate on this pivot
					# WG standard model should have centered pivot though.
					bind_shape_mat = numpy.identity(4, dtype=numpy.float32)
					bind_shape_mat.shape = (-1,)
					joint_source = sourceID_joints
					matrix_source = sourceID_matrices
					index = numpy.array(v,dtype=numpy.int32)
					vcounts = numpy.array(vcount, dtype=numpy.int32)
					weight_joint_source = sourceID_joints
					weight_source = sourceID_weights
					offsets = [0,1]
					controller_skin = collada.controller.Skin(sourcebyid, bind_shape_mat, joint_source, matrix_source,
                weight_source, weight_joint_source, vcounts, index, offsets,
                geometry, None, None, controllerName)
					mesh.controllers.append(controller_skin)
					
		#this is why we're missing all the dummy nodes.
		#rewrite this section
		'''
		node = collada.scene.Node('node0', children=node_children)
		myscene = collada.scene.Scene('myscene', [node])
		mesh.scenes.append(myscene)
		mesh.scene = myscene
		'''
		#new scene:
		#_unpackNodesToScene
		print 'dumping scene to collada '
		nodes=[]
		for ele in primitive.nodes[sceneRootName]['children']:
			nodes.append( self._readScene(ele,primitive.nodes[sceneRootName]['children'][ele]))
#		sceneRootNode.transforms = []		#somehow i'm getting -100% scaling at SceneRoot
		if len(mesh._controllers)==0:
			print '******not skinned'
			nodes.append(collada.scene.Node('node0', children=node_children))
		else:
			print '******skinned'
			
			for ele in mesh._controllers:
				node_children_skinned = []
				node_children_skinned.append(collada.scene.ControllerNode(ele,[]))	#todo: material node support
				nodes.append(collada.scene.Node(ele.id.rstrip('Controller'), children=node_children_skinned))
		myscene = collada.scene.Scene('myscene', nodes)
		mesh.scenes.append(myscene)
		mesh.scene = myscene
		
				
#	if primitive.renderSets

#		pdb.set_trace()
		mesh.write(filename)

		return filename
