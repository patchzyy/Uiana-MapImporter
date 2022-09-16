
import os
from os.path import exists
import re
import winsound
import subprocess
from pathlib import Path
import unreal
import time
from mods.liana.helpers import *
from mods.liana.valorant import *

Seting = None
LoadableMaterials = {}
AllMeshes = [] 
AllTextures= []
AllBps = {}
object_types = []
AllLevelPaths = []
file = "snd.mp3"
AssetTools = unreal.AssetToolsHelpers.get_asset_tools()
#BaseEnv = ["BaseEnv_Blend_MAT_V4","BaseEnv_Blend_MAT_V4_V3Compatibility","BaseEnv_MAT_V4","BaseEnv_MAT_V4_Inst","BaseEnv_MAT","BlendEnv_MAT","BaseEnvEmissiveUnlit_MAT"]
def GetMaterialToOverride(Data):
	Props = Data["Properties"]
	MaterialArray = []
	OverrideMaterials = Props["OverrideMaterials"]
	for mat in OverrideMaterials:
		if not mat:
			MaterialArray.append(None)
			continue
		matname = mat["ObjectName"]
		CheckLoaded = ReturnObjectName(matname)
		if CheckLoaded == "Stone_M2_Steps_MI1":
			CheckLoaded =  "Stone_M2_Steps_MI"
		if "MaterialInstanceDynamic" in CheckLoaded:
			MaterialArray.append(None)
			continue
		MaterialArray.append(unreal.load_asset(f'/Game/ValorantContent/Materials/{CheckLoaded}'))
	return MaterialArray

def extract_assets(settings: Settings):
	assetobjects = settings.selected_map.folder_path.joinpath("all_assets.txt")
	args = [settings.umodel.__str__(),
			f"-path={settings.paks_path.__str__()}",
			f"-game=valorant",
			f"-aes={settings.aes}",
			f"-files={assetobjects}",
			"-export",
			f"-{settings.texture_format.replace('.', '')}",
			f"-out={settings.assets_path.__str__()}"]
	subprocess.call(args,stderr=subprocess.DEVNULL)

def extract_data(settings: Settings, export_directory: str, asset_list_txt: str = ""):
	args = [settings.cue4extractor.__str__(),
			"--game-directory", settings.paks_path.__str__(),
			"--aes-key", settings.aes,
			"--export-directory", export_directory.__str__(),
			"--map-name", settings.selected_map.name,
			"--file-list", asset_list_txt,
			"--game-umaps", settings.umap_list_path.__str__()
			]
	subprocess.call(args)

def get_map_assets(settings: Settings):
	umaps = []

	if not settings.selected_map.folder_path.joinpath("exported.yo").exists():
		extract_data(settings, export_directory=settings.selected_map.umaps_path)
		extract_assets(settings)

		umaps = get_files(
			path=settings.selected_map.umaps_path.__str__(), extension=".json")
		umap: Path

		object_list = list()
		actor_list = list()
		materials_ovr_list = list()
		materials_list = list()

		for umap in umaps:
			umap_json, asd = filter_umap(read_json(umap))
			object_types.append(asd)

			# save json
			save_json(umap.__str__(), umap_json)

			# get objects
			umap_objects, umap_materials,umap_actors  = get_objects(umap_json)
			actor_list.append(umap_actors)
			object_list.append(umap_objects)
			materials_ovr_list.append(umap_materials)
		######## ACTORS
		actor_txt = save_list(filepath=settings.selected_map.folder_path.joinpath(f"_assets_actors.txt"), lines=actor_list)
		extract_data(settings, export_directory=settings.selected_map.actors_path,asset_list_txt=actor_txt)
		actors = get_files(path=settings.selected_map.actors_path.__str__(), extension=".json")
		ActorObjects = list()
		ActorMaterials = list()
		allActorAssets = list()
		local4list = list()
		for ac in actors:
			actor_json = read_json(ac)
			ActorObjects, ActorMaterials,local4list = get_objects(actor_json)
			object_list.append(ActorObjects)
			materials_ovr_list.append(ActorMaterials)
		#### next
		object_txt = save_list(filepath=settings.selected_map.folder_path.joinpath(
			f"_assets_objects.txt"), lines=object_list)
		mats_ovr_txt = save_list(filepath=settings.selected_map.folder_path.joinpath(
			f"_assets_materials_ovr.txt"), lines=materials_ovr_list)

		extract_data(settings, export_directory=settings.selected_map.objects_path,
					 asset_list_txt=object_txt)
		extract_data(settings, export_directory=settings.selected_map.materials_ovr_path,
					 asset_list_txt=mats_ovr_txt)

		# ---------------------------------------------------------------------------------------

		models = get_files(
			path=settings.selected_map.objects_path.__str__(), extension=".json")
		model: Path
		for model in models:
			model_json = read_json(model)
			model_name = model.stem
			# save json
			save_json(model.__str__(), model_json)
			# get object materials
			model_materials = get_object_materials(model_json)
			# get object textures
			# ...

			materials_list.append(model_materials)
		save_list(filepath=settings.selected_map.folder_path.joinpath("all_assets.txt"), lines=[
            [
                path_convert(path) for path in _list
            ] for _list in object_list + materials_list + materials_ovr_list
        ])
		mats_txt = save_list(filepath=settings.selected_map.folder_path.joinpath(
			f"_assets_materials.txt"), lines=materials_list)
		extract_data(settings, export_directory=settings.selected_map.materials_path,
					 asset_list_txt=mats_txt)
		extract_assets(settings)
		with open(settings.selected_map.folder_path.joinpath('exported.yo').__str__(), 'w') as out_file:
			out_file.write("")
		with open(settings.assets_path.joinpath('exported.yo').__str__(), 'w') as out_file:
			out_file.write("")

	else:
		umaps = get_files(
			path=settings.selected_map.umaps_path.__str__(), extension=".json")

	return umaps
# TODO : MATERIALS

	### WAITING ON HALF TO FIX .PSKS
def SetDecalMaterial(Set,MapObject):
	Set = Seting
	object_properties_OG = MapObject["Properties"]
	if "DecalMaterial" in object_properties_OG:
		yoyo = MapObject["Properties"]["DecalMaterial"]
		mat_name = get_obj_name(data=yoyo, mat=True)
		Mat = unreal.load_asset(f'/Game/ValorantContent/Materials/{mat_name}.{mat_name}')
		return Mat
	else: 
		return None

# SECTION : Set Material
def ReturnParent(parentName):
	rformPar =parentName.rfind(' ') + 1
	ActualName = parentName[rformPar:len(parentName)]
	DefEnv = ImportShader(ActualName)
	if not DefEnv:
		ParentName = "BaseEnv_MAT_V4"
	else:
		ParentName = ActualName
	return ParentName

def set_material(settings: Settings, UEMat,  mat_data: dict, override: bool = False, decal: bool = False, object_cls: MapObject = None):
	if "Properties" not in mat_data:
		return
	mat_props = mat_data["Properties"]
	if "Parent" in mat_props:
		mat_type = get_name(mat_props["Parent"]["ObjectPath"])
	else:
		mat_type = "NO PARENT"
	mat_props = mat_data["Properties"]
	mat_name = mat_data["Name"]

	SetTextures(mat_props,UEMat,mat_data)
	SetAllSettings(mat_props,UEMat)

	BasePropsBlacklist = ['bVertexFog','bOverride_DecalDiffuseLighting','bDecalDiffuseLighting','bDitherOpacityMask','DecalDiffuseLighting','LightingSourceDirectionality','bOverride_IndirectLightingContributionValue','IndirectLightingContributionValue','TranslucencyDepthMode','ShadingModel','bOverride_VertexFog','bOverride_CubemapSource','CubemapSource','bOverride_SortPriorityOffset','SortPriorityOffset','bOverride_Fresnel','bFresnel','bOverride_SpecularModel','SpecularModel','bSpecularModel','bOverride_CubemapMode','CubemapMode']
	if "BasePropertyOverrides" in mat_props:
		BasePropOverride = unreal.MaterialInstanceBasePropertyOverrides()
		if "TwoSided" in mat_props["BasePropertyOverrides"]:
			value = mat_props["BasePropertyOverrides"]["TwoSided"]
			BasePropOverride.set_editor_property('override_two_sided', True)
			BasePropOverride.set_editor_property('two_sided', value)
		if "BlendMode" in mat_props["BasePropertyOverrides"]:
			prop_value = mat_props["BasePropertyOverrides"]["BlendMode"]
			blend_mode = unreal.BlendMode.BLEND_OPAQUE
			if "BLEND_Translucent" in prop_value:
				unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(UEMat, 'BLENDTranslucent',True)
				blend_mode = unreal.BlendMode.BLEND_TRANSLUCENT
			elif "BLEND_Masked" in prop_value:
				blend_mode = unreal.BlendMode.BLEND_MASKED
			elif "BLEND_Additive" in prop_value:
				blend_mode = unreal.BlendMode.BLEND_ADDITIVE
			elif "BLEND_Modulate" in prop_value:
				blend_mode = unreal.BlendMode.BLEND_MODULATE
			elif "BLEND_AlphaComposite" in prop_value:
				blend_mode = unreal.BlendMode.BLEND_ALPHA_COMPOSITE
			elif "BLEND_AlphaHoldout" in prop_value:
				blend_mode = unreal.BlendMode.BLEND_BLEND_ALPHA_HOLDOUT
			BasePropOverride.set_editor_property('bOverride_BlendMode', True)
			BasePropOverride.set_editor_property('blend_mode', blend_mode)
		UEMat.set_editor_property('BasePropertyOverrides',BasePropOverride)
		unreal.MaterialEditingLibrary.update_material_instance(UEMat)

			#if prop_name not in BasePropsBlacklist:
			#	BasePropOverride = unreal.MaterialInstanceBasePropertyOverrides()
			#	BasePropOverride.set_editor_property(prop_name, prop_value)
	
	if "StaticParameters" in mat_props:
		if "StaticSwitchParameters" in mat_props["StaticParameters"]:
			for param in mat_props["StaticParameters"]["StaticSwitchParameters"]:
				param_name = param["ParameterInfo"]["Name"].lower()
				param_value = param["Value"]
				unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(UEMat, param_name,bool(param_value))
		if "StaticComponentMaskParameters" in mat_props["StaticParameters"]:
			for param in mat_props["StaticParameters"]["StaticComponentMaskParameters"]:
				listosa = ["R","G","B"]
				for pa in listosa:
					value = param[pa]
					unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(UEMat, pa,bool(value))
	if "ScalarParameterValues" in mat_props:
		for param in mat_props["ScalarParameterValues"]:
			param_name = param['ParameterInfo']['Name'].lower()
			param_value = param["ParameterValue"]
			SetMaterialScalarValue(UEMat,param_name,param_value)

	if "VectorParameterValues" in mat_props:
		for param in mat_props["VectorParameterValues"]:
			param_name = param['ParameterInfo']['Name'].lower()
			param_value = param["ParameterValue"]
			if param_name == "texture tint a":
				param_name = "layer a tint"
			if param_name == "texture tint b":
				param_name = "layer b tint"
			SetMaterialVectorValue(UEMat, param_name,get_rgb(param_value))


def ImportTexture(Path):
	if Path not in AllTextures:
		AllTextures.append(Path)

def SetTextures(mat_props: dict, MatRef, mat_data: dict):
	Set = Seting
	ImportedTexture = None
	set_switch_param = unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value
	set_texture_param = unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value
	if not (HasKey("TextureParameterValues",mat_props)):
		return
	if HasKey("VectorParameterValues",mat_props):
		vector_name = []
		for VectorParam in mat_props["VectorParameterValues"]:
			param_name = VectorParam['ParameterInfo']['Name'].lower()
			vector_name.append(param_name)

	for param in mat_props["TextureParameterValues"]:
		vector_name = []
		tex_game_path = get_texture_path(s=param, f=Set.texture_format)
		if not tex_game_path:
			continue
		tex_local_path = Set.assets_path.joinpath(tex_game_path).__str__()
		param_name = param['ParameterInfo']['Name'].lower()
		tex_name = Path(tex_local_path).stem
		
		if "diffuse b low" not in param_name:
			if Path(tex_local_path).exists():
				ImportedTexture = unreal.load_asset(f'/Game/ValorantContent/Textures/{tex_name}')
			if not ImportedTexture:
				continue
			if "diffuse" == param_name or "albedo" == param_name:
				MatParameterValue = set_texture_param(MatRef, 'Diffuse', ImportedTexture)
			if "diffuse a" == param_name  or "texture a" == param_name or "albedo a" == param_name:
				MatParameterValue = set_texture_param(MatRef, 'Diffuse A', ImportedTexture)
			if "diffuse b" == param_name  or "texture b" == param_name or "albedo b" == param_name:
				MatParameterValue = set_texture_param(MatRef, 'Diffuse B', ImportedTexture)
			if  "texture a normal" == param_name or "normal a" == param_name:
				MatParameterValue = set_texture_param(MatRef, 'Texture A Normal', ImportedTexture)
			if  "texture b normal" == param_name or "normal b" == param_name:
				MatParameterValue = set_texture_param(MatRef, 'Texture B Normal', ImportedTexture)
			if "mask" in param_name or "Mask Textuer" in param_name or "Mask Texture" in param_name:
				MatParameterValue = set_texture_param(MatRef, 'Mask Textuer', ImportedTexture)
			if "mask" in param_name or "rgba" in param_name:
				pass
			set_texture_param(MatRef, param_name, ImportedTexture)

	if HasKey("TextureParameterValues",mat_props):
		texture_name = []
		for TextureParam in mat_props["TextureParameterValues"]:
			param_name = TextureParam['ParameterInfo']['Name'].lower()
			texture_name.append(param_name)
	mat_name = mat_data["Name"]
	if "diffuse a" in texture_name:
		if "diffuse b" not in texture_name:
			if "Wood_M15" in mat_name or "Stone_M0_SquareTiles" in mat_name:
				set_switch_param(MatRef, 'WoodFix',True)

	unreal.MaterialEditingLibrary.update_material_instance(MatRef)

def SetAllSettings(asset,Comp):
	blackmisc = ["CachedMaxDrawDistance","OnComponentBeginOverlap","Mobility"]
	if not asset:
		return
	for Setting in asset:
		bHasIt = HasSetting(Setting,Comp,blackmisc)
		if bHasIt:
			ActorSetting = asset[Setting]
			try:
				PropSet = Comp.get_editor_property(Setting)
			except:
				continue
			classname = GetClassName(PropSet)
			if type(ActorSetting) == int or type(ActorSetting) == float or type(ActorSetting) == bool :
				try:
					Comp.set_editor_property(Setting, ActorSetting)
					continue
				except:
					print(f'UianaLog: {Setting} could not be set')
					continue
			if type(ActorSetting) == str:
				ActorSetting = ActorSetting.upper()
			if "::" in ActorSetting:
				ActorSetting = ReturnFormattedString(ActorSetting,":")
			if classname == "Color":
				Colorized = unreal.Color(r=ActorSetting['R'], g=ActorSetting['G'], b=ActorSetting['B'], a=ActorSetting['A'])
				Comp.set_editor_property(Setting, Colorized)
				continue
			if type(ActorSetting) == dict:
				if Setting == "StaticMesh":
					MeshLoadable = ConvertToLoadableUE(ActorSetting,"StaticMesh ","Meshes")
					Comp.set_editor_property('static_mesh',MeshLoadable)
					#ActorSetting[""]
				if Setting == "BoxExtent":
					Comp.set_editor_property("box_extent",unreal.Vector(ActorSetting["X"],ActorSetting["Y"],ActorSetting["Z"]))
				if Setting == "LightmassSettings":
					ReturnLMass = None
					### gotta fix later
					if type(Comp) == unreal.MaterialInstanceConstant:
						ReturnLMass = SetLightmassSetting(ActorSetting,"LightmassMaterialInterfaceSettings")
						continue
					if type(Comp) == unreal.DirectionalLightComponent or type(Comp) == unreal.SpotLightComponent:
						ReturnLMass = SetLightmassSetting(ActorSetting,"LightmassDirectionalLightSettings")
						continue
					if type(Comp) == unreal.PointLightComponent:
						ReturnLMass = SetLightmassSetting(ActorSetting,"LightmassPointLightSettings")
						continue
					if type(Comp) == unreal.StaticMeshComponent or type(Comp) == unreal.HierarchicalInstancedStaticMeshComponent:
						ReturnLMass = SetLightmassSetting(ActorSetting,"LightmassPrimitiveSettings")
					if not ReturnLMass:
						continue
					Comp.set_editor_property("lightmass_settings",ReturnLMass)
					continue
				continue
			ActualValue = FindNonSlasher(eval(f'unreal.{classname}'),ActorSetting)
			if not ActualValue:
				continue
			value = eval(f'unreal.{classname}.{ActualValue}')
			Comp.set_editor_property(Setting, value)
def SetLightmassSetting(ActorSetting,Evalu):
	Set = eval(f'unreal.{Evalu}()')
	BlacklistLMass = ["bCastShadowAsTranslucent","bOverrideCastShadowAsTranslucent","MaskedTranslucentOpacity","bOverrideMaskedTranslucentOpacity","bLightAsBackFace","bUseTwoSidedLighting"]
	for val in ActorSetting:
		if val in BlacklistLMass:
			continue
		num = 1
		if val.startswith("b"):
			num = 2
		newstr = re.sub('([A-Z])', r'_\1', val)
		try:
			Set.set_editor_property(newstr[num:len(newstr)].lower(),ActorSetting[val])
		except:
			print(f'Property LightMass {newstr[num:len(newstr)].lower()} doesnt exist')
	return Set

	#################### Spawners
def ImportLights(OBJData, ArrObjsImport):
	ActorInfo = ActorDefs(OBJData)
	PostProcessSettings = []
	LightTypeNoComp = ActorInfo.type.replace("Component","")
	LightType = eval(f'unreal.{LightTypeNoComp}')
			########SpawnLightAndGetReferenceForComp#######
	if not ActorInfo.transform:
		return
	LightActor = unreal.EditorLevelLibrary.spawn_actor_from_class(LightType, ActorInfo.transform.translation, ActorInfo.transform.rotation.rotator())
	LightActor.set_folder_path(f'Lights/{LightTypeNoComp}')
	LightActor.set_actor_label(ActorInfo.name)
	LightActor.set_actor_scale3d(ActorInfo.transform.scale3d )
	if hasattr(LightActor,"light_component"):
		CompToUse = LightActor.light_component
	elif  hasattr(LightActor,"portal_component"):
		CompToUse = LightActor.portal_component
	elif hasattr(LightActor,"scene_component"):
		CompToUse = LightActor.scene_component
	elif hasattr(LightActor,"settings"):
		LightActor.set_editor_property("Unbound", True)
		LightActor.set_editor_property("Priority",1.0)
		CompToUse = LightActor.settings
	elif hasattr(LightActor,"capture_component"):
		CompToUse = LightActor.capture_component
	elif hasattr(LightActor,"component") == False:
		CompToUse = LightActor
	else:
		CompToUse = LightActor.component 
	#Figure out Mobility
	Mobility = unreal.ComponentMobility.STATIC
	LightActor.modify()
	if HasKey("Settings",ActorInfo.props) :
		PostProcessSettings = ActorInfo.props["Settings"]
		SetPostProcessSettings(PostProcessSettings,CompToUse)
	for Setting in ActorInfo.props:
		LightSetting = ActorInfo.props[Setting]
		if Setting == "IESTexture":
			CompToUse.set_editor_property('IESTexture',SetIesTexture(LightSetting))
		if Setting == "Cubemap":
			CompToUse.set_editor_property('Cubemap',SetCubeMapTexture(LightSetting))
		if Setting == "LightColor":
			Colorized = unreal.Color(r=LightSetting['R'], g=LightSetting['G'], b=LightSetting['B'], a=LightSetting['A'])
			CompToUse.set_editor_property('LightColor',Colorized)
		if Setting == "FogInscatteringColor":
			Colorized = unreal.LinearColor(r=LightSetting['R'], g=LightSetting['G'], b=LightSetting['B'], a=LightSetting['A'])
			CompToUse.set_editor_property('fog_inscattering_luminance',Colorized)
		if Setting == "Mobility":
			CompToUse.set_editor_property('Mobility',Mobility)
	SetAllSettings(ActorInfo.props,CompToUse)


	############## to pass it to c++ we need to make a data asset that withholds all data from the umaps.
def ImportDecal(DecalData):
	ActorInfo = ActorDefs(DecalData)
	if not ActorInfo.transform:
		return
	DecActor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DecalActor,ActorInfo.transform.translation,ActorInfo.transform.rotation.rotator())
	DecActor.set_folder_path(f'Decals')
	DecActor.set_actor_scale3d(ActorInfo.transform.scale3d)
	DecalComponent = DecActor.decal
	DecalMat = SetDecalMaterial(Settings, DecalData)
	DecalComponent.set_decal_material(DecalMat)
	BlacklistDecal =  ['DecalMaterial','LightColorType','CachedVertexFogIntensityFromVolumes','bVertexFog','bOverrideColor','bOverrideIntensity','DetailMode','VisibilityId','bAllowCullingWhenFacingCamera','LightColorOverride','LightIntensityOverride','LightingSourceDirectionality','bOverride_IndirectLightingContributionValue','IndirectLightingContributionValue','TranslucencyDepthMode','ShadingModel','bOverride_VertexFog','bOverride_CubemapSource','CubemapSource','bOverride_SortPriorityOffset','SortPriorityOffset','bOverride_Fresnel','bFresnel','bOverride_SpecularModel','SpecularModel','bSpecularModel','bOverride_CubemapMode','CubemapMode']
	for propName,PropValue in ActorInfo.props.items():
		if propName not in BlacklistDecal:
			SetAllSettings(DecalData,DecalComponent)

def FixActorBP(MData):
	try:
		CompToUse = unreal.BPFL.get_component_by_name(AllBps[MData.outer],MData.name)
	except:
		return
	if not CompToUse:
		return
	if HasKey("StaticMesh",MData.props):
		MeshToLoad = ConvertToLoadableUE(MData.props["StaticMesh"],"StaticMesh ","Meshes")
		CompToUse.set_editor_property('static_mesh',MeshToLoad)
	if HasKey("OverrideMaterials",MData.props):
		if not Seting.import_materials:
			return
		MatOver = GetMaterialToOverride(MData.data)
		if MatOver:
			unreal.BPFL.set_override_material(AllBps[MData.outer],MData.name,MatOver)
	if not HasKey("AttachParent",MData.props):
		return
	Transform = GetTransform(MData.props)
	#CompToUse.set_relative_transform(Transform,False,False)
	CompToUse.set_editor_property('relative_scale3d',Transform.scale3d)
	CompToUse = unreal.BPFL.get_component_by_name(AllBps[MData.outer],MData.name)
	CompToUse.set_editor_property('relative_location',Transform.translation)
	CompToUse = unreal.BPFL.get_component_by_name(AllBps[MData.outer],MData.name)
	CompToUse.set_editor_property('relative_rotation',Transform.rotation.rotator())
def ImportMesh(MeshData,MapObj):
	MeshActor = ActorDefs(MeshData)
	if HasKey("Template",MeshActor.data):
		FixActorBP(MeshActor)
		return
	OvrVertexes = []
	HasVCol = False
	if not HasKey("StaticMesh",MeshActor.props):
		return
	Transform = GetTransform(MeshActor.props)
	if type(Transform) == bool:
		Transform = GetTransform(MeshActor.props)
	if not Transform:
		return
	UnrealMeshType = unreal.StaticMeshActor
	if MapObj.is_instanced():
		UnrealMeshType = unreal.HismActor
	SMActor = unreal.EditorLevelLibrary.spawn_actor_from_class(UnrealMeshType,location=unreal.Vector(), rotation = unreal.Rotator())
	SMActor.set_actor_label(MeshActor.outer)
	SMActor.set_actor_scale3d(Transform.scale3d)
	PathOriginal = GetActualPath(MeshActor.props["StaticMesh"])
	if HasKey("LODData",MeshActor.data):
		OvrVertexes = GetOverrideVertexColor(MeshActor.data)
	if MapObj.is_instanced():
		instance_data = MeshActor.data["PerInstanceSMData"]
		Instance = SMActor.hism_component
		SetAllSettings(MeshActor.props,Instance)
		Instance.set_world_transform(Transform,False,False)
		SMActor.set_folder_path(f'Meshes/Instanced')
		for inst in instance_data:
			Trans = GetTransform(inst)
			if not Trans:
				return
			Instance.add_instance(Trans)
		if len(OvrVertexes) > 0:
			unreal.BPFL.paint_sm_vertices(Instance,OvrVertexes,PathOriginal)
	else:
		Instance = SMActor.static_mesh_component
		SetAllSettings(MeshActor.props,Instance)
		Instance.set_world_transform(Transform,False,False)
		FolderName = 'Meshes/Static'
		if MapObj.umap.endswith("_VFX"):
			FolderName = 'VFX/Meshes'
		SMActor.set_folder_path(FolderName)
		if len(OvrVertexes) > 0:
			unreal.BPFL.paint_sm_vertices(Instance,OvrVertexes,PathOriginal)
	##SetTransform(Instance,Transform)
	if HasKey("OverrideMaterials",MeshActor.props):
		if not Seting.import_materials:
			return
		MatOver = GetMaterialToOverride(MeshActor.data)
		if MatOver:
			Instance.set_editor_property('override_materials',MatOver)
def SetTransform(inst,TForm):
	inst.set_editor_property('relative_scale3d',TForm.scale3d)
	inst.set_editor_property('relative_location',TForm.translation)
	inst.set_editor_property('relative_rotation',TForm.rotation.rotator())
def SetSMSettings(settings: Settings):
	Mult = settings.manual_lmres_mult
	OBJPath = Seting.selected_map.objects_path
	### first normal mats #######
	ListObjs = os.listdir(OBJPath)
	for obj in ListObjs:
		Join = OBJPath.joinpath(obj)
		ObjJson = read_json(Join)
		sm = ObjJson
		for sm in ObjJson:
			if HasKey("Outer",sm):
				Outer = sm["Outer"]
			if sm["Type"] == "StaticMesh":
				Props = sm["Properties"]
				Name = sm["Name"]
				LmCoord = 0
				LMRes = LMRes = round(256*Mult/4)*4 								#multiple of 4
				#########Set LightMapSettings
				if HasKey("LightMapResolution",Props):
					LMRes = round(Props["LightMapResolution"]*Mult/4)*4 	#multiple of 4
				if HasKey("LightMapCoordinateIndex",Props):
					LmCoord = Props["LightMapCoordinateIndex"]
				MeshToLoad = unreal.load_asset(f"/Game/ValorantContent/Meshes/{Name}")
				if (MeshToLoad):
					CastSM = unreal.StaticMesh.cast(MeshToLoad)
					CastSM.set_editor_property("light_map_coordinate_index", LmCoord)
					CastSM.set_editor_property("light_map_resolution", LMRes)
			########### Set BodyCollision
			if sm["Type"] == "BodySetup":
				PropsBody = sm["Properties"]
				if HasKey("CollisionTraceFlag",PropsBody):
					ColTrace = re.sub('([A-Z])', r'_\1', PropsBody["CollisionTraceFlag"])
					MeshToLoad = unreal.load_asset(f"/Game/ValorantContent/Meshes/{Outer}")
					if (MeshToLoad):
						CastSM = unreal.StaticMesh.cast(MeshToLoad)
						BSetup =  CastSM.get_editor_property("body_setup")
						strcollision = 'CTF_' + ColTrace[8:len(ColTrace)].upper()
						BSetup.set_editor_property("collision_trace_flag", eval(f'unreal.CollisionTraceFlag.{strcollision}'))
						CastSM.set_editor_property("body_setup", BSetup)

###### end spawners
def import_umap(settings: Settings, umap_data: dict, umap_name: str):
	map_object = None
	test = []
	objectsToImport = filter_objects(umap_data)
	skip = 0
	for objectIndex, object_data in enumerate(objectsToImport):
		object_type = get_object_type(object_data)
		if object_type == "blueprint" and settings.import_blueprints:
			if skip < 2:
				skip += 1
				continue
			ImportBP(object_data,objectsToImport)
	for objectIndex, object_data in enumerate(objectsToImport):
		objectIndex = f"{objectIndex:03}"
		object_type = get_object_type(object_data)
		if object_type == "mesh" and settings.import_Mesh:
			#if "Lighting" not in umap_name:
			map_object = MapObject(settings=settings, data=object_data, umap_name=umap_name,umap_data=umap_data)
			ImportMesh(object_data,map_object)
		if object_type == "decal" and settings.import_decals:
			ImportDecal(object_data)
		if object_type == "light" and settings.import_lights:
			ImportLights(object_data,objectsToImport)
def LevelStreamingStuff():
	world = unreal.EditorLevelLibrary.get_editor_world()
	for j in AllLevelPaths:
		JAfterSlash = ReturnFormattedString(j,"/")
		MapType = GetUMapType(JAfterSlash)
		unreal.EditorLevelUtils.add_level_to_world(world, j, MapType)
		ReadableMapType = GetReadableUMapType(JAfterSlash)
		if ReadableMapType == "LevelStreamingDynamic":
			SubSys = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
			Level2 = unreal.LevelEditorSubsystem.get_current_level(SubSys)
			unreal.EditorLevelUtils.set_level_visibility(Level2,False,False)
# ANCHOR: Functions
def SetPostProcessSettings(AllSettings,Comp):
	for Setting in AllSettings:
		bekaBlackList=["SavedSelections","bOverride_AresAdaptiveSharpenEnable","FilmContrast","bOverride_AmbientOcclusionTintColor","AmbientOcclusionTintColor","bOverride_FilmContrast","bOverride_AutoExposureBiasBackup","FilmWhitePoint","bOverride_FilmWhitePoint","AutoExposureBiasBackup","bOverride_AresClarityEnable","bOverride_IndirectLightingScaleCurve","IndirectLightingScaleCurve","bOverride_ScreenPercentage","ScreenPercentage"]
		if Setting not in bekaBlackList:
			ResultValue = AllSettings[Setting] 
			CompSet = type(Comp.get_editor_property(Setting))
			if CompSet == unreal.LinearColor:
				ResultValue = unreal.LinearColor(ResultValue["R"],ResultValue["G"],ResultValue["B"],ResultValue["A"])
			if CompSet == unreal.Color:
				ResultValue = unreal.Color(ResultValue["R"],ResultValue["G"],ResultValue["B"],ResultValue["A"])
			Comp.set_editor_property(Setting, ResultValue)
			Comp.set_editor_property("override_ambient_occlusion_intensity", True)
			Comp.set_editor_property("ambient_occlusion_intensity", 0)
def ImportBP(bpdata,umapdata):
	BPActor = ActorDefs(bpdata)
	Transform = GetTransform(BPActor.props)
	if not HasTransform(BPActor.props):
		Transform = GetAttachScene(BPActor.data,BPActor.outer,umapdata)
	if type(Transform) == bool:
		Transform = GetTransform(BPActor.props)
	if not Transform:
		return
	BPName = BPActor.type[0:len(BPActor.type)-2]
	BPObject = unreal.load_asset(f"/Game/ValorantContent/Blueprints/{BPName}.{BPName}")
	BP = unreal.EditorLevelLibrary.spawn_actor_from_object(BPObject,Transform.translation,Transform.rotation.rotator())
	if not BP:
		return
	AllBps[BPActor.name] = BP
	BP.set_actor_label(BPActor.name)
	BP.set_actor_scale3d(Transform.scale3d)
def CreateNewLevel(mapname):
	newmap = GetInitialName(mapname)
	startpath = f"/Game/ValorantContent/Maps/{newmap}/{mapname}"
	bLoaded =unreal.load_asset(startpath)
	SubSystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
	unreal.LevelEditorSubsystem.new_level(SubSystem,startpath)
	AllLevelPaths.append(startpath)
def GetOverrideVertexColor(data):
	vtxarray = []
	Lod = data["LODData"]
	for itLod in Lod:
		if HasKey("OverrideVertexColors",itLod):
			DataToConvert = itLod["OverrideVertexColors"]["Data"]
			for rgba_hex in DataToConvert:
				Color = unreal.BPFL.return_from_hex(rgba_hex)
				vtxarray.append(Color)
	return vtxarray
def GetActualPath(name):
	pathe = name["ObjectPath"]
	rfindpoint = pathe.rfind('.') 
	fixexportdir =str(Seting.export_path) +'\\export\\Game'
	fixedName = pathe[0:rfindpoint].replace("ShooterGame/Content",fixexportdir) + '.pskx'
	windowsfix = fixedName.replace("/","\\")
	return windowsfix
def ImportAllTexturesFromMaterial(matJson):
	for node in matJson:
		if HasKey("Properties",node):
			props = node["Properties"]
			if HasKey("TextureParameterValues",props):
				TextParamValues = props["TextureParameterValues"]
				for param in TextParamValues:
					tex_game_path = get_texture_path(s=param, f=Seting.texture_format)
					if not tex_game_path:
						continue
					tex_local_path = Seting.assets_path.joinpath(tex_game_path).__str__()
					param_name = param['ParameterInfo']['Name'].lower()
					tex_name = Path(tex_local_path).stem
					if tex_local_path not in AllTextures:
						AllTextures.append(tex_local_path)
def CreateMaterial(mat):
	mat_data = mat[0]
	mat_name = mat_data["Name"]
	ParentToImport = "None"
	MatProps = None
	if HasKey("Properties",mat_data):
		MatProps = mat_data["Properties"]
	Mat = unreal.load_asset(f'/Game/ValorantContent/Materials/{mat_name}.{mat_name}')
	if Mat is not None:
		if HasKey("Parent",MatProps):
			ParentToImport = ReturnParent(MatProps["Parent"]["ObjectName"])
		Mat = unreal.MaterialInstanceConstant.cast(Mat)
		MatBase = ImportShader(ParentToImport)
		Parent = Mat.set_editor_property('parent', MatBase)
	else:
		Mat = AssetTools.create_asset(mat_name,'/Game/ValorantContent/Materials/', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
		Mat = unreal.MaterialInstanceConstant.cast(Mat)
		ParentToImport = "BaseEnv_MAT_V4"
		if HasKey("Parent",MatProps):
			ParentToImport = ReturnParent(MatProps["Parent"]["ObjectName"])
		MatBase = ImportShader(ParentToImport)
		Mat.set_editor_property('parent', MatBase)

	if mat_name not in LoadableMaterials:
		LoadableMaterials[mat_name] = Mat
	set_material(settings=Settings,  mat_data=mat_data, object_cls=None,UEMat = Mat )
	######################## Initial Importers func
def ExportAllMeshes():
	OBJPath = Seting.selected_map.folder_path.joinpath(f"_assets_objects.txt")
	with open(OBJPath,'r') as file1:
		Lines = file1.read().splitlines() 
	ExpPath = str(Seting.assets_path)
	for line in Lines:
		if is_blacklisted(line[line.rfind("\\")+1:len(line)]):
			continue
		linearr = line.split("\\")
		if linearr[0] == "Engine":
			continue
		else:
			linearr.pop(0)
			linearr.pop(0)
		JoinedLinesBack = "\\".join(linearr)
		FullPath = ExpPath + '\\Game\\' + JoinedLinesBack + ".pskx"
		if FullPath not in AllMeshes:
			AllMeshes.append(FullPath)
	# import 
	unreal.BPFL.import_meshes(AllMeshes,str(Seting.selected_map.objects_path))
def ExportAllTextures():
	MatPath = Seting.selected_map.materials_path
	MatOverridePath = Seting.selected_map.materials_ovr_path

	### first normal mats #######
	listMatPath = os.listdir(MatPath)
	for pathzin in listMatPath:
		bago = MatPath.joinpath(pathzin)
		MatJson = read_json(bago)
		ImportAllTexturesFromMaterial(MatJson)
	   ########## mat ovverrides##############
	listOverridePath = os.listdir(MatOverridePath)
	for pathovr in listOverridePath:
		entireovrpath = MatOverridePath.joinpath(pathovr)
		MatJson = read_json(entireovrpath)
		ImportAllTexturesFromMaterial(MatJson)
	unreal.BPFL.import_textures(AllTextures)
def CreateBP(FullData,BPName):
	BlacklistBP = ['SpawnBarrier','SoundBarrier','SpawnBarrierProjectile','Gumshoe_CameraBlockingVolumeParent_Box','DomeBuyMarker','BP_StuckPickupVolume','BP_LevelBlockingVolume','BP_TargetingLandmark','BombSpawnLocation']
	BPName = BPName.replace(".json","")
	Actor = unreal.load_asset(f'/Game/ValorantContent/Blueprints/{BPName}')
	if not Actor and BPName not in BlacklistBP :
		Actor = AssetTools.create_asset(BPName,'/Game/ValorantContent/Blueprints/', unreal.Blueprint, unreal.BlueprintFactory())
	else:
		return
	data = FullData["Nodes"]
	if len(data) == 0:
		print(f'UianaBPLog: {BPName} didnt have any comps')
		return
	RootScene = FullData["SceneRoot"]
	DefaultSceneRoot = RootScene[0][RootScene[0].rfind('.') + 1:len(RootScene[0])]
	GameObjects = FullData["GameObjects"]
	NodesRoot = FullData["ChildNodes"]
	for idx,BPC in enumerate(data):
		if BPC["Name"] == DefaultSceneRoot:
			del data[idx]
			data.insert(len(data),BPC)
			break
	data.reverse()
	NodesArray = []
	for smbp in data:
		if smbp["Name"] in NodesRoot:
			continue
		ComponentName = smbp["Properties"]["ComponentClass"]["ObjectName"].replace("Class ","")
		try:
			uClass = eval(f'unreal.{ComponentName}')
		except:
			continue
		Props = smbp["Properties"]
		if HasKey("ChildNodes",Props):
			NodesArray = HandleChildNodes(Props["ChildNodes"],data,Actor)
		compnamefix = smbp["Properties"]["InternalVariableName"]
		Compon = unreal.BPFL.create_bp_comp(Actor,uClass,compnamefix,NodesArray)
		if HasKey("Properties",smbp):
			SMProps = smbp["Properties"]["CompProps"]
			SetAllSettings(SMProps,Compon)
			if not SMProps:
				continue
		SetMeshSettings(SMProps,Compon)
	for GObject in GameObjects:
		uClass = unreal.StaticMeshComponent
		Compon = unreal.BPFL.create_bp_comp(Actor,uClass,"GameObjectMesh",NodesArray)
		SetMeshSettings(GObject["Properties"],Compon)
def SetMeshSettings(smbpProps,Comp):
	SetAllSettings(smbpProps,Comp)
	Transform = GetTransform(smbpProps)
	if HasKey("RelativeRotation",smbpProps):
		Comp.set_editor_property('relative_rotation',Transform.rotation.rotator())
	if HasKey("RelativeLocation",smbpProps):
		Comp.set_editor_property('relative_location',Transform.translation)
	if HasKey("RelativeScale3D",smbpProps):
		Comp.set_editor_property('relative_scale3d',Transform.scale3d)
	if HasKey("StaticMesh",smbpProps):
		if smbpProps["StaticMesh"] == None:
			return
def HandleChildNodes(ArrayCN,EntireArray,BPActor):
	LocalChildArray = []
	for ChildNode in ArrayCN:
		ChildObjectName = ChildNode["ObjectName"]
		ChildName = ChildObjectName[ChildObjectName.rfind('.')+1:len(ChildObjectName)]
		for CNode in EntireArray:
			NodeName = CNode["Name"]
			ComponentName = CNode["Properties"]["ComponentClass"]["ObjectName"].replace("Class ","")
			try:
				uClass = eval(f'unreal.{ComponentName}')
			except:
				continue
			InternalName = CNode["Properties"]["InternalVariableName"]
			if "TargetViewMode" in InternalName:
				continue
			if NodeName == ChildName:
				UNode,ComponentNode = unreal.BPFL.create_node(BPActor,uClass,InternalName)
				LocalChildArray.append(UNode)
				SetAllSettings(CNode["Properties"]["CompProps"],ComponentNode)
				#print(f'UNode : {type(UNode)}')
				break
	return LocalChildArray


def ExportAllBlueprints():
	BPath = Seting.selected_map.actors_path
	ListBPath = os.listdir(BPath)
	for bp in ListBPath:
		NewBPath = BPath.joinpath(bp)
		BPJson = ReduceBPJson(read_json(NewBPath))
		CreateBP(BPJson,bp)
def ExportAllMaterials():
	MatPath = Seting.selected_map.materials_path
	MatOverridePath = Seting.selected_map.materials_ovr_path

	### first normal mats #######
	listMatPath = os.listdir(MatPath)
	for pathzin in listMatPath:
		bago = MatPath.joinpath(pathzin)
		MatJson = read_json(bago)
		CreateMaterial(MatJson)
	   ########## mat ovverrides##############
	listOverridePath = os.listdir(MatOverridePath)
	for pathovr in listOverridePath:
		entireovrpath = MatOverridePath.joinpath(pathovr)
		MatJson = read_json(entireovrpath)
		CreateMaterial(MatJson)

################# Initial Main Function
def import_map(Setting):
	unreal.BPFL.change_project_settings()
	unreal.BPFL.execute_console_command('r.DefaultFeature.LightUnits 0')
	unreal.BPFL.execute_console_command('r.DynamicGlobalIlluminationMethod 0')
	AllLevelPaths.clear()
	settings = Settings(Setting)
	global Seting
	Seting = settings
	umap_json_paths = get_map_assets(Seting)
	if not Seting.import_sublevel:
		CreateNewLevel(settings.selected_map.name)
	ClearLevel()
	#  Check if the game files are exported
	######### export all textures before ###########
	if (Seting.import_materials ):
		txttime = time.time()
		ExportAllTextures()
		print("--- %s seconds to create textures ---" % (time.time() - txttime))
		start_time = time.time()
		ExportAllMaterials()
		print("--- %s seconds to create materials  ---" % (time.time() - start_time))
	Mstart_time = time.time()
	if Seting.import_Mesh:
		ExportAllMeshes()
	print("--- %s seconds to create meshes ---" % (time.time() - Mstart_time))
	if Seting.import_blueprints:
		ExportAllBlueprints()
	###### above takes 0.09 might fix #######
	umap_json_path: Path
	Ltart_time = time.time()
	for index, umap_json_path in reversed(list(enumerate(umap_json_paths))):
		umap_data = read_json(umap_json_path)
		umap_name = umap_json_path.stem
		if Seting.import_sublevel :
			CreateNewLevel(umap_name)
		import_umap(settings=settings, umap_data=umap_data, umap_name=umap_name)
		if Seting.import_sublevel :
			unreal.EditorLevelLibrary.save_current_level()
	if Seting.import_sublevel :
		LevelStreamingStuff()
	SetSMSettings(settings)
	print("--- %s seconds to spawn actors ---" % (time.time() - Ltart_time))
	winsound.Beep(26000, 1500)