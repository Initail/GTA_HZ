import {createCitySitePaths} from './city-site-path-view.ts';
import {COMPATIBLE_CITY_RANGE} from './city-stream-profile.ts';
import './city-engine-registration.ts';
import {CAR_BODY,sweepVehicleContact,vehicleImpulse,vehicleBlocksPoint,type VehicleBody} from './city-vehicle-contact.ts';
import {CITY_COPY} from './city-copy.ts';
import {roadAllows,type TravelMode} from './road-access.ts';
import {CITY_CONFIG,cityAssetUrl,assertCityAssetIdentity} from './city-config.ts';
import {CITY_GRAPHICS_PROFILES,cityGraphicsRenderRatio,isCityGraphicsQuality,loadCityGraphicsQuality,saveCityGraphicsQuality,type CityGraphicsQuality} from './city-graphics-quality.ts';
import {createVehicleReflections} from './city-vehicle-reflections.ts';
import {headlightAnchors,type VehicleManifest} from './city-vehicle-manifest.ts';
import {Engine} from '@babylonjs/core/Engines/engine.js';
import {Scene} from '@babylonjs/core/scene.js';
import {Vector3,Quaternion,Matrix} from '@babylonjs/core/Maths/math.vector.js';
import {Color3,Color4} from '@babylonjs/core/Maths/math.color.js';
import {FreeCamera} from '@babylonjs/core/Cameras/freeCamera.js';
import {HemisphericLight} from '@babylonjs/core/Lights/hemisphericLight.js';
import {DirectionalLight} from '@babylonjs/core/Lights/directionalLight.js';
import {ShadowGenerator} from '@babylonjs/core/Lights/Shadows/shadowGenerator.js';
import {TransformNode} from '@babylonjs/core/Meshes/transformNode.js';
import {MeshBuilder} from '@babylonjs/core/Meshes/meshBuilder.js';
import {Mesh} from '@babylonjs/core/Meshes/mesh.js';
import {StandardMaterial} from '@babylonjs/core/Materials/standardMaterial.js';
import {PBRMaterial} from '@babylonjs/core/Materials/PBR/pbrMaterial.js';
import {RawCubeTexture} from '@babylonjs/core/Materials/Textures/rawCubeTexture.js';
import {RawTexture} from '@babylonjs/core/Materials/Textures/rawTexture.js';
import {Texture} from '@babylonjs/core/Materials/Textures/texture.js';
import {DynamicTexture} from '@babylonjs/core/Materials/Textures/dynamicTexture.js';
import {Effect} from '@babylonjs/core/Materials/effect.js';
import {ShaderMaterial} from '@babylonjs/core/Materials/shaderMaterial.js';
import {PointLight} from '@babylonjs/core/Lights/pointLight.js';
import {ImportMeshAsync} from '@babylonjs/core/Loading/sceneLoader.js';
import {DefaultRenderingPipeline} from '@babylonjs/core/PostProcesses/RenderPipeline/Pipelines/defaultRenderingPipeline.js';
import {MirrorTexture} from '@babylonjs/core/Materials/Textures/mirrorTexture.js';
import {Plane} from '@babylonjs/core/Maths/math.plane.js';
import {FresnelParameters} from '@babylonjs/core/Materials/fresnelParameters.js';
import {SpotLight} from '@babylonjs/core/Lights/spotLight.js';
import {MeshoptCompression} from '@babylonjs/core/Meshes/Compression/meshoptCompression.js';
import {SSAO2RenderingPipeline} from '@babylonjs/core/PostProcesses/RenderPipeline/Pipelines/ssao2RenderingPipeline.js';
import {Constants} from '@babylonjs/core/Engines/constants.js';
import {SceneInstrumentation} from '@babylonjs/core/Instrumentation/sceneInstrumentation.js';
import {EngineInstrumentation} from '@babylonjs/core/Instrumentation/engineInstrumentation.js';
import {RenderingGroup} from '@babylonjs/core/Rendering/renderingGroup.js';
import {Frustum} from '@babylonjs/core/Maths/math.frustum.js';
import {type SubMesh} from '@babylonjs/core/Meshes/subMesh.js';
import {type AbstractMesh} from '@babylonjs/core/Meshes/abstractMesh.js';
import '@babylonjs/loaders/glTF';
import './city-gltf-streaming.ts';
MeshoptCompression.Configuration={decoder:{url:cityAssetUrl("meshopt_decoder.js")}};
import {loadLandmarkDetails,loadLandmarkCandidates,isCandidateGroundSlab,type LandmarkDetailManifest,type LandmarkCandidateManifest} from './landmark-details.ts';
import {CityObserver} from './city-observer.ts';
import {CityFlight} from './city-flight.ts';
import {observerNearClip} from './city-observer-depth.ts';
import {CityBicycle,BICYCLE_BODY,type BicycleSurface} from './city-bicycle.ts';
import {CityBicycleParking} from './city-bicycle-parking.ts';
import {CityWalk} from './city-walk.ts';
import {CityLeisureSession} from './city-leisure-session.ts';
import {CityLeisureWater} from './city-leisure-water.ts';
import {createCityLeisureView,type CityLeisureSite} from './city-leisure-view.ts';
import {CityTank} from './city-tank.ts';
import {stepTank,tankFootprintClear} from './city-tank-simulation.ts';
import {createCityRider,type CityRider} from './city-rider.ts';
import {loadRoadDisplayNames,roadDisplayName} from './city-road-names.ts';
import {CityFacadeStream} from './city-facade-stream.ts';
import {createArchitectureMaterials} from './city-architecture-materials.ts';
import {createFacadeDiversity} from './city-facade-diversity.ts';
import {CityLandscape,applyLandscapeSurfaces} from './city-landscape.ts';
import {CityCanopy} from './city-canopy.ts';
import {CityRooftops} from './city-rooftops.ts';
import {createRoofSurface} from './city-roof-surface.ts';
import {createCityAmbient} from './city-ambient-occlusion.ts';
import {attachCityBuildingSigns} from './city-building-signs.ts';
import {loadLandmarkSignage} from './landmark-signage.ts';
import {createCinematicLook,syncPostChain,applyAntiAliasing,applyCityLightBalance} from './city-cinematic.ts';
import {keepSkyInReflections} from './city-sky-reflection.ts';
import {createBambooLook} from './city-bamboo-look.ts';
import {createBambooCafe} from './city-bamboo-cafe.ts';
import {createBayparkLook} from './city-baypark-look.ts';
import {createLocalLighting} from './city-local-lighting.ts';
import {applyCinematicRoad} from './city-road-surface.ts';
import {createRainPuddles} from './city-rain-puddles.ts';
import {createCityRainWeather,CITY_WEATHER_LABELS,type CityWeather} from './city-rain-weather.ts';
import {loadCityGroundRelief} from './city-ground-relief.ts';
import {loadCityMountains} from './city-mountains.ts';
import {loadCityGeography} from './city-geography.ts';
import type {RoadHeightHint} from './city-road-levels.ts';
import {loadCityJsonChunks,type CityJsonSource} from './city-json-chunks.ts';
import {CityBaseStream,type BaseStreamSources} from './city-base-stream.ts';
import {CityBaseMaterialCache} from './city-stream-ownership.ts';
import type {BaseStreamTile} from './city-stream-assets.ts';
import type {BasePackRecord,BasePackMetadata} from './city-stream-pack-manifest.ts';
import type {AssetContainer} from '@babylonjs/core/assetContainer.js';
import {applyCinematicVehicleFinish} from './city-vehicle-finish.ts';
import {refineHeroVehicleMaterials} from './city-vehicle-materials.ts';
import {CityAudio} from './city-audio.ts';
import {CityAutopilot,type DrivingInput} from './city-autopilot.ts';
import {createCityCockpit,CITY_DRIVER_POSE} from './city-cockpit.ts';
import {createCityTailLights} from './city-tail-lights.ts';
import {createCitySportDetails} from './city-sport-details.ts';
import {CityStreetFurniture} from './city-street-furniture.ts';
import {CityPedestrians} from './pedestrians.ts';
import {CityTraffic} from './traffic.ts';
import {CityTrafficSignals} from './city-traffic-signals.ts';
import {CityEbikes} from './city-ebikes.ts';
import {loadCoastalInfrastructure} from './city-coastal-infrastructure.ts';
import {createBayWater} from './city-bay-water.ts';
import {createCoastalHorizon} from './city-coastal-horizon.ts';
import {createPublicLighting} from './city-public-lighting.ts';
import {createBambooCorridor} from './city-bamboo-corridor.ts';
import {setLandscapeLightingMode} from './city-landscape-lighting.ts';
import type {RoadGraph} from './navigation.ts';
import type {CityData,Landmark,V2} from './city-types.ts';
import {CityCollision,stepCar,manualSteeringInput,clamp,type CarState} from './driving.ts';
/** Screen-space contact shading at street level: a tight 2.5 m radius darkens
 * kerbs, door reveals and wheel wells within 130 m. It reads depth and normals
 * from a dedicated half-resolution geometry buffer whose render list is only
 * the meshes within reach; the previous prepass path re-rendered the whole
 * visible city into a full-resolution MRT. Occlusion is estimated and blurred
 * at `aoRatio` and multiplied into the full-size scene colour. Aerial views
 * detach the pass: the facade shader's own sky-visibility ramp grounds the
 * towers there. `listMargin` covers the 100 m of travel between culls. */
// aoRatio is the half-size AO estimate; blurRatio also sizes ssaoCombine's output, so it must
// stay 1 or every later pass samples a half-resolution frame (GTA_SZ#3).
export const STREET_AO={radius:2.5,maxZ:130,strength:.65,base:.1,bufferRatio:.5,aoRatio:.5,blurRatio:1,listMargin:100} as const;
/** Shadow-map self-shadowing offsets per frustum. Babylon's normalBias shrinks casters along their normal in
 * world metres, so it has to follow the shadow texel: the 520 m street box is .25 m/px and .10 m is enough,
 * but the 2100 m aerial box is 1.03 m/px and the same .10 m left every sunlit facade speckled with acne
 * (random texels failing the depth test) while true tower shadows on the lawns were mostly lost. .8 m
 * (~.8 texel) clears the acne; casters thinner than that (lamp posts, trunks) drop out of the aerial map. */
export const SHADOW_BIAS={street:{normal:.10,depth:.0002},aerial:{normal:.8,depth:.0002}} as const;
/** terrain.glb / roads.glb materials that read the baked city occlusion (src/city-ambient-occlusion.ts). */
export const GROUND_AMBIENT_MATERIALS=new Set(['land','park','pavement','concrete','asphalt','roadline']);
/** Hull-front lamp anchors for the 3.48 m wide, 8.3 m long tank (game metres, +Z forward). */
export const TANK_HEADLIGHT_ANCHORS:[number,number,number][]=[[-1.15,1.35,3.4],[1.15,1.35,3.4]];
export class DrivingWorld{
 geography:Awaited<ReturnType<typeof loadCityGeography>>|null=null;
 sitePathView:ReturnType<typeof createCitySitePaths>|null=null;
 leisure:CityLeisureSession|null=null;
 leisureWater:CityLeisureWater|null=null;
 leisureView:ReturnType<typeof createCityLeisureView>|null=null;
 leisureBusy:()=>boolean=()=>false;
 leisureReelHeld=false;
 bicycle:CityBicycle|null=null;
 private bicycleParking:CityBicycleParking|null=null;
 private nextBicycleHint=0;
 private carRoadHint:RoadHeightHint|undefined;
 private walkRoadHint:RoadHeightHint|undefined;
 private walkSiteHint:{id:string|null;height:number}|undefined;
 carSurfaceHeight(x:number,z:number){if(!this.geography)return this.groundHeight(x,z);const surface=this.geography.levels.sample(x,z,this.carRoadHint).height;return this.bambooCafe?.layout.floorAt(x,z,surface)??surface;}
 private siteAccessBlocked(x:number,z:number,height:number,mode:TravelMode='motorcar'){
  const source=this.geography?.siteSurfaces?.restrictedSourceAt(x,z,height,mode);if(!source)return false;
  const publicRoad=this.collision.nearest(x,z,height,mode);
  return !(publicRoad&&publicRoad.road.sourceId!==source&&publicRoad.d<publicRoad.road.width/2-.65&&(publicRoad.height===undefined||Math.abs(publicRoad.height-height)<1.5));
 }
 private actorBlockReason(x:number,z:number,walking=false){
  const floor=walking&&this.geography?this.walkingSurface(x,z):undefined,height=this.geography?(floor?.height??this.carSurfaceHeight(x,z)):undefined,mode=walking?'foot':'motorcar';
  if(height!==undefined&&this.geography?.siteSurfaces?.blocked(x,z,height))return 'structure';
  if(height!==undefined&&this.siteAccessBlocked(x,z,height,mode))return 'restricted-road';
  return this.collision.blockReason(x,z,height,1.6,!!floor?.id,mode);
 }
 private actorCollision(x:number,z:number,walking=false){return !!this.leisureView?.peopleBlocked(x,z,walking?this.walkingSurfaceHeight(x,z):this.carSurfaceHeight(x,z))||this.actorBlockReason(x,z,walking)!==null;}
 private groundCollision(x:number,z:number){const height=this.geography?this.groundHeight(x,z):undefined;return (height!==undefined&&this.geography?.siteSurfaces?.blocked(x,z,height))||this.collision.blocked(x,z,height,1.6,false,'foot');}
 private walkingCameraCollision(x:number,y:number,z:number){
  const sites=this.geography?.siteSurfaces;
  const floor=sites?.walkAt(x,z,this.groundHeight(x,z),this.walkSiteHint);
  return sites?.blocked(x,z,y)||this.collision.blocked(x,z,this.geography?y:undefined,1.6,!!floor?.id&&y>=floor.height,'foot')||this.propBlocked(x,z);
 }
 graphicsQuality:CityGraphicsQuality=(()=>{let storage:Storage|null=null;try{storage=window.localStorage;}catch{}return loadCityGraphicsQuality(location.search,storage);})();
 get graphicsProfile(){return CITY_GRAPHICS_PROFILES[this.graphicsQuality];}
 setGraphicsQuality(quality:CityGraphicsQuality){
  if(!isCityGraphicsQuality(quality))return false;
  this.graphicsQuality=quality;let storage:Storage|null=null;try{storage=window.localStorage;}catch{}
  const saved=saveCityGraphicsQuality(quality,storage);this.applyGraphicsQuality();
  if(this.ready&&this.graphicsProfile.multipass&&!this.cinematic)void this.loadCinematicEnvironment().catch(error=>console.warn('Cinematic lighting unavailable',error));
  return saved;
 }
 private opticsAttached=false;
 private syncGraphicsPostEffects(){
  const {multipass}=this.graphicsProfile;
  if(!multipass){
   if(this.opticsAttached){this.pipeline.removeCamera(this.camera);this.opticsAttached=false;}
   if(this.ao?.cameras.includes(this.camera))this.scene.postProcessRenderPipelineManager.detachCamerasFromRenderPipeline('contact-shading',this.camera);
   this.pipeline.automaticBuild=false;
   this.scene.imageProcessingConfiguration.applyByPostProcess=false;
   return;
  }
  if(!this.opticsAttached){this.pipeline.automaticBuild=true;this.pipeline.addCamera(this.camera);this.opticsAttached=true;}
  if(!this.ao)this.createContactShading();
  const profile=this.graphicsProfile,msaa=this.overviewEffects?1:Math.min(profile.msaa,this.engine.getCaps().maxMSAASamples||1);
  const lens=profile.lensEffects&&this.lightMode!=='day';
  applyAntiAliasing(this.pipeline,this.overviewEffects,{msaa,fxaa:msaa===1,grain:lens,chromaticAberration:lens,bloomScale:profile.bloomScale});
  if(this.ao){
   this.ao.samples=profile.aoSamples;
   const enabled=profile.ao&&!this.overviewEffects,attached=this.ao.cameras.includes(this.camera),manager=this.scene.postProcessRenderPipelineManager;
   if(enabled&&!attached)manager.attachCamerasToRenderPipeline('contact-shading',this.camera);
   else if(!enabled&&attached)manager.detachCamerasFromRenderPipeline('contact-shading',this.camera);
  }
  syncPostChain(this.scene,this.pipeline,this.camera);
 }
 private applyGraphicsQuality(){
  const profile=this.graphicsProfile;this.resize();this.engine.resize();
  this.scene.postProcessesEnabled=profile.multipass;
  this.scene.renderTargetsEnabled=profile.multipass;
  this.scene.shadowsEnabled=profile.multipass;
  this.reflectionsEnabled=profile.multipass;
  if(this.shadows.mapSize!==profile.shadowSize)this.shadows.mapSize=profile.shadowSize;this.applyShadowBias();
  const shadowMap=this.shadows.getShadowMap();if(shadowMap){shadowMap.refreshRate=this.overviewEffects?12:1;shadowMap.resetRefreshCounter();}
  for(const mirror of [this.mirror,this.waterMirror]){if(mirror.getSize().width!==profile.mirrorSize)mirror.resize(profile.mirrorSize);mirror.resetRefreshCounter();}
  this.syncGraphicsPostEffects();this.landscape?.setGraphicsQuality(this.graphicsQuality);this.canopy?.setGraphicsQuality(this.graphicsQuality);
  this.vehicleReflections?.setEnabled(profile.vehicleProbe&&this.reflectionsEnabled&&!this.tank?.active);
  if(this.ready){this.vegetation();this.cull();}
 }

 flight:CityFlight|null=null;private flightRequest=0;
 tank:CityTank|null=null;rider:CityRider|null=null;riderLoading=false;walkFirstPerson=false;private riderYaw=0;private riderPending:Promise<boolean>|null=null;private walkingTransition=false;private tankRequest=0;
 coastal:Awaited<ReturnType<typeof loadCoastalInfrastructure>>|null=null;bayWater:ReturnType<typeof createBayWater>|null=null;publicLighting:ReturnType<typeof createPublicLighting>|null=null;private lampAssignments=[-1,-1];
 coastalHorizon:ReturnType<typeof createCoastalHorizon>[]=[];
 propObstacles:{x:number;z:number;heading:number}[]=[];
 buildingSigns:Awaited<ReturnType<typeof attachCityBuildingSigns>>|null=null;
 vehicleMaterials:ReturnType<typeof refineHeroVehicleMaterials>|null=null;audio=new CityAudio();autopilot:CityAutopilot|null=null;cockpit:ReturnType<typeof createCityCockpit>|null=null;tailLights:ReturnType<typeof createCityTailLights>|null=null;streetFurniture:CityStreetFurniture|null=null;bambooCorridor:ReturnType<typeof createBambooCorridor>|null=null;
 drivingInput:DrivingInput={throttle:0,steer:0,handbrake:false};private previousAutoPhase='idle';
 cinematic:Awaited<ReturnType<typeof createCinematicLook>>|null=null;
 private cinematicPending:Promise<void>|null=null;
 private loadCinematicEnvironment(){
  this.cinematicPending??=createCinematicLook(this).then(look=>{
   this.cinematic=look;
   this.scene.onDisposeObservable.addOnce(()=>look.dispose());
   this.setLightMode(this.lightMode);
  }).finally(()=>{this.cinematicPending=null;});
  return this.cinematicPending;
 }
 bambooLook:ReturnType<typeof createBambooLook>|null=null;
 bambooCafe:Awaited<ReturnType<typeof createBambooCafe>>|null=null;
 bayparkLook:ReturnType<typeof createBayparkLook>|null=null;
 localLighting:ReturnType<typeof createLocalLighting>|null=null;
 roadSurface:ReturnType<typeof applyCinematicRoad>|null=null;
 rainPuddles:ReturnType<typeof createRainPuddles>|null=null;
 rainWeather:ReturnType<typeof createCityRainWeather>|null=null;
 weather:CityWeather='clear';
 get raining(){return this.weather==='rain';}
 groundRelief:Awaited<ReturnType<typeof loadCityGroundRelief>>|null=null;
 mountains:Awaited<ReturnType<typeof loadCityMountains>>|null=null;
 private nextDetailUpdate=0;private detailWasMoving=false;private previousDetailFocus={x:Infinity,z:Infinity};
 private sceneryTop=0;
 readonly compatibleRange=COMPATIBLE_CITY_RANGE;
 private baseStream:CityBaseStream|null=null;
 private baseMaterialCache:CityBaseMaterialCache|null=null;
 private baseMeshes:Record<BaseStreamTile['role'],AbstractMesh[]>={terrain:[],roads:[],buildings:[]};
 private landscapeSurfaces:ReturnType<typeof applyLandscapeSurfaces>|null=null;
 private baseDirty=false;private basePanel:HTMLDivElement|null=null;
 private baseTravel:{id:number;landmark:Landmark}|null=null;private baseTravelId=0;private baseTravelCommit=false;
 vehicleReflections:ReturnType<typeof createVehicleReflections>|null=null;
 vehicleFinish:ReturnType<typeof applyCinematicVehicleFinish>|null=null;
 sportDetails:ReturnType<typeof createCitySportDetails>|null=null;
 instrumentation!:SceneInstrumentation; gpuInstrumentation!:EngineInstrumentation; updateMs=0; renderMs=0; ao:SSAO2RenderingPipeline|null=null; debugSimulation=true; debugFacades=true; facadeStream:CityFacadeStream|null=null; aerial=false; observer=new CityObserver(); overviewEffects=false; renderFrames=0;
 architecture!:ReturnType<typeof createArchitectureMaterials>; facadeDiversity!:ReturnType<typeof createFacadeDiversity>; landscape:CityLandscape|null=null; canopy:CityCanopy|null=null; rooftops:CityRooftops|null=null; roofSurface!:ReturnType<typeof createRoofSurface>; ambient!:ReturnType<typeof createCityAmbient>; signage:Awaited<ReturnType<typeof loadLandmarkSignage>>|null=null; wheelRadius=.4404; lastLandscapeAerial=false;
 engine:Engine;scene:Scene;camera:FreeCamera;car:TransformNode;data!:CityData;collision!:CityCollision;
 state:CarState={x:0,z:0,yaw:0,speed:0,steer:0,distance:0};ready=false;paused=false;night=false;lightMode:'sunset'|'night'|'day'='sunset';walk:CityWalk|null=null;debugEpoch=0;view=0;keys=new Set<string>();
 groundHeight:(x:number,z:number)=>number=()=>0;detailManifest:LandmarkDetailManifest|null=null;candidateManifest:LandmarkCandidateManifest|null=null;carFill:PointLight|null=null;traffic:CityTraffic|null=null;signals:CityTrafficSignals|null=null;ebikes:CityEbikes|null=null;pedestrians:CityPedestrians|null=null;trafficSources:AbstractMesh[]=[];wheelSpin=0;
 onTick:((dt:number)=>void)|null=null;onMessage:((s:string)=>void)|null=null;
 samples:number[]=[];sun:DirectionalLight;hemi:HemisphericLight;shadows:ShadowGenerator;pipeline:DefaultRenderingPipeline;mirror:MirrorTexture;waterMirror:MirrorTexture;
 blocks:{mesh:AbstractMesh;x:number;z:number;road:boolean;detail?:boolean;terrain?:boolean;water?:boolean;bounds?:{minX:number;maxX:number;minZ:number;maxZ:number}}[]=[];landmarks:AbstractMesh[]=[];carMeshes:AbstractMesh[]=[];
 reflectionsEnabled=true;private reflectionEye=new Vector3(1e9,0,0);private reflectionDirection=new Vector3();private reflectionMotionUntil=0;reflectionFrames={road:0,water:0};
 lastCull=new Vector3(1e9,0,1e9);lastVegetation=new Vector3(1e9,0,1e9);roadName='滨海大道';offroad=false;cameraYaw=0;cameraPitch=.22;drag=false;pointer=[0,0];viewReturn=0;time=0;skyMat!:ShaderMaterial;headlights:SpotLight[]=[];vehicleLightRig!:TransformNode;carHeadlightAnchors:[number,number,number][]=[[-.6,.82,2.25],[.6,.82,2.25]];streetLights:PointLight[]=[];windowLights:PointLight[]=[];lampData:number[][]=[];lightTick=0;lightTargets:{position:Vector3;power:number}[]=[];windowSources:{x:number;z:number}[]=[];photoTarget:Landmark|null=null;photoAngle=.5;photoElevation=.32;photoDistance=250;
 constructor(public canvas:HTMLCanvasElement){
  const {multipass}=this.graphicsProfile;
  this.engine=new Engine(canvas,false,{stencil:true,powerPreference:multipass?'high-performance':'default',doNotHandleContextLost:true},false);this.resize();
  this.scene=new Scene(this.engine);this.scene.clearColor=new Color4(.39,.54,.63,1);this.scene.fogMode=Scene.FOGMODE_LINEAR;this.scene.fogStart=this.compatibleRange.fogStart;this.scene.fogEnd=this.compatibleRange.fogEnd;this.scene.fogDensity=.000115;this.scene.fogColor=new Color3(.38,.24,.30);
  const ip=this.scene.imageProcessingConfiguration;ip.toneMappingEnabled=true;ip.toneMappingType=1;ip.exposure=1.05;ip.contrast=1.14;
  this.instrumentation=new SceneInstrumentation(this.scene);this.instrumentation.captureActiveMeshesEvaluationTime=true;this.instrumentation.captureRenderTargetsRenderTime=true;this.instrumentation.captureRenderTime=true;this.gpuInstrumentation=new EngineInstrumentation(this.engine);this.gpuInstrumentation.captureGPUFrameTime=false; /* Compatibility release: CPU timing retained; no GPU timestamp queries during the Mac watchdog investigation. */this.gpuInstrumentation.captureShaderCompilationTime=true;
  this.camera=new FreeCamera('driving-chase',new Vector3(0,4,-8),this.scene);this.camera.minZ=.75;this.camera.maxZ=18000;this.camera.fov=.9;this.camera.inputs.clear();
  this.hemi=new HemisphericLight('sky-bounce',new Vector3(0,1,0),this.scene);this.hemi.diffuse=new Color3(.70,.80,1.0);this.hemi.groundColor=new Color3(.32,.27,.30);this.hemi.intensity=.88;
  this.sun=new DirectionalLight('sunset',new Vector3(.95,-.22,.18),this.scene);this.sun.diffuse=new Color3(1,.41,.18);this.sun.intensity=3.0;this.sun.shadowMinZ=1;this.sun.shadowMaxZ=1200;this.sun.autoUpdateExtends=false;this.sun.orthoLeft=-260;this.sun.orthoRight=260;this.sun.orthoTop=260;this.sun.orthoBottom=-260;
  this.shadows=new ShadowGenerator(this.graphicsProfile.shadowSize,this.sun);this.shadows.usePercentageCloserFiltering=true;this.shadows.filteringQuality=ShadowGenerator.QUALITY_LOW;this.shadows.bias=SHADOW_BIAS.street.depth;this.shadows.normalBias=SHADOW_BIAS.street.normal;
  this.opticsAttached=multipass;
  this.pipeline=new DefaultRenderingPipeline('city-optics',true,this.scene,multipass?[this.camera]:[],multipass);this.pipeline.samples=1;this.pipeline.fxaaEnabled=true;this.pipeline.bloomEnabled=true;this.pipeline.bloomThreshold=.90;this.pipeline.bloomWeight=.34;this.pipeline.bloomKernel=72;this.pipeline.bloomScale=.5;
  // The scene target must be half-float so HDR survives into bloom and ACES;
  // the default 8-bit pass clipped every highlight when this pipeline owned
  // the scene. MSAA on that target is applied by `syncPostChain`.
  this.sky();this.environment();this.roofSurface=createRoofSurface(this.scene);this.ambient=createCityAmbient(this.scene);
  // Every architecture material (ordinary blocks, near facades, landmark glass) reads the baked city occlusion; roofs sample at their own height.
  this.architecture=createArchitectureMaterials(this.scene,(id,material)=>{if(id==='city-roof')this.roofSurface.attach(material);this.ambient.attach(material,id==='city-roof'?'roof':'wall');});this.facadeDiversity=createFacadeDiversity(this.scene);
  this.car=new TransformNode('player-electric-GT',this.scene);
  this.mirror=new MirrorTexture('wet-road-reflection',this.graphicsProfile.mirrorSize,this.scene,true);this.mirror.mirrorPlane=new Plane(0,-1,0,.105);this.mirror.refreshRate=2;this.mirror.blurKernel=7;this.mirror.level=.65;
  this.waterMirror=new MirrorTexture('bay-reflection',this.graphicsProfile.mirrorSize,this.scene,true);this.waterMirror.mirrorPlane=new Plane(0,-1,0,-.12);this.waterMirror.refreshRate=3;this.waterMirror.blurKernel=1;this.waterMirror.level=.68;
  this.applyGraphicsQuality();
  // Sky first: its finite radius must never overwrite more distant terrain.
  // Mirrors own separate render queues and need the same ordering.
  const atmosphere=this.scene.getMeshByName('atmosphere');
  const skyFirst=(a:SubMesh,b:SubMesh)=>Number(b.getMesh()===atmosphere)-Number(a.getMesh()===atmosphere)||RenderingGroup.PainterSortCompare(a,b);
  this.scene.setRenderingOrder(0,skyFirst);
  for(const mirror of [this.mirror,this.waterMirror]){
   mirror.setRenderingOrder(0,skyFirst);
   // Infinite-distance meshes follow the real camera. During an RTT center
   // the sky at the reflected eye as well, including at 2200m drone height.
   const inverseView=Matrix.Identity(),savedSkyPosition=new Vector3();
   mirror.onBeforeRenderObservable.add(()=>{
    if(!atmosphere)return;savedSkyPosition.copyFrom(atmosphere.position);
    this.scene.getViewMatrix().invertToRef(inverseView);
    inverseView.getTranslationToRef(atmosphere.position);
    atmosphere.position.subtractInPlace(this.camera.globalPosition);
    atmosphere.computeWorldMatrix(true);
   });
   mirror.onAfterRenderObservable.add(()=>{
    if(!atmosphere)return;atmosphere.position.copyFrom(savedSkyPosition);atmosphere.computeWorldMatrix(true);
   });

   // Explicit RTT lists bypass Babylon's normal frustum culling. This callback
   // runs after MirrorTexture installs its reflected view matrix.
   mirror.getCustomRenderList=(_face,list,length)=>{
    if(!list)return null;const planes=Frustum.GetPlanes(this.scene.getTransformMatrix()),visible:AbstractMesh[]=[];
    for(let i=0;i<length;i++){const m=list[i];if(m===atmosphere||m.isInFrustum(planes))visible.push(m);}
    return visible;
   };
  }
  this.mirror.onAfterRenderObservable.add(()=>{this.reflectionFrames.road=this.renderFrames;});this.waterMirror.onAfterRenderObservable.add(()=>{this.reflectionFrames.water=this.renderFrames;});
  // Attach timing observers after the object renderers exist.
  this.instrumentation.captureRenderTargetsRenderTime=false;
  this.instrumentation.captureRenderTargetsRenderTime=true;
  // Vehicle lights hang off a rig that is never disabled. Disabling the car
  // node while the tank is driven would disable these lights too, and every
  // light enable/disable changes the light layout of each nearby PBR shader:
  // ~90 programs recompile per vehicle switch, a 1-2 s stall with holes
  // where meshes wait for their new effect. The rig follows the active vehicle.
  this.vehicleLightRig=new TransformNode('vehicle-light-rig',this.scene);
  for(const side of [-1,1]){const light=new SpotLight('headlight',new Vector3(side*.6,0.82,2.25),new Vector3(0,-.055,1),Math.PI/3,4,this.scene);light.parent=this.vehicleLightRig;light.diffuse=new Color3(.78,.87,1);light.intensity=250;light.range=65;this.headlights.push(light);}
  window.addEventListener('resize',()=>{this.resize();this.engine.resize();});
  window.addEventListener('keydown',e=>{if(e.target instanceof HTMLElement&&e.target.closest('input,textarea,select,[contenteditable=true]'))return;if(['KeyW','KeyS','KeyA','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space','Tab'].includes(e.code))e.preventDefault();this.keys.add(e.code);if(!this.paused&&['KeyW','KeyS','KeyA','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space'].includes(e.code))this.cancelAutoDrive('manual-takeover');if(e.repeat)return;if(e.code==='KeyQ'&&!this.observer.active)this.leisure?.toggleFishing();if(e.code==='Space'&&!this.observer.active)this.leisure?.hook();if(e.code==='KeyB')void this.toggleFlight();if(e.code==='KeyT')void this.toggleTank();if(e.code==='Space'&&this.flight?.active)this.flight.fire();else if((e.code==='Enter'||e.code==='Space')&&this.controlMode==='tank'&&!this.paused)this.tank?.fire();if(e.code==='KeyN'&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!this.paused&&!this.observer.active)void this.toggleBicycle();if(e.code==='KeyH')this.audio.cue('horn');if(e.code==='KeyG')this.toggleAerial();if(e.code==='KeyR'&&!this.observer.active)this.resetRoad();if(e.code==='KeyC'&&!this.observer.active&&(this.bicycle?.active||this.leisure?.boat.active)){this.view=(this.view+1)%2;}else if(e.code==='KeyC'&&!this.observer.active&&this.walk?.active){this.walkFirstPerson=!this.walkFirstPerson;this.onMessage?.(this.walkFirstPerson?'步行 · 第一人称':'步行 · 第三人称');}else if(e.code==='KeyC'&&!this.observer.active){this.view=(this.view+1)%3;this.onMessage?.(['追踪镜头','驾驶舱镜头','远景镜头'][this.view]);}if(e.code==='KeyL')this.toggleLight();if(e.code==='KeyY')this.toggleRain();if(e.code==='KeyV'){if(this.observer.active)this.exitPhoto();else this.enterPhoto({id:'car',name:`绯红${CITY_COPY.vehicle}`,x:this.state.x,z:this.state.z,height:1.45,area:'车辆',excludeRadius:0,arrival:[this.state.x,this.state.z],yaw:this.state.yaw,photoDistance:7.7,photoElevation:.18,photoAngle:this.state.yaw+Math.PI+.65,photoTargetHeight:this.groundHeight(this.state.x,this.state.z)+.65});}if(e.code==='KeyF'){if(this.observer.active)this.exitPhoto();else if(!this.paused)void this.toggleWalking();}});
  window.addEventListener('keyup',e=>this.keys.delete(e.code));window.addEventListener('blur',()=>{this.keys.clear();this.drag=false;});
  let dragPointer:number|null=null,touchCentroid:{x:number;y:number}|null=null;
  const endDrag=()=>{this.drag=false;dragPointer=null;touchCentroid=null;this.viewReturn=2;};
  canvas.style.touchAction='none';
  canvas.addEventListener('contextmenu',e=>e.preventDefault());
  canvas.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'||![0,2].includes(e.button))return;this.drag=true;dragPointer=e.pointerId;this.pointer=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointerup',endDrag);canvas.addEventListener('pointercancel',endDrag);canvas.addEventListener('lostpointercapture',endDrag);window.addEventListener('blur',endDrag);
  canvas.addEventListener('pointermove',e=>{if(!this.drag||e.pointerId!==dragPointer||!e.buttons)return;const dx=e.clientX-this.pointer[0],dy=e.clientY-this.pointer[1];if(this.observer.active){if(!this.flight?.active){if(e.shiftKey)this.observer.pan(dx,dy,canvas.clientHeight);else this.observer.rotate(dx,dy);}}else if(this.walk?.active){this.walk.look(dx,dy);}else{this.cameraYaw+=dx*.005;this.cameraPitch=clamp(this.cameraPitch+dy*.002,.02,.8);}this.pointer=[e.clientX,e.clientY];});
  const touchPosition=(touches:TouchList)=>{let x=0,y=0;for(const touch of Array.from(touches)){x+=touch.clientX;y+=touch.clientY;}return {x:x/touches.length,y:y/touches.length};};
  canvas.addEventListener('touchstart',e=>{if(e.touches.length){touchCentroid=touchPosition(e.touches);e.preventDefault();}},{passive:false});
  canvas.addEventListener('touchmove',e=>{if(!touchCentroid||!e.touches.length)return;e.preventDefault();const next=touchPosition(e.touches),dx=next.x-touchCentroid.x,dy=next.y-touchCentroid.y;if(this.observer.active){if(!this.flight?.active){if(e.shiftKey)this.observer.pan(dx,dy,canvas.clientHeight);else this.observer.rotate(dx,dy);}}else if(this.walk?.active){this.walk.look(dx,dy);}else{this.cameraYaw+=dx*.005;this.cameraPitch=clamp(this.cameraPitch+dy*.002,.02,.8);}touchCentroid=next;},{passive:false});
  canvas.addEventListener('touchend',e=>{touchCentroid=e.touches.length?touchPosition(e.touches):null;});canvas.addEventListener('touchcancel',endDrag);
  canvas.addEventListener('wheel',e=>{if(this.observer.active){e.preventDefault();if(!this.flight?.active)this.observer.zoom(e.deltaY);}else if(this.walk?.active&&!this.paused){e.preventDefault();this.walk.zoom(e.deltaY);}},{passive:false});
  this.engine.runRenderLoop(()=>{if(document.hidden||!this.ready)return;if(!this.prepareBaseFrame()){this.engine.getDeltaTime();return;}const raw=this.engine.getDeltaTime(),dt=Math.min(raw/1000,.05);const begin=performance.now();if(this.ready){if(this.debugSimulation)this.update(dt);if(this.samples.length<36000)this.samples.push(raw);}this.updateMs=this.updateMs*.9+(performance.now()-begin)*.1;if(!this.prepareBaseFrame())return;const render=performance.now();this.scene.render();this.renderFrames++;this.renderMs=this.renderMs*.9+(performance.now()-render)*.1;});
  document.addEventListener('visibilitychange',()=>{this.keys.clear();this.drag=false;this.engine.getDeltaTime();});
  if(new URLSearchParams(location.search).has('profile'))this.profileControls();
 }
 resize(){const ratio=cityGraphicsRenderRatio(this.graphicsQuality,innerWidth,innerHeight,devicePixelRatio||1);this.engine?.setHardwareScalingLevel(1/ratio);}
 private createContactShading(){
  if(SSAO2RenderingPipeline.IsSupported){const gbuffer=this.scene.enableGeometryBufferRenderer(STREET_AO.bufferRatio);if(gbuffer){gbuffer.renderList=[];const ao=this.ao=new SSAO2RenderingPipeline('contact-shading',this.scene,{ssaoRatio:STREET_AO.aoRatio,blurRatio:STREET_AO.blurRatio},[this.camera],gbuffer,this.engine.getCaps().textureHalfFloatRender?Constants.TEXTURETYPE_HALF_FLOAT:Constants.TEXTURETYPE_UNSIGNED_INT);ao.radius=STREET_AO.radius;ao.totalStrength=STREET_AO.strength;ao.base=STREET_AO.base;ao.samples=8;ao.expensiveBlur=false;ao.maxZ=STREET_AO.maxZ;}}
 }
 private environment(){
  const n=128,faces=[];for(let face=0;face<6;face++){const arr=new Uint8Array(n*n*3);for(let y=0;y<n;y++)for(let x=0;x<n;x++){const u=x/(n-1)*2-1,v=y/(n-1)*2-1;let d:Vector3;switch(face){case 0:d=new Vector3(1,-v,-u);break;case 1:d=new Vector3(-1,-v,u);break;case 2:d=new Vector3(u,1,v);break;case 3:d=new Vector3(u,-1,-v);break;case 4:d=new Vector3(u,-v,1);break;default:d=new Vector3(-u,-v,-1);}d.normalize();const h=clamp(d.y*1.5,0,1),sun=Math.pow(Math.max(0,Vector3.Dot(d,new Vector3(-.95,.16,-.18).normalize())),9);const c=d.y<0?[.34,.31,.35]:[.64-h*.30+sun*.35,.49-h*.13+sun*.13,.56+h*.12-sun*.17];for(let j=0;j<3;j++)arr[(y*n+x)*3+j]=Math.min(255,c[j]*255);}faces.push(arr);}
  const env=new RawCubeTexture(this.scene,faces,n,Engine.TEXTUREFORMAT_RGB,Engine.TEXTURETYPE_UNSIGNED_BYTE,true,false,Texture.TRILINEAR_SAMPLINGMODE);env.gammaSpace=true;this.scene.environmentTexture=env;this.scene.environmentIntensity=.85;
 }

 private sky(){
  Effect.ShadersStore['szSkyVertexShader']='precision highp float;attribute vec3 position;uniform mat4 worldViewProjection;varying vec3 vP;void main(){vP=position;gl_Position=worldViewProjection*vec4(position,1.);}';
  Effect.ShadersStore['szSkyFragmentShader']=`precision highp float;varying vec3 vP;uniform float night;uniform float daylight;
  float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
  float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
  float fbm(vec2 p){float f=0.,a=.5;for(int i=0;i<5;i++){f+=noise(p)*a;p=p*2.03+17.;a*=.5;}return f;}
  void main(){vec3 p=normalize(vP);vec3 sd=normalize(vec3(-.95,.16,-.18));float west=pow(max(0.,dot(p,sd)),4.);float h=smoothstep(-.05,.72,p.y);
  if(daylight>.5){gl_FragColor=vec4(mix(vec3(.66,.76,.85),vec3(.20,.43,.68),h),1.);return;}
  vec3 horizon=mix(vec3(.42,.24,.35),vec3(.94,.32,.115),west);vec3 c=mix(horizon,vec3(.047,.12,.25),h);
  float glow=pow(max(0.,dot(p,sd)),22.);c+=vec3(.5,.18,.055)*glow;
  float sun=pow(max(0.,dot(p,sd)),4200.);c+=vec3(5.,2.2,.6)*sun;
  vec2 uv=p.xz/max(.14,p.y+.08)*2.0;uv.x*=.52;float cloud=fbm(uv+fbm(uv*.4)*1.6);float stripe=noise(vec2(uv.x*.8,uv.y*4.))* .13;
  float mask=smoothstep(.40,.66,cloud+stripe)*smoothstep(.01,.12,p.y)*(1.-smoothstep(.55,.99,p.y));
  vec3 cloudDark=mix(vec3(.18,.17,.29),vec3(.38,.16,.20),west);vec3 cloudLit=mix(vec3(.68,.31,.38),vec3(1.25,.34,.10),west);
  float rim=smoothstep(.46,.53,cloud)*(1.-smoothstep(.54,.65,cloud));vec3 cloudColor=mix(cloudDark,cloudLit,rim*.85+.24*west);
  c=mix(c,cloudColor,mask*.85);c=mix(c,c*vec3(.12,.22,.44),night);gl_FragColor=vec4(c,1.);}`;
  this.skyMat=new ShaderMaterial('sky',this.scene,{vertex:'szSky',fragment:'szSky'},{attributes:['position'],uniforms:['worldViewProjection','night','daylight']});this.skyMat.backFaceCulling=false;this.skyMat.disableDepthWrite=true;this.skyMat.setFloat('night',0);this.skyMat.setFloat('daylight',0);
  const sky=MeshBuilder.CreateSphere('atmosphere',{diameter:8000,segments:24},this.scene);sky.material=this.skyMat;sky.infiniteDistance=true;sky.isPickable=false;sky.applyFog=false;keepSkyInReflections(sky);
 }
 private async load(name:string){const r=await ImportMeshAsync(cityAssetUrl(name+'.glb'),this.scene);r.meshes[0].rotationQuaternion=Quaternion.Identity();for(const m of r.meshes){m.isPickable=false;m.receiveShadows=true;if(m.material instanceof PBRMaterial){m.material.environmentIntensity=1.0;m.material.forceIrradianceInFragment=true;m.material.maxSimultaneousLights=8;
   // Ground planes of the base city (lawn, pavement, plaza concrete, asphalt, markings) receive the baked city occlusion; water and lamps do not.
   if((name==='terrain'||name==='roads')&&GROUND_AMBIENT_MATERIALS.has(m.material.name))this.ambient.attach(m.material,'ground');}if(m.getTotalVertices())m.freezeWorldMatrix();}this.architecture.applyMeshes(r.meshes,name);this.facadeDiversity.applyMeshes(r.meshes,name);return r;}
 private baseView(destination?:Landmark){
  const focus=destination?{x:destination.arrival[0],z:destination.arrival[1]}:this.sceneFocus();
  const matrix=destination?Matrix.LookAtLH(new Vector3(focus.x-Math.sin(destination.yaw)*9,this.groundHeight(focus.x,focus.z)+4,focus.z-Math.cos(destination.yaw)*9),new Vector3(focus.x,this.groundHeight(focus.x,focus.z)+1.1,focus.z),Vector3.Up()).multiply(this.camera.getProjectionMatrix()):this.camera.getTransformationMatrix();
  const planes=Frustum.GetPlanes(matrix);
  return {x:focus.x,z:focus.z,overview:destination?false:this.overviewEffects,rangeProfile:'compatible' as const,planes,intersects:(tile:BaseStreamTile)=>planes.every(p=>p.normal.x*tile.bounds[p.normal.x>=0?'max':'min'][0]+p.normal.y*tile.bounds[p.normal.y>=0?'max':'min'][1]+p.normal.z*tile.bounds[p.normal.z>=0?'max':'min'][2]+p.d>=0)};
 }
 captureStreamView(id:string){
  if(!id||id.length>80)throw Error('Invalid camera sample identity');
  const view=this.baseView();
  return {id,origin:'runtime-captured' as const,x:view.x,z:view.z,overview:view.overview,planes:view.planes.map(p=>({normal:p.normal.asArray(),d:p.d})),camera:{eye:this.camera.position.asArray(),fov:this.camera.fov,minZ:this.camera.minZ,maxZ:this.camera.maxZ},controlMode:this.controlMode,capturedAt:new Date().toISOString()};
 }
 private placeInitialDrivingView(){
  const s=this.state,height=this.carSurfaceHeight(s.x,s.z);
  this.car.position.set(s.x,height+.12,s.z);this.car.rotation.y=s.yaw;this.cameraYaw=s.yaw;
  this.camera.position.set(s.x-Math.sin(s.yaw)*8,height+3.7,s.z-Math.cos(s.yaw)*8);
  this.camera.setTarget(new Vector3(s.x,height+1.1,s.z));
 }
 private attachBaseTile(tile:BaseStreamTile,container:AssetContainer,records:readonly unknown[]){
  this.baseMaterialCache!.adopt(container,tile.role,records);
  for(const material of container.materials)if(material instanceof PBRMaterial&&tile.role!=='buildings'&&GROUND_AMBIENT_MATERIALS.has(material.name))this.ambient.attach(material,'ground');
  return this.registerBaseMeshes(tile.role,container.meshes.filter(mesh=>mesh.getTotalVertices()>0));
 }
 private attachBasePack(pack:BasePackRecord,container:AssetContainer,records:readonly unknown[],metadata:BasePackMetadata){
  const meshes=container.meshes.filter(mesh=>mesh.getTotalVertices()>0),bindings=new Map(metadata.nodes.map(n=>[n.name,n]));
  const members=new Set(pack.members.map(m=>m.id));
  const groups:Record<BaseStreamTile['role'],AbstractMesh[]>={terrain:[],roads:[],buildings:[]};
  if(records.length!==metadata.materialOrigins.length||bindings.size!==metadata.nodes.length||meshes.length!==bindings.size||new Set(meshes.map(m=>m.name)).size!==meshes.length)throw Error('Physical pack world bindings incomplete');
  for(const mesh of meshes){const binding=bindings.get(mesh.name);if(!binding||!members.has(binding.member)||!Object.hasOwn(groups,binding.role))throw Error('Physical pack world role missing');groups[binding.role].push(mesh);}
  this.baseMaterialCache!.adoptMapped(container,metadata.materialOrigins);
  const releases:(()=>void)[]=[];let released=false;
  const detach=()=>{if(released)return;released=true;for(const release of releases.reverse())release();};
  try{for(const role of ['terrain','roads','buildings'] as const)if(groups[role].length)releases.push(this.registerBaseMeshes(role,groups[role]));return detach;}
  catch(error){detach();throw error;}
 }
 /** Both single-role tiles and physical packs enter the same original world
  * controllers. Own every mesh reference here so a failed attach or an unload
  * cannot leave water, reflection, shadow or culling lists holding old meshes. */
 private registerBaseMeshes(role:BaseStreamTile['role'],meshes:AbstractMesh[]){
  const waters=role==='terrain'?meshes.filter(m=>/^terrain_water(?:_|$)/.test(m.name)):[];
  // Validate all identities before any mesh is registered with a controller.
  const blocks:DrivingWorld['blocks']=meshes.map(mesh=>{
   const box=mesh.getBoundingInfo().boundingBox;
   if(role==='terrain')return {mesh,x:box.centerWorld.x,z:box.centerWorld.z,road:false,terrain:true,water:waters.includes(mesh),bounds:{minX:box.minimumWorld.x,maxX:box.maximumWorld.x,minZ:box.minimumWorld.z,maxZ:box.maximumWorld.z}};
   const name=mesh.name.match(/(?:block|roads)_(?:site_)?(-?\d+)_(-?\d+)_/);if(!name)throw Error('Streamed base mesh has no original block identity: '+mesh.name);
   return {mesh,x:(Number(name[1])+.5)*640,z:(Number(name[2])+.5)*640,road:role==='roads'};
  });
  let released=false;
  const detach=()=>{
   if(released)return;released=true;
   const removed=new Set(meshes),remove=(list:AbstractMesh[]|null|undefined)=>{if(list)for(let i=list.length-1;i>=0;i--)if(removed.has(list[i]))list.splice(i,1);};
   remove(this.baseMeshes[role]);for(let i=this.blocks.length-1;i>=0;i--)if(removed.has(this.blocks[i].mesh))this.blocks.splice(i,1);
   remove(this.shadows?.getShadowMap()?.renderList);remove(this.mirror?.renderList);remove(this.waterMirror?.renderList);remove(this.scene.geometryBufferRenderer?.renderList);
   for(const light of this.headlights)remove(light.excludedMeshes);
   this.bayWater?.detachMeshes(meshes);this.baseDirty=true;
  };
  try{
   // Cached terrain/road materials have already left the container ownership list.
   for(const mesh of meshes)if(mesh.material instanceof PBRMaterial&&role!=='buildings'&&GROUND_AMBIENT_MATERIALS.has(mesh.material.name))this.ambient.attach(mesh.material,'ground');
   this.architecture.applyMeshes(meshes,role);this.facadeDiversity.applyMeshes(meshes,role);
   this.landscapeSurfaces?.attach(meshes);this.bayWater?.attachMeshes(waters);
   for(const light of this.headlights)for(const water of waters)if(!light.excludedMeshes.includes(water))light.excludedMeshes.push(water);
   this.baseMeshes[role].push(...meshes);this.blocks.push(...blocks);this.baseDirty=true;
   return detach;
  }catch(error){detach();throw error;}
 }
 private prepareBaseFrame(){
  if(!this.baseStream)return true;
  void this.baseStream.request(this.baseView(this.baseTravel?.landmark));
  const state=this.baseStream.stats;
  if(state.ready){if(this.basePanel)this.basePanel.style.display='none';if(this.baseDirty){this.baseDirty=false;this.cull();}return true;}
  this.keys.clear();
  if(!this.basePanel){const panel=this.basePanel=document.createElement('div');panel.setAttribute('role','status');panel.style.cssText='position:fixed;inset:0;z-index:200;background:#102c2af5;color:#ecf4e9;display:grid;place-items:center;font:18px system-ui';document.body.append(panel);this.scene.onDisposeObservable.addOnce(()=>panel.remove());}
  this.basePanel.style.display='grid';this.basePanel.textContent=state.plan?.exceeded.length?'当前视野超出街区加载预算，场景保持暂停。':'正在读取前方街区，加载完成后继续。';
  return false;
 }
 async init(progress:(s:string)=>void,dataSources?:{city:CityJsonSource;roadLevels:CityJsonSource;base?:BaseStreamSources}){
  const loadAbort=new AbortController();this.scene.onDisposeObservable.addOnce(()=>loadAbort.abort());
  progress(`正在展开${CITY_CONFIG.product.city}地图`);
  if(dataSources)this.data=await loadCityJsonChunks<CityData>(dataSources.city,{signal:loadAbort.signal,progress:(loaded,total)=>progress(`正在读取地图分块 ${loaded}/${total}`)});
  else {const response=await fetch(cityAssetUrl('city.json'),{signal:loadAbort.signal});if(!response.ok)throw Error('地图加载失败');this.data=await response.json();}
  assertCityAssetIdentity(this.data.meta);await loadRoadDisplayNames(this.data);
  // Hangzhou detail assets bind the already verified whole-city geography,
  // rather than loading a Shenzhen-only terrain patch and replacing it later.
  progress(`正在展开${CITY_CONFIG.product.city}山地`);
  if(CITY_CONFIG.id==='hangzhou'){this.geography=await loadCityGeography(this.data,dataSources?.roadLevels,loadAbort.signal);this.groundHeight=this.geography.heightAt;this.sitePathView=createCitySitePaths(this.scene,this.geography.sitePaths);this.scene.onDisposeObservable.addOnce(()=>this.sitePathView?.dispose());}
  const sharedTerrain=this.geography?{cityId:'hangzhou' as const,manifestSha256:this.geography.manifestSha256,heightAt:this.geography.heightAt}:undefined;
  const detail=await loadLandmarkDetails(this.data,sharedTerrain);
  if(detail){this.groundHeight=detail.heightAt;this.detailManifest=detail.manifest;}
  this.candidateManifest=await loadLandmarkCandidates(this.data);
  if(CITY_CONFIG.id!=='hangzhou'){this.mountains=await loadCityMountains(this.groundHeight);this.groundHeight=this.mountains.heightAt;progress('正在铺设公园缓坡');this.groundRelief=await loadCityGroundRelief(this.groundHeight,undefined,false);this.groundHeight=this.groundRelief.heightAt;}progress('正在架设跨水桥梁');this.coastal=await loadCoastalInfrastructure(this.data,this.groundHeight);this.groundHeight=this.coastal.heightAt;this.collision=new CityCollision(this.data,this.geography?(id,x,z,y)=>this.geography!.levels.heightForSourceRoad(id,x,z,y):undefined);this.bicycle=new CityBicycle((x,z,height)=>this.bicycleSurface(x,z,height));this.walk=new CityWalk((x,z)=>this.actorCollision(x,z,true)||this.propBlocked(x,z)||this.parkedVehicleBlocks(x,z),(x,z)=>this.walkingSurfaceHeight(x,z));this.windowSources=[];this.state={...this.data.spawn,speed:0,steer:0,distance:0};
  if(CITY_CONFIG.id==='hangzhou')await this.initLeisure();
  let terrain:{meshes:AbstractMesh[]}={meshes:[]},roads:{meshes:AbstractMesh[]}={meshes:[]},buildings:{meshes:AbstractMesh[]}={meshes:[]};
  progress(`正在铺设水岸和城市道路`);
  if(dataSources?.base){
   this.baseMaterialCache=new CityBaseMaterialCache(this.scene);
   this.placeInitialDrivingView();
   this.baseStream=new CityBaseStream(this.scene,dataSources.base,{attach:(tile,container,records)=>this.attachBaseTile(tile,container,records),attachPack:(pack,container,records,metadata)=>this.attachBasePack(pack,container,records,metadata)});
   await this.baseStream.init(this.baseView());
   if(!this.baseStream.stats.ready)throw Error('基础街区未通过完整视野资源准入：'+JSON.stringify(this.baseStream.stats.plan));
   terrain={meshes:this.baseMeshes.terrain};roads={meshes:this.baseMeshes.roads};buildings={meshes:this.baseMeshes.buildings};
  }else{terrain=await this.load('terrain');roads=await this.load('roads');}
  this.mountains?.drapePaths(roads.meshes);for(const name of ['coastal-bridges','coastal-shoreline',...(CITY_CONFIG.water.oppositeShore?['opposite-shore']:[])]){const part=await this.load(name);for(const mesh of part.meshes.filter(m=>m.getTotalVertices()>0)){mesh.receiveShadows=name!=='opposite-shore';if(name==='opposite-shore'){mesh.applyFog=true;if(mesh.material instanceof PBRMaterial){mesh.material.albedoColor.set(.10,.15,.14);mesh.material.environmentIntensity=.35;}this.coastalHorizon.push(createCoastalHorizon(this.scene,mesh,this.coastal!.manifest.waterHeight));}if(name==='coastal-shoreline'&&mesh.material)mesh.material.backFaceCulling=false;this.landmarks.push(mesh);}}
  progress(`正在载入${CITY_CONFIG.product.city}建筑`);if(!this.baseStream)buildings=await this.load('buildings');this.facadeStream=new CityFacadeStream(this.scene,()=>this.cull(),(meshes,name)=>this.architecture.applyMeshes(meshes,name));await this.facadeStream.init(this.state.x,this.state.z);
  if(!this.baseStream)for(const mesh of [...roads.meshes,...buildings.meshes]){const m=mesh.name.match(/(?:block|roads)_(?:site_)?(-?\d+)_(-?\d+)_/);if(m)this.blocks.push({mesh,x:(Number(m[1])+.5)*640,z:(Number(m[2])+.5)*640,road:mesh.name.startsWith('roads')});}
  if(!this.baseStream&&CITY_CONFIG.id==='hangzhou')for(const mesh of terrain.meshes){if(!mesh.getTotalVertices())continue;const b=mesh.getBoundingInfo().boundingBox;this.blocks.push({mesh,x:b.centerWorld.x,z:b.centerWorld.z,road:false,terrain:true,water:/^terrain_water_/.test(mesh.name),bounds:{minX:b.minimumWorld.x,maxX:b.maximumWorld.x,minZ:b.minimumWorld.z,maxZ:b.maximumWorld.z}});}
  progress(`正在装配${CITY_CONFIG.product.city}地标`);const lm=await this.load('landmarks');this.landmarks.push(...lm.meshes.filter(m=>m.getTotalVertices()>0));if(this.detailManifest){const prefixes=this.detailManifest.replacedMeshPrefixes;for(const m of [...this.scene.meshes])if(prefixes.some(p=>m.name.startsWith(p)))m.dispose(false,false);this.blocks=this.blocks.filter(b=>!b.mesh.isDisposed());this.landmarks=this.landmarks.filter(m=>!m.isDisposed());const details=await this.load('landmark-detail');for(const mesh of details.meshes.filter(m=>m.getTotalVertices()>0)){const tile=mesh.name.match(/detail_block_(-?\d+)_(-?\d+)_/);if(tile)this.blocks.push({mesh,x:(Number(tile[1])+.5)*640,z:(Number(tile[2])+.5)*640,road:false});else this.landmarks.push(mesh);}}
  // Merged single-object candidates replace the remaining legacy base landmark silhouettes by name prefix; the source-grounded landmark-detail meshes above are never touched here.
  if(this.candidateManifest){progress('正在替换候选地标模型');const prefixes=this.candidateManifest.replacedMeshPrefixes;for(const m of [...this.scene.meshes])if(prefixes.some(p=>m.name.startsWith(p)))m.dispose(false,false);this.landmarks=this.landmarks.filter(m=>!m.isDisposed());const candidates=await this.load('landmark-candidates');for(const m of candidates.meshes){if(!m.getTotalVertices())continue;const box=m.getBoundingInfo().boundingBox;if(isCandidateGroundSlab(m.name,box.maximumWorld.y-box.minimumWorld.y,this.candidateManifest))m.dispose(false,false);else this.landmarks.push(m);}}
  this.signage=await loadLandmarkSignage(this.scene);this.landmarks.push(...this.signage.meshes);
  progress(`正在打开月白咖啡馆`);
  this.bambooCafe=await createBambooCafe(this.scene,this.groundHeight,meshes=>this.landmarks.push(...meshes));
  const cafeGround=this.groundHeight;
  this.groundHeight=(x,z)=>this.bambooCafe!.layout.floorAt(x,z,cafeGround(x,z));
  this.data.landmarks.push(this.bambooCafe.layout.landmark);
  progress('正在点亮城市招牌');this.buildingSigns=await attachCityBuildingSigns(this.scene,buildings.meshes,this.data);
  progress('正在启动你的车');const ambient=await this.load('traffic-car');this.trafficSources=ambient.meshes.filter(m=>m.getTotalVertices()>0);ambient.meshes[0].setEnabled(false);const metadata=await fetch(cityAssetUrl('vehicle-manifest.json')).then(r=>r.json()) as VehicleManifest;this.wheelRadius=metadata.wheelRadius;this.carHeadlightAnchors=headlightAnchors(metadata.recommendedHeadlightAnchorsGame);this.headlights.forEach((l,i)=>l.position.copyFromFloats(...this.carHeadlightAnchors[i]));const car=await this.load('car');car.meshes[0].parent=this.car;this.carMeshes=car.meshes.filter(m=>m.getTotalVertices()>0);for(const m of car.meshes){m.unfreezeWorldMatrix();const q=m.name.match(/(?:wheel|brake)_([lr][fr])_/);if(q&&m instanceof Mesh){m.setPivotPoint(Vector3.FromArray(metadata.wheelCentresGltf[q[1]]));m.rotationQuaternion=null;}}
  this.vehicleFinish=applyCinematicVehicleFinish(this.scene,this.car,this.carMeshes);this.carMeshes.push(...this.vehicleFinish.meshes);this.cockpit=createCityCockpit(this.scene,this.car,this.carMeshes);this.carMeshes.push(...this.cockpit.meshes);
  progress(CITY_COPY.planting);this.landscape=new CityLandscape(this.scene,this.groundHeight,(x,z,r)=>!!this.bambooCafe?.layout.reserved(x,z,r)||!!this.geography?.siteSurfaces?.reservedWalkPath(x,z));await this.landscape.init();progress(CITY_CONFIG.id==='hangzhou'?'正在栽种桃柳与杭州林冠':'正在栽种榕树、木棉与樟树林冠');this.canopy=new CityCanopy(this.scene,this.groundHeight,(x,z,r)=>!!this.bambooCafe?.layout.reserved(x,z,r)||!!this.geography?.siteSurfaces?.reservedWalkPath(x,z));await this.canopy.init();
  progress('正在布置屋顶设备、水箱与停机坪');progress('正在读取城市遮蔽贴图');await this.ambient.load();this.ambient.setMode(this.lightMode);try{const rooftops=new CityRooftops(this.scene);await rooftops.init();this.rooftops=rooftops;rooftops.setMode(this.lightMode);if(rooftops.plan){progress('正在读取屋顶索引贴图');await this.roofSurface.load(rooftops.plan.lookup);}}catch(error){console.warn('Rooftop layer unavailable; base roofs kept',error);}progress('正在准备路侧树木');this.landscape.configureRoadside(this.data,{collisionFootprints:this.detailManifest?.collisionFootprints,bridgeCrossings:this.coastal?.manifest.crossings,blocked:(x,z)=>this.groundCollision(x,z)||this.propBlocked(x,z)||!!this.canopy?.trunkNear(x,z)||!!this.geography?.siteSurfaces?.reservedWalkPath(x,z)});progress('正在布置城市座椅');this.streetFurniture=new CityStreetFurniture(this.scene,this.groundHeight);await this.streetFurniture.init();progress('正在安装路口红绿灯');this.signals=new CityTrafficSignals(this.scene,this.groundHeight);await this.signals.init();this.signals.setNight(this.night);progress('正在停放电动车');this.ebikes=new CityEbikes(this.scene,this.groundHeight);await this.ebikes.init();
  progress(`正在铺设${CITY_CONFIG.streetScene.name}街面`);this.bambooCorridor=createBambooCorridor(this.scene,this.data,(x,z)=>{
  const terrain=this.groundHeight(x,z),n=this.collision.nearest(x,z);
  if(!n)return terrain+.08;
  const edge=n.d-n.road.width/2;
  return terrain+(edge<=10?.26:.08);
},{reserved:(x,z,r)=>!!this.bambooCafe?.layout.reserved(x,z,r)});this.bambooCorridor.setMode(this.lightMode);
  const corridorTree=CITY_CONFIG.id==='hangzhou'?CITY_CONFIG.vegetation.baseTreeNames[0]:'orchid-tree';this.bambooCorridor.adoptStreetTrees(this.landscape.borrowPrototype(corridorTree),this.landscape.borrowPrototype(corridorTree+'-lod'));
  this.bambooCorridor.adoptParkedCars(this.trafficSources);
  this.setupReflections();this.landscapeSurfaces=applyLandscapeSurfaces(this.scene);this.mountains?.attachVisuals(this.scene);this.groundRelief?.attachVisuals(this.scene);this.roadSurface=applyCinematicRoad(this.scene,this.mirror);this.setupSigns();this.pedestrians=new CityPedestrians(this.scene,this.groundHeight,(x,z)=>this.groundCollision(x,z)||this.propBlocked(x,z));await this.pedestrians.init();this.pedestrians.place(this.state.x,this.state.z);this.lampData=await(await fetch(cityAssetUrl('lamps.json'))).json();for(let i=0;i<2;i++){const l=new PointLight('street-light-pool-'+i,Vector3.Zero(),this.scene);l.diffuse=new Color3(1,.67,.36);l.range=26;l.intensity=70;this.streetLights.push(l);}for(let i=0;i<2;i++){const l=new PointLight('window-spill-'+i,Vector3.Zero(),this.scene);l.diffuse=new Color3(1,.42,.14);l.range=17;l.intensity=0;l.setEnabled(false);this.windowLights.push(l);}
  const parkPoles=await this.load('park-floodlight');this.publicLighting=createPublicLighting(this.scene,this.lampData,this.coastal!.manifest.parkLights,parkPoles.meshes,this.groundHeight,{tiledShoreReceivers:CITY_CONFIG.id==='hangzhou'});this.publicLighting.update(this.state.x,this.state.z,true);
  progress(CITY_COPY.lighting);
  if(this.graphicsProfile.multipass)await this.loadCinematicEnvironment();
  this.vehicleMaterials=refineHeroVehicleMaterials(this.scene,this.carMeshes);
  this.sportDetails=createCitySportDetails(this.scene,this.car);this.sportDetails.setMode(this.lightMode);this.carMeshes.push(...this.sportDetails.meshes);this.scene.onDisposeObservable.addOnce(()=>this.sportDetails?.dispose());
  progress('雨停了，正在铺设路边积水');this.rainPuddles=createRainPuddles(this.scene,this.data,this.groundHeight,this.mirror);await this.rainPuddles.readyPromise;this.rainWeather=createCityRainWeather(this.scene,(x,z,radius,limit)=>this.rainPuddles!.nearby(x,z,radius,limit),this.sun,this.hemi);this.rainWeather.setEnabled(this.raining);this.tailLights=createCityTailLights(this.scene,this.car,this.carMeshes,this.vehicleLightRig);this.scene.onDisposeObservable.addOnce(()=>{this.rainWeather?.dispose();this.rainPuddles?.dispose();this.cockpit?.dispose();this.tailLights?.dispose();this.streetFurniture?.dispose();this.bambooCorridor?.dispose();this.audio.dispose();this.vehicleMaterials?.dispose();});
  // Sample-area surfaces keep the existing city assets, HDR and public light
  // field. Only the nearby authored fixtures receive a bounded extra shadow.
  this.bambooLook=createBambooLook(this.scene);this.bayparkLook=createBayparkLook(this.scene,CITY_CONFIG.id==='hangzhou'?{waterHeight:this.coastal!.manifest.waterHeight,tiledReceivers:true}:{});
  this.localLighting=createLocalLighting({scene:this.scene,lamps:this.lampData,parkLights:this.coastal!.manifest.parkLights,heightAt:this.groundHeight,casters:()=>this.shadows.getShadowMap()?.renderList??[],stableReceivers:this.carMeshes});
  this.bambooLook.setMode(this.lightMode);this.bayparkLook.setMode(this.lightMode);this.localLighting.setMode(this.lightMode);
  this.bambooCafe.setMode(this.lightMode);
  const depthScenery=new Set([...this.blocks.map(b=>b.mesh),...this.landmarks,...this.scene.meshes.filter(m=>/^(terrain_|ground_relief_)/.test(m.name))]);
  this.sceneryTop=Math.max(this.baseStream?.maximumWorldHeight??0,...Array.from(depthScenery,m=>m.getBoundingInfo().boundingBox.maximumWorld.y));
  this.vehicleReflections=createVehicleReflections(this.scene,this.car,this.carMeshes,this.camera,()=>this.mirror.renderList??[]);this.scene.onDisposeObservable.addOnce(()=>this.vehicleReflections?.dispose());
  this.flight=new CityFlight(this.scene,this.data,this.groundHeight,this.landmarks,()=>this.audio.explosion());this.scene.onDisposeObservable.addOnce(()=>this.flight?.dispose());
  this.tank=new CityTank(this.scene,this.data,this.groundHeight,()=>this.landmarks,()=>this.audio.explosion());this.scene.onDisposeObservable.addOnce(()=>{this.tank?.dispose();this.rider?.dispose();});
  this.ready=true;this.placeInitialDrivingView();this.applyGraphicsQuality();
  if(CITY_CONFIG.id==='hangzhou'){this.setLightMode('day');this.restoreBicycleParking();}
 }
 private configureTrafficContact(){
  if(!this.traffic)return;
  this.traffic.vehicleObstacle=()=>this.bicycle?.active?{...this.bicycle.pose,groundY:this.bicycle.height,...BICYCLE_BODY}:this.walk?.active?{x:this.walk.x,z:this.walk.z,yaw:this.walk.yaw,groundY:this.walkingSurfaceHeight(this.walk.x,this.walk.z),halfWidth:.23,halfLength:.23,height:1.6}:
   {...this.state,groundY:this.carSurfaceHeight(this.state.x,this.state.z),...(this.tank?.active?{halfWidth:1.94,halfLength:3.55,height:2.5}:CAR_BODY)};
  this.traffic.contactBlocked=(body:VehicleBody)=>{
   const c=Math.cos(body.yaw),s=Math.sin(body.yaw);
   for(const u of [-body.halfWidth,0,body.halfWidth])for(const v of [-body.halfLength,0,body.halfLength]){
    const x=body.x+c*u+s*v,z=body.z-s*u+c*v;
    if(this.siteAccessBlocked(x,z,body.groundY)||this.collision.blocked(x,z,body.groundY,body.height)||this.propBlocked(x,z)||this.geography?.siteSurfaces?.blocked(x,z,body.groundY,body.height))return true;
   }
   return false;
  };
  this.traffic.onVehicleContact=speed=>{if(speed>.35&&this.time>=this.nextVehicleImpact){this.nextVehicleImpact=this.time+.18;this.audio.impact(speed);if(!this.walk?.active)this.vehicleImpactPulse=Math.max(this.vehicleImpactPulse,Math.min(.12,speed*.006));}};
 }
 startTraffic(graph:RoadGraph){if(this.geography)graph.bindSourceSurfaceHeight((id,x,z,y)=>this.geography!.levels.heightForSourceRoad(id,x,z,y));const signalHold=(x:number,z:number,yaw:number,height?:number)=>height!==undefined&&Math.abs(height-this.groundHeight(x,z))>2.5?null:this.signals?.holdDistance(x,z,yaw)??null;const directionAllowed=(a:number,b:number,mode:TravelMode='motorcar')=>{const sourceDirection=graph.allowsDirection(a,b,mode);if(sourceDirection!==undefined)return sourceDirection;const p=graph.nodes[a],q=graph.nodes[b],n=this.collision.nearest((p[0]+q[0])/2,(p[1]+q[1])/2);return !n?.road.oneway||(q[0]-p[0])*Math.sin(n.yaw)+(q[1]-p[1])*Math.cos(n.yaw)>0;};this.autopilot=new CityAutopilot(graph,this.collision,{signalHold:(x,z,yaw)=>signalHold(x,z,yaw,this.geography?this.carSurfaceHeight(x,z):undefined),surfaceHeight:this.geography?(x,z)=>this.carSurfaceHeight(x,z):undefined,destinationHeight:this.geography?this.groundHeight:undefined});this.traffic=new CityTraffic(graph,this.trafficSources,this.scene,this.groundHeight,directionAllowed);this.traffic.signalHold=signalHold;this.configureTrafficContact();this.traffic.place(this.state.x,this.state.z);if(this.ebikes){this.ebikes.attachGraph(graph,(a,b)=>directionAllowed(a,b,'bicycle'));this.ebikes.signalHold=signalHold;this.ebikes.place(this.state.x,this.state.z);}this.cull();}
 startAutoDrive(destination:Landmark){if(this.leisure?.active){this.onMessage?.('先靠岸下船或收竿，再回到汽车自动驾驶');return;}if(this.bicycle?.active){this.onMessage?.('骑行使用手动操作，回到汽车后可自动驾驶');return;}if(this.tank?.active){this.onMessage?.('坦克使用手动驾驶，按 T 换回轿车可自动导航');return;}if(this.walk?.active){this.onMessage?.('走回车旁，按 F 上车后开始驾驶');return;}if(!this.autopilot)return;if(this.observer.active)this.exitPhoto();this.keys.clear();this.paused=false;this.autopilot.start(destination);this.previousAutoPhase='driving';this.audio.cue('engage');this.onMessage?.('自动驾驶 · '+destination.name+' · 方向键 / WASD 随时接管');}
 cancelAutoDrive(reason='manual-takeover'){const status=this.autopilot?.status;if(!status||['idle','cancelled'].includes(status.phase))return;this.autopilot!.cancel(reason);if(reason==='manual-takeover'){this.audio.cue('cancel');this.onMessage?.('已切换为手动驾驶');}}
 propBlocked(x:number,z:number){return !!this.bambooCafe?.layout.blocked(x,z)||this.propObstacles.some(p=>{const dx=x-p.x,dz=z-p.z,c=Math.cos(p.heading),s=Math.sin(p.heading),lx=dx*c-dz*s,lz=dx*s+dz*c;return Math.abs(lx)<6.1&&lz> -2.4&&lz<3.3;});}
 get controlMode():'car'|'tank'|'bicycle'|'boat'|'walking'|'observer'|'aircraft'{return this.flight?.active?'aircraft':this.observer.active?'observer':this.leisure?.boat.active?'boat':this.bicycle?.active?'bicycle':this.walk?.active?'walking':this.tank?.active?'tank':'car';}
 get actor(){return this.leisure?.boat.active?this.leisure.actor:this.bicycle?.active?this.bicycle:this.walk?.active?{x:this.walk.x,z:this.walk.z,yaw:this.walk.yaw,speed:this.walk.speed}:this.state;}
 // Detail and lighting belong to the subject being viewed. Throttle costly
 // updates while turning the drone, without moving that detail to the eye.
 sceneFocus(){return this.observer.active?this.observer.focus:this.actor;}
 locationRoadName(){const p=this.sceneFocus(),n=this.collision.nearest(p.x,p.z);return n&&n.d<90?roadDisplayName(n.road)+(n.d>n.road.width/2+3?'周边':''):'城市风景';}
 parkedVehicleBlocks(x:number,z:number){
  const feet=this.walkingSurfaceHeight(x,z),groundY=this.carSurfaceHeight(this.state.x,this.state.z);
  if(vehicleBlocksPoint({...this.state,groundY,halfWidth:this.tank?.active?1.94:1.18,halfLength:this.tank?.active?3.55:2.7,height:this.tank?.active?2.5:CAR_BODY.height},x,z,feet))return true;
  return this.traffic?.cars.some(c=>vehicleBlocksPoint({...c,...CAR_BODY,groundY:this.traffic!.surfaceHeight(c)},x,z,feet))??false;
 }
 get vehicleMeshes(){return this.tank?.active?this.tank.meshes:this.carMeshes;}
 /** Headlights/rear light follow whichever vehicle is driven. Only positions
  * change here; the lights themselves stay enabled so no shader recompiles. */
 syncVehicleLightRig(){
  const tank=this.tank?.active?this.tank:null,root=tank?tank.root:this.car,rig=this.vehicleLightRig;
  rig.position.copyFrom(root.position);rig.rotation.copyFrom(root.rotation);
  const anchors=tank?TANK_HEADLIGHT_ANCHORS:this.carHeadlightAnchors;
  this.headlights.forEach((l,i)=>{const a=anchors[i];if(a&&(l.position.x!==a[0]||l.position.y!==a[1]||l.position.z!==a[2]))l.position.copyFromFloats(a[0],a[1],a[2]);});
 }
 private async initLeisure(){
  const response=await fetch(cityAssetUrl('leisure.json'));if(!response.ok)throw Error('湖畔休闲地点加载失败');
  const config=await response.json();
  if(config.cityId!==CITY_CONFIG.id||config.horizontalScale!==CITY_CONFIG.geography.scale||JSON.stringify(config.originWGS84)!==JSON.stringify(CITY_CONFIG.geography.originWGS84)||config.eastMetresPerDegree!==CITY_CONFIG.geography.eastMetresPerDegree||config.northMetresPerDegree!==CITY_CONFIG.geography.northMetresPerDegree||config.sites?.length!==1)throw Error('湖畔休闲坐标与城市不一致');
  const site=config.sites[0] as CityLeisureSite;
  for(const p of [site.dock.land,site.dock.berth,site.fishing,site.keeper,site.volunteer])if(!p||![p.x,p.z,p.height,p.yaw].every(Number.isFinite))throw Error('湖畔休闲地点无效');
  this.leisureView=createCityLeisureView(this.scene,site);
  const water=this.leisureWater=new CityLeisureWater(this.data,new Set(site.waterIds),this.collision,this.geography?.siteSurfaces,(x,z,feet)=>this.leisureView!.peopleBlocked(x,z,feet)||(this.propBlocked(x,z)&&Math.abs(feet-this.groundHeight(x,z))<2),(id,x,z,y)=>this.geography!.levels.heightForSourceRoad(id,x,z,y));
  let storage:Storage|null=null;try{storage=localStorage;}catch{}
  const pose=()=>{const w=this.walk!;return {x:w.x,z:w.z,yaw:w.yaw,height:this.walkingSurfaceHeight(w.x,w.z)};};
  this.leisure=new CityLeisureSession(site,(x,z,h)=>water.clear(x,z,h),{
   pose,walking:()=>!!this.walk?.active,paused:()=>this.paused||this.observer.active||!!this.flight?.active,busy:()=>this.leisureBusy(),
   clear:p=>Math.abs(this.walkingSurfaceHeight(p.x,p.z)-p.height)<.4&&this.walk!.clear(p.x,p.z),
   path:(a,b)=>{const n=Math.ceil(Math.hypot(a.x-b.x,a.z-b.z)/.15);let h=a.height;for(let i=1;i<=n;i++){const x=a.x+(b.x-a.x)*i/n,z=a.z+(b.z-a.z)*i/n,y=this.walkingSurfaceHeight(x,z);if(!this.walk!.clear(x,z)||Math.abs(y-h)>.48)return false;h=y;}return true;},
   board:()=>{this.walk!.active=false;this.walk!.speed=0;this.walk!.moving=false;this.state.speed=0;this.rider?.setEnabled(false);this.cancelAutoDrive('boat');this.drivingInput={throttle:0,steer:0,handbrake:false};this.keys.clear();this.view=0;},
   land:p=>{Object.assign(this.walk!,{x:p.x,z:p.z,yaw:p.yaw,active:true,speed:0,moving:false});this.walkSiteHint={id:'leisure:marina-deck',height:p.height};this.walkRoadHint={height:p.height,groundOnly:true};this.riderYaw=p.yaw;this.keys.clear();this.cull();},
   message:text=>this.onMessage?.(text),storage,storageKey:CITY_CONFIG.storage.namespace+'-leisure-v1'
  });
  this.data.landmarks.push({id:'leisure:'+site.id,name:site.name,x:site.dock.land.x,z:site.dock.land.z,height:0,area:'西湖湖滨',excludeRadius:0,detailCollision:true,arrival:site.arrival.point,arrivalRoadId:site.arrival.roadId,yaw:site.arrival.yaw,photoDistance:28,photoElevation:.4,photoTargetHeight:site.dock.land.height+1});
 }
 private walkingSurface(x:number,z:number):{id:string|null;height:number}{
  const surface=this.geography?this.geography.levels.sample(x,z,this.walkRoadHint).height:this.groundHeight(x,z),height=this.bambooCafe?.layout.floorAt(x,z,surface)??surface;
  if(Number.isFinite(this.bambooCafe?.layout.floorAt(x,z,NaN)))return {id:null,height};
  const n=this.collision.nearest(x,z,this.geography?height:undefined);
  // The authored road/pavement meshes sit above the terrain sampler. Place
  // the shoe sole on those surfaces, as the vehicle already does for wheels.
  const edge=n?n.d-n.road.width/2:Infinity;
  const pavement=n&&['trunk','primary','secondary','tertiary'].includes(n.road.kind)?2.4:1.2;
  const ground=height+(edge<=0?.105:edge<pavement?.065:0);
  return this.geography?.siteSurfaces?.walkAt(x,z,ground,this.walkSiteHint)??{id:null,height:ground};
 }
 walkingSurfaceHeight(x:number,z:number){return this.walkingSurface(x,z).height;}
 async toggleTank(){
  if(this.leisure?.active){this.onMessage?.('先靠岸下船或收竿，再返回车辆');return;}
  if(!this.ready||!this.tank||this.tank.loading||(this.paused&&!this.observer.active))return;
  if(this.bicycle?.active){this.onMessage?.('先停稳单车并按 F 下车，再回到汽车切换坦克');return;}
  if(this.walk?.active){this.onMessage?.('先走回车辆旁按 F 上车，再按 T 切换坦克');return;}
  this.cancelAutoDrive('vehicle-switch');if(this.observer.active)this.exitPhoto();this.state.speed=0;this.keys.clear();
  const active=!this.tank.active,request=++this.tankRequest;
  if(active){
   const n=this.collision.nearest(this.state.x,this.state.z,this.geography?this.carSurfaceHeight(this.state.x,this.state.z):undefined);if(!tankFootprintClear(this.state.x,this.state.z,this.state.yaw,(x,z)=>this.actorCollision(x,z)||this.propBlocked(x,z))){
    if(!n||!tankFootprintClear(n.x,n.z,n.yaw,(x,z)=>this.actorCollision(x,z)||this.propBlocked(x,z))){this.onMessage?.('这里太窄，请到宽阔道路后切换坦克');return;}
    this.state.x=n.x;this.state.z=n.z;this.state.yaw=n.yaw;
   }
   this.onMessage?.('正在准备坦克');try{await this.tank.load();}catch(error){console.error('Tank asset:',error);this.onMessage?.('坦克素材加载失败，仍可驾驶轿车；按 T 重试');return;}
   if(request!==this.tankRequest||this.scene.isDisposed)return;
   if(!tankFootprintClear(this.state.x,this.state.z,this.state.yaw,(x,z)=>this.actorCollision(x,z)||this.propBlocked(x,z))){this.onMessage?.('坦克已就绪，请到开阔路段后再按 T');return;}
   if(this.walk?.active||this.observer.active){this.onMessage?.('坦克已准备好，返回车辆后按 T 切换');return;}
  }
  this.tank.setActive(active);this.car.setEnabled(!active);this.state.speed=0;this.state.steer=0;this.view=0;this.cameraYaw=this.state.yaw;
  this.tank.setPose(this.state.x,this.carSurfaceHeight(this.state.x,this.state.z),this.state.z,this.state.yaw);this.syncVehicleLightRig();
  this.vehicleReflections?.setEnabled(!active&&this.reflectionsEnabled&&this.graphicsProfile.vehicleProbe);this.keys.clear();this.cull();
  this.onMessage?.(active?'坦克 · WASD 驾驶 · Q/E 炮塔 · 空格开炮 · T 换回轿车':'已换回轿车 · F 下车 / T 坦克');
 }
 async ensureRider():Promise<boolean>{
  if(this.rider)return true;if(this.riderPending)return this.riderPending;
  this.riderLoading=true;
  this.riderPending=(async()=>{try{
   const rider=await createCityRider(this.scene);
   if(this.scene.isDisposed){rider.dispose();return false;}
   this.rider=rider;return true;
  }catch(error){console.error('Rider asset:',error);this.onMessage?.('角色加载失败，仍可驾驶；按 F 或“重试角色”重试');return false;}
  finally{this.riderLoading=false;this.riderPending=null;}})();
  return this.riderPending;
 }
 private restoreBicycleParking(){
  if(!this.bicycle)return;
  let storage:Storage|null=null;try{storage=localStorage;}catch{}
  const g=CITY_CONFIG.geography;
  this.bicycleParking=new CityBicycleParking(this.bicycle,storage,{city:CITY_CONFIG.id,key:CITY_CONFIG.storage.namespace+'-bicycle-parking-v1',projection:JSON.stringify([g.originWGS84,g.eastMetresPerDegree,g.northMetresPerDegree,g.scale]),extent:this.data.meta.extent});
  const result=this.bicycleParking.restore();
  if(result==='parked')this.onMessage?.('已恢复停放的单车 · 走回单车旁按 N 骑行');
  else if(result==='blocked'||result==='invalid')this.onMessage?.('原单车停放点已不适用，本次收起；可在安全公共道路按 N 取车');
 }
 private checkpointBicycleParking(){
  return this.bicycleParking?.checkpoint()!==false;
 }
 private bicycleSurface(x:number,z:number,height:number):BicycleSurface{
  const base=this.geography?.levels.sample(x,z,{...this.walkRoadHint,height,groundOnly:this.walkRoadHint?.groundOnly??!this.walkRoadHint}).height??this.groundHeight(x,z);
  const road=this.collision.nearest(x,z,base),edge=road?road.d-road.road.width/2:Infinity;
  const ground=base+(edge<=0?.105:edge<1.2?.065:0);
  const floor=this.geography?.siteSurfaces?.walkAt(x,z,ground,{id:this.walkSiteHint?.id??null,height})??{id:null,height:ground};
  const h=floor.height;
  if(this.leisureView?.peopleBlocked(x,z,h))return {height:h,blocked:'obstacle'};
  if(this.siteAccessBlocked(x,z,h,'bicycle'))return {height:h,blocked:'restricted-road'};
  const reason=this.collision.blockReason(x,z,h,BICYCLE_BODY.height,!!floor.id,'bicycle');
  if(reason)return {height:h,blocked:reason==='restricted-road'?'restricted-road':reason==='water'?'water':'obstacle'};
  if(this.propBlocked(x,z)||this.canopy?.trunkNear(x,z)||this.geography?.siteSurfaces?.blocked(x,z,h,BICYCLE_BODY.height)||Number.isFinite(this.bambooCafe?.layout.floorAt(x,z,NaN)))return {height:h,blocked:'obstacle'};
  if(vehicleBlocksPoint({...this.state,groundY:this.carSurfaceHeight(this.state.x,this.state.z),...(this.tank?.active?{halfWidth:1.94,halfLength:3.55,height:2.5}:CAR_BODY)},x,z,h)||this.traffic?.cars.some(c=>vehicleBlocksPoint({...c,...CAR_BODY,groundY:this.traffic!.surfaceHeight(c)},x,z,h)))return {height:h,blocked:'obstacle'};
  if(this.pedestrians?.people.some(p=>Math.hypot(p.x-x,p.z-z)<.4&&Math.abs(this.pedestrians!.heightAt(p.x,p.z)-h)<1.5))return {height:h,blocked:'obstacle'};
  return {height:h,blocked:null};
 }
 async toggleBicycle(){
  if(this.leisure?.active){this.onMessage?.('先靠岸下船或收竿，再使用单车');return;}
  const b=this.bicycle,w=this.walk;
  if(!this.ready||this.paused||this.observer.active||!b||!w||this.walkingTransition)return;
  if(b.active){this.dismountBicycle();return;}
  if(!w.active){this.onMessage?.('先停稳汽车并按 F 下车，再按 N 取出试骑单车');return;}
  if(!this.ebikes?.playerBicycleReady){this.onMessage?.('单车素材尚未就绪，请稍后再试');return;}
  const result=b.mount({x:w.x,z:w.z,yaw:w.yaw,height:this.walkingSurfaceHeight(w.x,w.z)},(x,z)=>w.clear(x,z));
  if(result!=='ok'){this.onMessage?.(result==='far'?`单车停在 ${Math.round(Math.hypot(w.x-b.x,w.z-b.z))} m 外，走回车旁按 N`:result==='restricted-road'?'这里禁止骑行，请到允许骑行的公共道路取车':'单车需要平整、开阔的岸上空间，请远离水边、台阶和车辆');return;}
  this.cancelAutoDrive('bicycle');w.active=false;w.speed=0;w.moving=false;this.rider?.setEnabled(false);this.state.speed=0;this.drivingInput={throttle:0,steer:0,handbrake:false};this.keys.clear();this.view=0;this.cull();
  const saved=this.checkpointBicycleParking();
  this.onMessage?.('单车试骑 · W 踩踏 / A D 转向 / S 或空格刹车 / F 下车 / C 远近镜头'+(saved?'':' · 浏览器暂不能保存单车状态'));
 }
 private dismountBicycle(){
  const b=this.bicycle,w=this.walk;if(!b?.active||!w)return;
  this.walkRoadHint={height:b.height};this.walkSiteHint={id:null,height:b.height};
  const p=b.dismount((x,z)=>w.clear(x,z));
  if(!p){this.onMessage?.(b.speed>.5?'先按 S 或空格刹停，再按 F 下车':'车旁空间不足，请到宽阔岸边下车');return;}
  Object.assign(w,{x:p.x,z:p.z,yaw:p.yaw,pitch:.06,speed:0,moving:false,active:true});this.walkFirstPerson=false;this.riderYaw=p.yaw;this.keys.clear();this.cull();this.vegetation();
  const saved=this.checkpointBicycleParking();
  this.onMessage?.('单车已停放 · N 再次骑行；也可收起后步行通过禁骑路段'+(saved?'':' · 浏览器暂不能保存停放位置'));
 }
 stowBicycle(){
  const w=this.walk,b=this.bicycle;if(this.paused||this.observer.active||!w?.active||!b?.deployed)return;
  if(!w.canEnter({x:b.x,z:b.z,yaw:b.yaw,speed:0,groundY:b.height},2,.85)||!b.stow({x:w.x,z:w.z,yaw:w.yaw,height:this.walkingSurfaceHeight(w.x,w.z)})){this.onMessage?.('走回单车旁，停稳下车后再收起');return;}
  const saved=this.checkpointBicycleParking();
  this.onMessage?.('单车已收起 · 可步行通过禁骑路段，在允许骑行处按 N 取出'+(saved?'':' · 浏览器暂不能保存单车状态'));
 }
 async toggleWalking(){
  if(this.leisure?.boat.active){this.leisure.dismount();return;}
  if(this.leisure?.fishingActive){this.leisure.cancelFishing();return;}
  if(this.bicycle?.active){this.dismountBicycle();return;}
  if(!this.walk||this.walkingTransition)return;
  this.walkingTransition=true;try{
  if(this.walk.active){if(!this.walk.canEnter(this.geography?{...this.state,groundY:this.carSurfaceHeight(this.state.x,this.state.z)}:this.state,this.tank?.active?7:5,this.tank?.active?3:1.9)){this.onMessage?.('走回车辆旁，按 F 上车');return;}this.walk.active=false;this.rider?.setEnabled(false);this.cameraYaw=this.state.yaw;this.onMessage?.('已上车 · C 切换驾驶镜头');}
  else{
   if(Math.abs(this.state.speed)>1){this.onMessage?.('先停稳，再按 F 下车');return;}
   if(!this.rider){this.onMessage?.('正在准备步行角色');if(!await this.ensureRider())return;}
   if(this.scene.isDisposed||this.observer.active||this.paused)return;
   this.walkRoadHint=this.geography?{height:this.carSurfaceHeight(this.state.x,this.state.z),roadId:this.carRoadHint?.roadId,groundOnly:this.carRoadHint?.groundOnly}:undefined;
   this.walkSiteHint=this.geography?{id:null,height:this.carSurfaceHeight(this.state.x,this.state.z)+.105}:undefined;
   if(!this.walk.exitCar(this.geography?{...this.state,groundY:this.carSurfaceHeight(this.state.x,this.state.z)}:this.state,this.tank?.active?3:1.9)){this.onMessage?.('车门旁需要留出空间，请到开阔处下车');return;}
   this.cancelAutoDrive('exit-car');this.state.speed=0;this.state.steer=0;this.drivingInput={throttle:0,steer:0,handbrake:false};this.walkFirstPerson=false;this.riderYaw=this.walk.yaw;
   this.onMessage?.(`${this.rider?.name??'角色'} · WASD 行走 / Shift 跑步 / 拖动环视 / 滚轮远近 / F 上车`);
  }
  this.keys.clear();this.cull();this.vegetation();
  }finally{this.walkingTransition=false;}
 }
 enterPhoto(m:Landmark){
  this.leisure?.suspend();
  if(this.bicycle?.active)this.bicycle.speed=0;
  this.flightRequest++;this.flight?.stop();
  this.cancelAutoDrive('observer');
  this.photoTarget=m;this.aerial=true;this.paused=true;this.keys.clear();
  const distance=m.photoDistance??(m.id==='civic'?380:m.height?m.height*1.65:320),elevation=m.photoElevation??.32;
  const focus={x:m.x,y:m.photoTargetHeight??(this.groundHeight(m.x,m.z)+m.height*.38),z:m.z};
  this.observer.begin(focus,distance,m.photoAngle??.65,elevation);this.observer.step(this.keys,0,this.groundHeight,this.data.meta.extent);
  this.cull();this.vegetation();this.onMessage?.('无人机 · WASD 平移 / 方向键转头 / Q E 升降 / 拖动环绕 / Shift 拖移 / G 或 F 返回');
 }
 async toggleFlight(){
  if(this.leisure?.active){this.onMessage?.('先靠岸下船，再使用飞机；无人机仍可观景');return;}
  const flight=this.flight;if(!flight||!this.ready||!this.observer.active||this.photoTarget?.id==='car')return;
  if(flight.active||flight.loading){this.returnFromFlight();return;}
  const request=++this.flightRequest;this.keys.clear();this.drag=false;
  try{await flight.load();if(request!==this.flightRequest||!this.observer.active||this.scene.isDisposed)return;
   if(!flight.start(this.observer.pose(),this.observer.yaw)){this.onMessage?.('此处没有足够起飞空间，请移动无人机后重试');return;}
   this.paused=true;this.cull();this.onMessage?.('湾翼 · W/S 抬头俯冲 · A/D 侧倾 · 空格发射导弹 · X 减速 · B 无人机');
  }catch(error){console.error('Aircraft asset failed to load',error);if(request===this.flightRequest)this.onMessage?.('飞机加载失败，已保留无人机模式，可按 B 重试');}
 }
 returnFromFlight(reason?:'recovered'|'boundary'){
  const flight=this.flight;if(!flight||(!flight.active&&!flight.loading&&!reason))return;
  this.flightRequest++;const p={...flight.sim.lastSafe};const wasLoaded=flight.loaded;
  flight.stop();this.keys.clear();this.drag=false;
  if(!wasLoaded)return;
  this.enterPhoto({id:'free-camera',name:'自由无人机',x:p.x-Math.sin(p.yaw)*25,z:p.z-Math.cos(p.yaw)*25,height:0,area:'城市全景',excludeRadius:0,arrival:[this.state.x,this.state.z],yaw:p.yaw,photoDistance:65,photoElevation:.22,photoAngle:-p.yaw,photoTargetHeight:p.y+18});
  this.onMessage?.(reason==='recovered'?'已返回无人机 · B 可再次飞行':reason==='boundary'?'已到城市边界 · 返回无人机观景':'已切换无人机 · B 进入飞机模式');
 }
 /** SHADOW_BIAS is authored for a 2048 map; the normal offset follows the texel when the quality preset shrinks it. */
 applyShadowBias(){const bias=this.overviewEffects?SHADOW_BIAS.aerial:SHADOW_BIAS.street;this.shadows.normalBias=bias.normal*2048/this.shadows.mapSize;this.shadows.bias=bias.depth;}
 aerialEffects(active:boolean){if(this.overviewEffects===active)return;this.overviewEffects=active;this.sun.orthoLeft=this.sun.orthoBottom=active?-1050:-260;this.sun.orthoRight=this.sun.orthoTop=active?1050:260;this.sun.shadowMaxZ=active?3200:1200;this.applyShadowBias();this.shadows.getShadowMap()!.refreshRate=active?12:1;this.shadows.getShadowMap()!.resetRefreshCounter();this.syncGraphicsPostEffects();this.cull();}
 toggleAerial(){if(this.observer.active){this.exitPhoto();return;}const s=this.actor;this.enterPhoto({id:'free-camera',name:'自由无人机',x:s.x,z:s.z,height:0,area:'城市全景',excludeRadius:0,arrival:[s.x,s.z],yaw:s.yaw,photoDistance:420,photoElevation:.42,photoAngle:.65,photoTargetHeight:this.groundHeight(s.x,s.z)+15});}
 exitPhoto(){this.flightRequest++;this.flight?.stop();this.aerialEffects(false);this.observer.active=false;this.aerial=false;this.photoTarget=null;this.paused=false;this.keys.clear();
  // Reselect lamps at the returning actor; nearby aerial slots can otherwise
  // remain latched to different poles within the 100 m assignment hysteresis.
  this.lampAssignments.fill(-1);this.lightTargets=[];this.lightTick=0;for(const light of this.streetLights)light.intensity=0;
  this.camera.position.set(this.state.x-Math.sin(this.state.yaw)*9,this.groundHeight(this.state.x,this.state.z)+3.5,this.state.z-Math.cos(this.state.yaw)*9);this.cull();this.vegetation();this.onMessage?.(this.leisure?.boat.active?'返回游船':this.bicycle?.active?'返回骑行':this.walk?.active?'返回步行探索':'返回驾驶');}
 setupReflections(){
  for(const material of this.scene.materials)if(material instanceof PBRMaterial&&/^car_glass(?:\.\d+)?$/.test(material.name)){material.albedoColor=new Color3(.012,.020,.027);material.metallic=0;material.roughness=.17;material.environmentIntensity=.55;material.specularIntensity=.65;material.clearCoat.isEnabled=false;}
  for(const material of this.scene.materials){if(!(material instanceof PBRMaterial))continue;if(material.name==='roadline')material.zOffset=-2;if(!this.carMeshes.some(mesh=>mesh.material===material)&&/^carpaint(?:\.\d+)?$/.test(material.name)){material.albedoColor=new Color3(.028,.074,.093);material.environmentIntensity=.75;material.metallic=.52;material.roughness=.31;material.specularIntensity=.65;}}
  for(const material of this.scene.materials){if(material instanceof PBRMaterial&&material.name==='asphalt'){material.reflectionTexture=this.mirror;material.metallic=.025;material.roughness=1.0;const n=128,orm=new Uint8Array(n*n*3),normal=new Uint8Array(n*n*3);for(let y=0;y<n;y++)for(let x=0;x<n;x++){const k=(y*n+x)*3,r=Math.sin(x*127.1+y*311.7)*43758.54,f=r-Math.floor(r),wet=Math.sin(x*.09)*Math.cos(y*.07);orm[k]=255;orm[k+1]=Math.round(235+wet*16);orm[k+2]=255;normal[k]=128+(f-.5)*22;normal[k+1]=128+(f-.5)*15;normal[k+2]=253;}material.metallicTexture=RawTexture.CreateRGBTexture(orm,n,n,this.scene,true,false);material.useRoughnessFromMetallicTextureGreen=true;material.useRoughnessFromMetallicTextureAlpha=false;material.bumpTexture=RawTexture.CreateRGBTexture(normal,n,n,this.scene,true,false);material.bumpTexture.level=.10;}
   if(material instanceof PBRMaterial&&!this.carMeshes.some(mesh=>mesh.material===material)&&/^carpaint(?:\.\d+)?$/.test(material.name)){material.clearCoat.isEnabled=true;material.clearCoat.intensity=.62;material.clearCoat.roughness=.23;}}
  const waterMeshes=this.scene.meshes.filter(m=>m.name==='terrain_water'||/^terrain_water_-?\d+_-?\d+_water$/.test(m.name));if(this.coastal)this.bayWater=createBayWater(this.scene,this.waterMirror,waterMeshes,this.coastal.manifest,{extendHorizon:CITY_CONFIG.water.southernOcean,flattenWater:CITY_CONFIG.id==='shenzhen',waterBodies:CITY_CONFIG.id==='hangzhou'?this.data.water.map(w=>{if(w.height===undefined)throw new Error('杭州水体缺少独立水位');return {...w,height:w.height};}):undefined});for(const light of this.headlights)light.excludedMeshes.push(...waterMeshes);

 }
 setupSigns(){
  // Signs are placed at actual major-road points, never at arbitrary world rows.
  let count=0;for(const road of this.data.roads){if(road.points.length<4||!['primary','trunk'].includes(road.kind)||road.name.includes('辅'))continue;const a=road.points[0],b=road.points[1];if(Math.abs(a[0]-this.data.spawn.x)>650||Math.abs(a[1]-this.data.spawn.z)>700)continue;if(count++>8)break;
   // The artwork belongs only on the traffic-facing side. Rendering the same
   // textured plane from behind mirrors both the Chinese and Latin lettering.
   const sign=MeshBuilder.CreatePlane('direction-sign',{width:8,height:2,sideOrientation:Mesh.FRONTSIDE},this.scene);const mat=new StandardMaterial('wayfinding',this.scene);
   if(CITY_CONFIG.id==='hangzhou'){
    // In-game wayfinding artwork based on the road it is placed above.
    const texture=new DynamicTexture('wayfinding-'+road.id,{width:512,height:128},this.scene,true);
    const context=texture.getContext();context.fillStyle='#07533f';context.fillRect(0,0,512,128);
    context.strokeStyle='#e8f5ee';context.lineWidth=4;context.strokeRect(8,8,496,112);
    context.fillStyle='#f5fff7';context.font='bold 48px sans-serif';
    context.fillText(roadDisplayName(road),34,84,370);context.fillText('↑',426,84);
    texture.update();mat.diffuseTexture=texture;
   }else mat.diffuseTexture=new Texture(cityAssetUrl("textures/sign-")+(b[0]<a[0]?'west':'east')+'.jpg',this.scene);
   mat.diffuseTexture.anisotropicFilteringLevel=8;
   // StandardMaterial adds emissiveTexture to emissiveColor. Keep the green
   // artwork in diffuseTexture so the unlit brightness multiplies its color.
   mat.specularColor=Color3.Black();mat.disableLighting=true;mat.emissiveColor=new Color3(.82,.82,.82);
   sign.material=mat;sign.position.set(a[0],6.8+(CITY_CONFIG.id==='hangzhou'?this.groundHeight(a[0],a[1]):0),a[1]);sign.rotation.y=Math.atan2(b[0]-a[0],b[1]-a[1])+Math.PI;sign.isPickable=false;
  }
 }
 cull(){const p=this.sceneFocus();this.sitePathView?.update(p.x,p.z);this.lastCull.set(p.x,0,p.z);const shadowDistance=this.overviewEffects?1800:800;this.sun.position.set(p.x-this.sun.direction.x*shadowDistance,this.groundHeight(p.x,p.z)-this.sun.direction.y*shadowDistance,p.z-this.sun.direction.z*shadowDistance);this.facadeStream?.update(p.x,p.z,this.debugFacades,this.overviewEffects?250:0);const traffic=this.traffic?.meshes.flat()??[];const casters:AbstractMesh[]=[...(this.flight?.active?this.flight.meshes:[]),...this.vehicleMeshes.filter(m=>m.metadata?.castsShadows!==false),...(this.walk?.active?this.rider?.meshes??[]:[]),...traffic,...(this.pedestrians?.casters??[])];const reflect:AbstractMesh[]=[...(this.sitePathView?.meshes.filter(m=>m.isEnabled())??[]),...(this.flight?.active?this.flight.meshes:[]),...(this.mountains?.meshes??[]),...this.vehicleMeshes,...(this.walk?.active?this.rider?.meshes??[]:[]),...this.landmarks,...this.coastalHorizon.flatMap(h=>h.mesh?[h.mesh]:[]),...traffic,...(this.buildingSigns?.meshes??[])];const sky=this.scene.getMeshByName('atmosphere');if(sky)reflect.push(sky);
  // Base buildings are already loaded. Aerial views retain their original
  // roofs, UV2 facade styles and glass; normal frustum culling limits draws.
  // Extra far geometry does not enter the existing shadow/reflection radii.
  for(const b of this.blocks){const d=b.bounds?Math.hypot(Math.max(b.bounds.minX-p.x,0,p.x-b.bounds.maxX),Math.max(b.bounds.minZ-p.z,0,p.z-b.bounds.maxZ)):Math.hypot(p.x-b.x,p.z-b.z),r=this.compatibleRange;b.mesh.setEnabled((!b.detail||this.debugFacades)&&(d<(b.detail?700:r?.visible??(b.road?2500:3300))||(!r&&this.overviewEffects&&!b.detail&&(!b.road||b.mesh.name.endsWith('_asphalt')))));if(d<(r?(this.overviewEffects?r.overviewShadow:r.streetShadow):(this.overviewEffects?1650:520))&&!b.road&&!b.water)casters.push(b.mesh);if(d<(r?.reflection??1400)&&!b.road&&!b.water)reflect.push(b.mesh);}
  for(const m of this.landmarks){const center=m.getBoundingInfo().boundingBox.centerWorld;if(Vector3.Distance(center,new Vector3(p.x,0,p.z))<(this.overviewEffects?1650:700))casters.push(m);}
  casters.push(...(this.groundRelief?.shadowMeshes(p.x,p.z,this.overviewEffects?1450:650)??[]));casters.push(...(this.landscape?.casters??[]));casters.push(...(this.canopy?.casters??[]));casters.push(...(this.rooftops?.casters??[]));for(const m of this.facadeStream?.shadowMeshes??[])casters.push(m);

  for(const light of this.windowLights){light.intensity=0;light.setEnabled(false);}
  this.shadows.getShadowMap()!.renderList=casters;if(this.aerial)this.shadows.getShadowMap()!.resetRefreshCounter();
  // Contact-shading depth/normal buffer: only meshes whose bounds reach into
  // the AO range (terrain and roads qualify through their large radii). The
  // shadow casters' 520 m radius is deliberately not reused: every mesh here
  // is drawn a second time. Vehicles and pedestrians are thin-instanced with
  // lagging bounds, so they are always in; the sky never is.
  const gbuffer=this.scene.geometryBufferRenderer;
  if(gbuffer){if(this.overviewEffects||!this.graphicsProfile.ao)gbuffer.renderList=[];else{const reach=STREET_AO.maxZ+STREET_AO.listMargin,near=new Set<AbstractMesh>([...this.vehicleMeshes,...(this.walk?.active?this.rider?.meshes??[]:[]),...traffic,...(this.pedestrians?.casters??[])]);for(const m of this.scene.meshes){if(near.has(m)||m===sky||!m.isEnabled()||!m.isVisible||!m.subMeshes?.length)continue;const s=m.getBoundingInfo().boundingSphere;if(Math.hypot(s.centerWorld.x-p.x,s.centerWorld.z-p.z)-s.radiusWorld<reach)near.add(m);}gbuffer.renderList=[...near];}}
  // A detail landmark can contain asphalt: never draw a material into its own texture.
  this.mirror.renderList=reflect.filter(m=>!m.material?.hasTexture(this.mirror));this.waterMirror.renderList=reflect.filter(m=>!m.material?.hasTexture(this.waterMirror));
  this.localLighting?.update(0,this.camera.position,true);
 }
 localLights(dt:number){
  this.lightTick-=dt;const p=this.sceneFocus();
  if(this.lightTick<=0){this.lightTick=.25;
   const sorted=this.lampData.map((l,id)=>({id,d:Math.hypot(l[0]-p.x,l[1]-p.z)})).filter(q=>q.d<120).sort((a,b)=>a.d-b.d);
   for(let i=0;i<this.streetLights.length;i++){
    const old=this.lampAssignments[i],lamp=this.lampData[old],d=lamp?Math.hypot(lamp[0]-p.x,lamp[1]-p.z):Infinity;
    // Keep identity across ranking changes; replace only an expired slot.
    if(d>100&&this.streetLights[i].intensity<1)this.lampAssignments[i]=sorted.find(q=>!this.lampAssignments.includes(q.id))?.id??-1;
   }
   this.lightTargets=this.lampAssignments.map(id=>{const l=this.lampData[id],d=l?Math.hypot(l[0]-p.x,l[1]-p.z):Infinity;return {position:l?new Vector3(l[0]-l[2]*1.5,this.groundHeight(l[0],l[1])+8.2,l[1]-l[3]*1.5):Vector3.Zero(),power:(this.night?360:this.lightMode==='day'?0:75)*clamp((108-d)/30,0,1)};});
  }
  this.streetLights.forEach((l,i)=>{const t=this.lightTargets[i];if(!t)return;const changing=Vector3.DistanceSquared(l.position,t.position)>1;if(changing&&l.intensity<1)l.position.copyFrom(t.position);const target=changing?0:t.power;l.intensity+=(target-l.intensity)*(1-Math.exp(-dt*6));l.range=46;});
 }


 vegetation(){
  const focus=this.sceneFocus();this.lastVegetation.set(focus.x,0,focus.z);this.lastLandscapeAerial=this.overviewEffects;
  this.landscape?.update(focus.x,focus.z,this.overviewEffects,true);this.canopy?.update(focus.x,focus.z,this.overviewEffects,true);this.rooftops?.update(focus.x,focus.z,this.overviewEffects,true);
  const plants=new Set([...(this.landscape?.meshes??[]),...(this.canopy?.meshes??[]),...(this.rooftops?.meshes??[])]),shadow=this.shadows.getShadowMap()!;
  shadow.renderList=[...(shadow.renderList??[]).filter(m=>!plants.has(m)),...(this.landscape?.casters??[]),...(this.canopy?.casters??[]),...(this.rooftops?.casters??[])];shadow.resetRefreshCounter();
  this.localLighting?.update(0,this.camera.position,true);
 }
 setLightMode(mode:'sunset'|'night'|'day'){
  this.lightMode=mode;this.night=mode==='night';this.skyMat.setFloat('night',this.night?1:0);this.skyMat.setFloat('daylight',mode==='day'?1:0);
  this.architecture.setMode(mode);this.facadeDiversity.setMode(mode);this.rooftops?.setMode(mode);this.ambient?.setMode(mode);this.signage?.setMode(mode);this.buildingSigns?.setNight(this.night);this.signals?.setNight(this.night);
  if(this.cinematic)this.cinematic.setMode(mode);else applyCityLightBalance(this,mode);
  this.roadSurface?.setMode(mode);this.rainPuddles?.setMode(mode);this.rainWeather?.setMode(mode);this.bayWater?.setMode(mode);this.publicLighting?.setMode(mode);this.lightTick=0;
  setLandscapeLightingMode(this.scene,mode);this.sportDetails?.setMode(mode);
  for(const light of this.headlights)light.intensity=mode==='day'?20:250;
  for(const m of this.scene.materials){
   if(m instanceof PBRMaterial&&/^lamp(?:\.\d+)?$/.test(m.name))m.emissiveIntensity=mode==='day'?0:1;
   // Dedicated civic materials retain the photographed blue roof/red-yellow
   // towers. Only the underside and eave fixtures receive night illumination.
   if(m instanceof PBRMaterial&&/^civic_(?:eave_light|flood_light)(?:\.\d+)?$/.test(m.name))m.emissiveIntensity=mode==='day'?0:mode==='night'?2.1:.55;
   if(m instanceof PBRMaterial&&/^civic_soffit(?:\.\d+)?$/.test(m.name))m.emissiveIntensity=mode==='day'?0:mode==='night'?.45:.08;
   if(m instanceof StandardMaterial&&m.name==='wayfinding'){const brightness=mode==='day'?.95:mode==='night'?.60:.82;m.emissiveColor.copyFromFloats(brightness,brightness,brightness);}
  }
  this.bambooLook?.setMode(mode);this.bayparkLook?.setMode(mode);this.localLighting?.setMode(mode);
  this.bambooCafe?.setMode(mode);this.bambooCorridor?.setMode(mode);
  this.syncGraphicsPostEffects();this.cull();this.shadows.getShadowMap()?.resetRefreshCounter();this.mirror.resetRefreshCounter();this.waterMirror.resetRefreshCounter();
  this.onMessage?.({sunset:`${CITY_COPY.sunset} · L 切换夜色`,night:`月下${CITY_COPY.city} · L 切换白天`,day:'白天 · L 切换日落'}[mode]);
 }
 toggleLight(){this.setLightMode(this.lightMode==='sunset'?'night':this.lightMode==='night'?'day':'sunset');}
 setWeather(weather:CityWeather){
  if(this.weather===weather)return;
  this.weather=weather;
  this.roadSurface?.setWeather(this.raining);this.rainPuddles?.setWeather(this.raining);
  this.rainWeather?.setWeather(weather);
  this.mirror.resetRefreshCounter();this.waterMirror.resetRefreshCounter();
  this.onMessage?.(CITY_WEATHER_LABELS[weather]);
 }
 toggleRain(){this.setWeather(this.raining?'clear':'rain');}
 resetRoad(){if(!this.ready)return;if(this.leisure?.active){this.onMessage?.('先靠岸下船或收竿，再使用车辆恢复');return;}if(this.bicycle?.active){this.onMessage?.('单车请先刹停，按 F 安全下车；汽车仍停在原处');return;}this.bicycle?.clearDeployment();this.checkpointBicycleParking();this.debugEpoch++;if(this.walk?.active)this.walk.active=false;this.cancelAutoDrive('reset-road');const n=this.collision.nearest(this.state.x,this.state.z,this.geography?this.carSurfaceHeight(this.state.x,this.state.z):undefined,'motorcar');if(n){this.state.x=n.x;this.state.z=n.z;this.state.yaw=n.yaw;this.state.speed=0;this.state.steer=0;this.cameraYaw=n.yaw;this.onMessage?.('已回到 '+roadDisplayName(n.road));}else this.travel(this.data.landmarks.find(m=>m.id===(CITY_CONFIG.id==='hangzhou'?CITY_CONFIG.missionPlaces.legacyDinner:'baypark'))!);}
 travel(m:Landmark){
  const arrivalRoad=m.arrivalRoadId?this.data.roads.find(r=>r.id===m.arrivalRoadId):this.collision.nearest(...m.arrival)?.road;
  if(arrivalRoad&&!roadAllows(arrivalRoad,'motorcar').allowed){this.onMessage?.('这里需步行进入，请选择周边公共道路停车点');return false;}
  let surface=this.groundHeight(...m.arrival),hint:RoadHeightHint|undefined;
  if(this.geography){
   const arrival=m.arrivalRoadId?this.geography.levels.sourceArrival(m.arrivalRoadId,...m.arrival):this.geography.levels.sample(...m.arrival,{height:surface,groundOnly:true});
   if(!arrival){this.onMessage?.('这个地点的道路到达点已失效，请重新选择');return false;}
   surface=arrival.height;hint={height:surface,roadId:arrival.roadId??undefined,groundOnly:arrival.roadId===null};
  }
  if(this.baseStream&&!this.baseTravelCommit){
   const id=++this.baseTravelId;this.baseTravel={id,landmark:m};this.onMessage?.('正在读取目的地街区');
   void this.baseStream.request(this.baseView(m)).then(()=>{
    if(this.baseTravel?.id!==id||this.scene.isDisposed)return;
    if(!this.baseStream?.stats.ready){this.onMessage?.('目的地区域尚未满足加载条件，已保留当前位置');return;}
    this.baseTravelCommit=true;try{this.travel(m);}finally{this.baseTravelCommit=false;}
   }).catch(error=>this.onMessage?.('街区加载失败：'+String(error))).finally(()=>{if(this.baseTravel?.id===id)this.baseTravel=null;});
   return true;
  }
  this.leisure?.resetForTravel();this.bicycle?.clearDeployment();this.checkpointBicycleParking();this.debugEpoch++;this.carRoadHint=hint;this.walkRoadHint=undefined;if(this.walk)this.walk.active=false;this.cancelAutoDrive('debug-travel');if(this.observer.active)this.exitPhoto();this.state.x=m.arrival[0];this.state.z=m.arrival[1];this.state.yaw=m.yaw;this.state.speed=0;this.state.steer=0;this.cameraYaw=m.yaw;this.car.position.set(this.state.x,surface+.115,this.state.z);this.camera.position.set(this.state.x-Math.sin(m.yaw)*9,surface+4,this.state.z-Math.cos(m.yaw)*9);this.cull();this.vegetation();this.traffic?.place(this.state.x,this.state.z);this.pedestrians?.place(this.state.x,this.state.z);this.bambooCorridor?.update(this.time,this.state.x,this.state.z,false);this.onMessage?.('已抵达 '+m.name+' 周边道路');return true;}
 private nextVehicleImpact=0;
 private nextDrivingBarrierHint=0;
 private vehicleImpactPulse=0;
 resolveVehicleMotion(before:CarState,dt:number){
  if(Math.abs(this.state.speed)<=.02)return;
  const after={...this.state},tank=!!this.tank?.active;
  const shape=tank?{halfWidth:1.94,halfLength:3.55,height:2.5}:CAR_BODY;
  const from={...before,...shape,groundY:this.carSurfaceHeight(before.x,before.z)},to={...after,...shape,groundY:this.carSurfaceHeight(after.x,after.z)};
  let contact:ReturnType<typeof sweepVehicleContact>=null,other:NonNullable<DrivingWorld['traffic']>['cars'][number]|undefined;
  for(const c of this.traffic?.cars??[]){
   const hit=sweepVehicleContact(from,to,{...c,...CAR_BODY,groundY:this.traffic!.surfaceHeight(c)});
   if(hit&&(!contact||hit.fraction<contact.fraction)){contact=hit;other=c;}
  }
  // Keep original static-world and tank collision contracts. Vehicle contact
  // now resolves at the body surface instead of the 2.7g centre-distance circle.
  const steps=Math.max(1,Math.ceil(Math.abs(after.speed)*dt/.7));
  for(let i=1;i<=steps;i++){
   const fraction=Math.min(i/steps,contact?.fraction??1);
   const x=before.x+(after.x-before.x)*fraction,z=before.z+(after.z-before.z)*fraction;
   const f=Math.sign(after.speed)*(tank?3.4:1.45);
   if((this.geography&&this.carRoadHint&&Math.abs(this.carSurfaceHeight(x,z)-this.carRoadHint.height)>.7)||(tank&&!tankFootprintClear(x,z,after.yaw,(a,b)=>this.actorCollision(a,b)||this.propBlocked(a,b)))||this.actorCollision(x+Math.sin(after.yaw)*f,z+Math.cos(after.yaw)*f)||this.propBlocked(x,z)){
    this.state.x=before.x;this.state.z=before.z;this.state.distance=before.distance;this.state.speed=tank?0:-before.speed*.15;
    if(this.collision&&this.time>=this.nextDrivingBarrierHint){
     const bx=x+Math.sin(after.yaw)*f,bz=z+Math.cos(after.yaw)*f,reason=this.actorBlockReason(bx,bz);
     const text=reason==='restricted-road'?'前方道路限制机动车通行，请停车后按 F 下车':reason==='water'?'前方是水域，请沿岸行驶':null;
     if(text){this.nextDrivingBarrierHint=this.time+8;this.onMessage?.(text);}
    }
    return;
   }
   if(contact&&fraction>=contact.fraction)break;
  }
  if(!contact||!other)return;
  const t=contact.fraction;
  this.state.x=before.x+(after.x-before.x)*t;this.state.z=before.z+(after.z-before.z)*t;
  this.state.yaw=before.yaw+Math.atan2(Math.sin(after.yaw-before.yaw),Math.cos(after.yaw-before.yaw))*t;
  this.state.distance=before.distance+(after.distance-before.distance)*t;
  const speed=other.actualSpeed??other.speed;
  const impulse=vehicleImpulse(contact.normal,{x:Math.sin(after.yaw)*after.speed,z:Math.cos(after.yaw)*after.speed},
   {x:Math.sin(other.yaw)*speed,z:Math.cos(other.yaw)*speed},tank?6:1);
  this.state.speed=tank?0:impulse.a.x*Math.sin(this.state.yaw)+impulse.a.z*Math.cos(this.state.yaw);
  if(impulse.closing>.1)this.traffic!.applyImpact(other,impulse.b.x,impulse.b.z);
  if(impulse.closing>.35&&this.time>=this.nextVehicleImpact){
   this.nextVehicleImpact=this.time+.18;this.audio.impact(impulse.closing);
   this.vehicleImpactPulse=Math.max(this.vehicleImpactPulse,Math.min(.12,impulse.closing*.006));
  }
 }
 update(dt:number){
  this.time+=dt;if(this.geography){const q=this.geography.levels.sample(this.state.x,this.state.z,this.carRoadHint);this.carRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};}if(!this.paused)this.tank?.step(dt);
  if(this.flight?.active){const result=this.flight.step(this.keys,dt,performance.now());if(result==='recovered'||result==='boundary')this.returnFromFlight(result);else if(result==='crashed'){this.keys.clear();this.onMessage?.('飞机撞毁 · 3 秒后返回无人机');}}
  this.localLights(dt);const oldCarX=this.car.position.x,oldCarZ=this.car.position.z;if(!this.paused&&this.controlMode==='walking'&&!this.leisure?.fishingActive&&this.walk){const before={x:this.walk.x,z:this.walk.z};this.walk.step(this.keys,dt);if(this.walk.moving){const target=Math.atan2(this.walk.x-before.x,this.walk.z-before.z),delta=Math.atan2(Math.sin(target-this.riderYaw),Math.cos(target-this.riderYaw));this.riderYaw+=delta*(1-Math.exp(-dt*16));}}
  if(this.geography&&this.walk?.active){this.walkSiteHint=this.walkingSurface(this.walk.x,this.walk.z);const q=this.geography.levels.sample(this.walk.x,this.walk.z,this.walkRoadHint);this.walkRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};}
  if(this.walk&&this.rider){this.rider.setEnabled(this.walk.active&&(!this.walkFirstPerson||this.observer.active));this.rider.setPose({x:this.walk.x,y:this.walkingSurfaceHeight(this.walk.x,this.walk.z),z:this.walk.z,yaw:this.riderYaw,speed:this.paused?0:this.walk.speed},dt);}
  if(!this.paused&&!this.walk?.active&&!this.bicycle?.active&&!this.leisure?.boat.active){const n=this.collision.nearest(this.state.x,this.state.z,this.geography?this.carSurfaceHeight(this.state.x,this.state.z):undefined);this.offroad=!n||n.d>n.road.width/2+1;if(n&&n.d<40)this.roadName=roadDisplayName(n.road);
   const throttle=(this.keys.has('KeyW')||this.keys.has('ArrowUp')?1:0)-(this.keys.has('KeyS')||this.keys.has('ArrowDown')?1:0),steer=(this.keys.has('KeyD')||this.keys.has('ArrowRight')?1:0)-(this.keys.has('KeyA')||this.keys.has('ArrowLeft')?1:0);
   const manual={throttle,steer:this.tank?.active?steer:manualSteeringInput(steer,this.state.speed),handbrake:this.keys.has(this.tank?.active?'KeyX':'Space')};const status=this.autopilot?.status;
   this.drivingInput=status&&!['idle','cancelled'].includes(status.phase)?this.autopilot!.update(this.state,this.geography?(this.traffic?.cars??[]).filter(c=>Math.abs(this.traffic!.surfaceHeight(c)-this.carSurfaceHeight(c.x,c.z))<2.5):this.traffic?.cars??[],dt).input:manual;
   const phase=this.autopilot?.status.phase??'idle';if(phase!==this.previousAutoPhase){if(phase==='arrived'){this.audio.cue('arrival');this.onMessage?.('已自动停靠 · '+this.autopilot!.status.destination!.name);}if(phase==='blocked')this.onMessage?.('前方暂时无法通过，已停车 · 可以手动接管或重选路线');this.previousAutoPhase=phase;}
   const before={...this.state};if(this.tank?.active){stepTank(this.state,this.drivingInput,dt);this.tank.aim(this.keys,dt);if(this.keys.has('Space'))this.tank.fire();}else stepCar(this.state,this.drivingInput,dt);
   this.resolveVehicleMotion(before,dt);
   const impact=this.pedestrians?.collideVehicle({...before,groundY:this.carSurfaceHeight(before.x,before.z)},{...this.state,groundY:this.carSurfaceHeight(this.state.x,this.state.z)},this.tank?.active?'tank':'sports-car');
   if(impact?.hits){this.state.speed*=Math.pow(.97,Math.min(3,impact.hits));this.audio.impact(impact.peakSpeed);}
  }
  this.leisure?.step(this.leisureReelHeld?new Set([...this.keys,'Space']):this.keys,dt,!this.observer.active&&!this.flight?.active);
  if(this.leisure?.fishingActive&&this.walk){this.walk.speed=0;this.walk.moving=false;}
  if(this.leisure&&this.leisureView){this.leisureView.update(this.leisure,dt,this.paused);const p=this.sceneFocus();this.leisureView.root.setEnabled(Math.hypot(p.x-this.leisure.site.dock.land.x,p.z-this.leisure.site.dock.land.z)<700);}
  if(this.bicycle?.active&&!this.paused){
   this.bicycle.step(this.keys,dt);
   if(this.bicycle.barrier&&this.time>=this.nextBicycleHint){this.nextBicycleHint=this.time+3;this.onMessage?.(this.bicycle.barrier==='restricted-road'?'前方禁止骑行 · 刹停后按 F 下车步行':this.bicycle.barrier==='water'?'前方是水域 · 请沿岸上道路骑行':'前方空间或高差不足 · 请停稳下车绕行');}
  }
  if(this.geography&&this.bicycle?.active){const b=this.bicycle;this.walkSiteHint=this.walkingSurface(b.x,b.z);const q=this.geography.levels.sample(b.x,b.z,this.walkRoadHint);this.walkRoadHint={height:q.height,roadId:q.roadId??undefined,groundOnly:q.roadId===null};}
  if(this.ebikes)this.ebikes.playerBicycle=this.bicycle?.deployed?{...this.bicycle.pose,active:this.bicycle.active}:null;
  const s=this.state;{const f=this.sceneFocus();this.signals?.update(dt,f.x,f.z,this.overviewEffects);this.ebikes?.update(dt,f.x,f.z,this.overviewEffects,this.paused);}if(!this.paused){this.traffic?.update(dt,this.actor.x,this.actor.z);this.pedestrians?.update(dt,this.actor.x,this.actor.z);this.wheelSpin+=s.speed*dt/this.wheelRadius;for(const m of this.carMeshes)if(m.name.startsWith('wheel_')){m.rotation.x=this.wheelSpin;m.rotation.y=m.name.match(/wheel_[lr]f_/)?-s.steer:0;}else if(m.name.startsWith('brake_'))m.rotation.set(0,-s.steer,0);}const ground=this.carSurfaceHeight(s.x,s.z);this.car.position.set(s.x,ground+.115+Math.sin(this.time*7)*Math.min(.008,Math.abs(s.speed)*.0004),s.z);const front=this.carSurfaceHeight(s.x+Math.sin(s.yaw)*1.5,s.z+Math.cos(s.yaw)*1.5),rear=this.carSurfaceHeight(s.x-Math.sin(s.yaw)*1.5,s.z-Math.cos(s.yaw)*1.5);this.car.rotation.set(-Math.atan2(front-rear,3),s.yaw,-s.steer*s.speed*.0025);
  if(this.tank?.active)this.tank.setPose(s.x,ground,s.z,s.yaw);
  this.syncVehicleLightRig();
  if(!this.drag){this.viewReturn-=dt;if(this.viewReturn<=0){let d=s.yaw-this.cameraYaw;d=Math.atan2(Math.sin(d),Math.cos(d));this.cameraYaw+=d*(1-Math.exp(-dt*3));}}
  const f=this.tank?.active?(this.view===1?-5:this.view===2?-22:-13):this.view===1?0.75:this.view===2?-18:-8.6;const height=this.tank?.active?(this.view===1?4:this.view===2?11:5.2):this.view===1?1.35:this.view===2?9:1.75+this.cameraPitch*2;
  const target=new Vector3(s.x+Math.sin(s.yaw)*5,ground+(this.view===0?2.65:1.15),s.z+Math.cos(s.yaw)*5);
  const desired=new Vector3(s.x+Math.sin(this.cameraYaw)*f,ground+height,s.z+Math.cos(this.cameraYaw)*f);this.camera.position.x+=s.x-oldCarX;this.camera.position.z+=s.z-oldCarZ;this.camera.position=Vector3.Lerp(this.camera.position,desired,1-Math.exp(-dt*(this.view===1?20:9)));this.camera.setTarget(target);this.camera.fov=.80+Math.abs(s.speed)*.00045;if(this.flight?.active){
   const p=this.flight.sim.pose,shot=this.flight.camera;this.observer.focus={x:p.x,y:p.y,z:p.z};this.observer.yaw=p.yaw;
   this.camera.position.copyFrom(shot.eye);this.camera.setTarget(shot.target);this.camera.minZ=.5;this.camera.fov=.88;this.aerialEffects(p.y-this.groundHeight(p.x,p.z)>(this.overviewEffects?125:165));
  }else if(this.observer.active){
   this.observer.step(this.keys,dt,this.groundHeight,this.data.meta.extent);const p=this.observer.pose(),f=this.observer.focus;
   this.camera.position.set(p.x,p.y,p.z);this.camera.setTarget(new Vector3(f.x,f.y,f.z));this.camera.fov=.85;
   this.camera.minZ=observerNearClip(this.observer.distance,p.y,this.sceneryTop,this.photoTarget?.id==='car');
   this.aerialEffects(p.y-this.groundHeight(p.x,p.z)>(this.overviewEffects?125:165));
  }else if(this.leisure?.boat.active){
   const b=this.leisure.actor,eye=new Vector3(b.x,b.height+1.4,b.z),back=this.view===1?9:5.5;
   const desired=eye.add(new Vector3(-Math.sin(b.yaw)*back,2.3,-Math.cos(b.yaw)*back));let fraction=1;
   for(let t=.12;t<=1;t+=.08){const p=Vector3.Lerp(eye,desired,t);if(this.leisureWater?.volumeBlocked(p.x,p.z,p.y,.3)){fraction=Math.max(.1,t-.1);break;}}
   fraction=Math.min(fraction,this.canopy?.cameraFraction(eye,desired)??1);this.camera.position.copyFrom(Vector3.Lerp(eye,desired,fraction));this.camera.setTarget(eye.add(new Vector3(Math.sin(b.yaw)*2,-.5,Math.cos(b.yaw)*2)));this.camera.minZ=.12;this.camera.fov=.85;
  }else if(this.bicycle?.active){
   const b=this.bicycle,eye=new Vector3(b.x,b.height+1.65,b.z),back=this.view===1?7:4.8;
   const desired=eye.add(new Vector3(-Math.sin(b.yaw)*back,1.4,-Math.cos(b.yaw)*back));let fraction=1;
   for(let t=.12;t<=1;t+=.08){const p=Vector3.Lerp(eye,desired,t);if(this.walkingCameraCollision(p.x,p.y,p.z)){fraction=Math.max(.1,t-.1);break;}}
   fraction=Math.min(fraction,this.canopy?.cameraFraction(eye,desired)??1);this.camera.position.copyFrom(Vector3.Lerp(eye,desired,fraction));this.camera.setTarget(eye.add(new Vector3(Math.sin(b.yaw)*2,-.3,Math.cos(b.yaw)*2)));this.camera.minZ=.12;this.camera.fov=.85;
  }else if(this.walk?.active){
   const e=this.walk.eye,direction=new Vector3(Math.sin(this.walk.yaw)*Math.cos(this.walk.pitch),-Math.sin(this.walk.pitch),Math.cos(this.walk.yaw)*Math.cos(this.walk.pitch));
   const eye=new Vector3(e.x,e.y,e.z),desired=eye.subtract(direction.scale(this.walk.cameraDistance)).addInPlaceFromFloats(.35,.4,0);
   if(this.walkFirstPerson){this.camera.position.copyFrom(eye);this.camera.setTarget(eye.add(direction));}
   else{let distance=1;for(let t=.15;t<=1;t+=.07){const p=Vector3.Lerp(eye,desired,t);if(this.walkingCameraCollision(p.x,p.y,p.z)){distance=Math.max(.12,t-.1);break;}}distance=Math.min(distance,this.canopy?.cameraFraction(eye,desired)??1);this.camera.position.copyFrom(Vector3.Lerp(eye,desired,distance));this.camera.position.y=Math.max(this.camera.position.y,this.groundHeight(this.camera.position.x,this.camera.position.z)+.3);this.camera.setTarget(eye.add(direction.scale(.7)).addInPlaceFromFloats(0,-.55,0));}this.camera.minZ=.12;this.camera.fov=.88;
  }else if(this.view===1&&this.cockpit&&!this.tank?.active){
   const transform=this.car.computeWorldMatrix(true);this.camera.position.copyFrom(Vector3.TransformCoordinates(Vector3.FromArray(CITY_DRIVER_POSE.position),transform));this.camera.setTarget(Vector3.TransformCoordinates(Vector3.FromArray(CITY_DRIVER_POSE.lookAhead),transform));this.camera.minZ=CITY_DRIVER_POSE.nearZ;this.camera.fov=CITY_DRIVER_POSE.fov;
  }else this.camera.minZ=.75;
  if(!this.paused){this.vehicleImpactPulse*=Math.exp(-dt*12);}
  if(!this.paused&&this.vehicleImpactPulse>.0001&&!this.leisure?.boat.active&&!this.bicycle?.active&&!this.walk?.active&&!this.observer.active&&!this.flight?.active){this.camera.position.y+=Math.sin(this.time*65)*this.vehicleImpactPulse;}
  this.cockpit?.setActive(this.view===1&&!this.leisure?.boat.active&&!this.bicycle?.active&&!this.observer.active&&!this.walk?.active&&!this.tank?.active);this.cockpit?.update(s.speed,s.steer/.48,{night:this.night,distanceMetres:s.distance});
  const braking=this.drivingInput.handbrake||this.drivingInput.throttle*s.speed<-.1;this.tailLights?.update({braking,night:this.night,speed:s.speed,enabled:!this.tank?.active});this.audio.update({speed:s.speed,throttle:this.drivingInput.throttle,steer:s.steer,braking,paused:this.paused||!!this.bicycle?.active||!!this.leisure?.boat.active,cockpit:this.view===1&&!this.observer.active,offroad:this.offroad});

  // Vehicle highlights come from world lighting, never a camera-following fill.
  if(!this.tank?.active)this.vehicleReflections?.update(this.time);
  this.buildingSigns?.update(this.camera.position);
  const focus=this.sceneFocus(),detailMoving=Math.hypot(focus.x-this.previousDetailFocus.x,focus.z-this.previousDetailFocus.z)>.01;
  // Keep the original single reflection target and refresh cadence. Its plane
  // follows the local Hangzhou earth surface instead of Shenzhen's flat datum.
  if(this.geography)this.mirror.mirrorPlane.d=this.groundHeight(focus.x,focus.z)+.105;
  if(detailMoving)this.facadeStream?.noteFocusMotion();
  const detailSettled=this.detailWasMoving&&!detailMoving;
  this.previousDetailFocus={x:focus.x,z:focus.z};this.detailWasMoving=detailMoving;
  if(!this.overviewEffects||this.time>=this.nextDetailUpdate||detailSettled){
   this.nextDetailUpdate=this.time+.25;
   this.streetFurniture?.update(focus.x,focus.z,this.overviewEffects);this.bambooCorridor?.update(this.time,focus.x,focus.z,this.overviewEffects);this.rainPuddles?.update(focus.x,focus.z,this.camera.position.y-this.groundHeight(this.camera.position.x,this.camera.position.z));
   if(!this.overviewEffects){const d=this.sun.direction;this.sun.position.set(focus.x-d.x*800,this.groundHeight(focus.x,focus.z)-d.y*800,focus.z-d.z*800);}
   if(Math.hypot(focus.x-this.lastCull.x,focus.z-this.lastCull.z)>100||detailSettled)this.cull();
   if(Math.hypot(focus.x-this.lastVegetation.x,focus.z-this.lastVegetation.z)>22||this.lastLandscapeAerial!==this.overviewEffects)this.vegetation();
   this.publicLighting?.update(focus.x,focus.z);
  }
  this.rainWeather?.update(this.time,this.camera.position,focus.x,focus.z,this.camera.position.y-this.groundHeight(this.camera.position.x,this.camera.position.z));
  this.bayWater?.update(this.time,focus.x,focus.z);
  this.localLighting?.update(dt,this.camera.position);
  this.bambooCafe?.update(this.camera.position.x,this.camera.position.z,this.walk?.active?this.actor:null);
  const direction=this.camera.getForwardRay().direction,moving=Vector3.DistanceSquared(this.camera.position,this.reflectionEye)>.000001||Vector3.DistanceSquared(direction,this.reflectionDirection)>.0000001;
  if(moving||this.drag)this.reflectionMotionUntil=this.time+.22;
  if(this.reflectionsEnabled){const profile=this.graphicsProfile;for(const [texture,idleRate] of [[this.mirror,profile.roadIdleRate],[this.waterMirror,profile.waterIdleRate]] as const){const rate=this.time<this.reflectionMotionUntil?profile.mirrorMovingRate:idleRate;if(texture.refreshRate!==rate){texture.refreshRate=rate;texture.resetRefreshCounter();}}}
  this.reflectionEye.copyFrom(this.camera.position);this.reflectionDirection.copyFrom(direction);
  this.onTick?.(dt);
 }
 carPaintDiagnostics(){const m=this.carMeshes.map(m=>m.material).find(m=>m instanceof PBRMaterial&&/^carpaint(?:\.\d+)?$/.test(m.name)) as PBRMaterial|undefined;return m?{name:m.name,clearCoat:m.clearCoat.isEnabled,albedo:m.albedoColor.asArray(),environmentIntensity:m.environmentIntensity,roughness:m.roughness}:null;}

 profileControls(){const panel=document.createElement('div');panel.id='render-profile';panel.style.cssText='position:fixed;z-index:100;right:12px;top:140px;background:#102029ee;padding:12px;color:white;font:13px sans-serif;pointer-events:auto';for(const [name,change] of Object.entries({facades:(v:boolean)=>{this.debugFacades=v;this.cull();},shadows:(v:boolean)=>{this.scene.shadowsEnabled=v;},reflections:(v:boolean)=>{this.reflectionsEnabled=v;this.vehicleReflections?.setEnabled(v&&this.graphicsProfile.vehicleProbe&&!this.tank?.active);this.mirror.refreshRate=v?1:0;this.waterMirror.refreshRate=v?1:0;},ssao:(v:boolean)=>{if(v)this.scene.postProcessRenderPipelineManager.attachCamerasToRenderPipeline('contact-shading',this.camera);else this.scene.postProcessRenderPipelineManager.detachCamerasFromRenderPipeline('contact-shading',this.camera);},simulation:(v:boolean)=>{this.debugSimulation=v;}})){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=true;input.dataset.profile=name;input.onchange=()=>change(input.checked);label.append(input,name);label.style.display='block';panel.append(label);}document.body.append(panel);}
 diagnostics(){const i=this.instrumentation;return {sitePaths:this.sitePathView?.stats??null,baseStreaming:this.baseStream?.stats??null,baseSharedMaterials:this.baseMaterialCache?.stats??null,graphics:{quality:this.graphicsQuality,renderWidth:this.engine.getRenderWidth(),renderHeight:this.engine.getRenderHeight(),shadowSize:this.shadows.mapSize,mirrorSize:this.mirror.getSize().width,msaa:this.pipeline.samples,preset:this.graphicsProfile},shaders:{compiles:this.gpuInstrumentation.shaderCompilationTimeCounter.count,compileMs:+this.gpuInstrumentation.shaderCompilationTimeCounter.total.toFixed(1),lights:this.scene.lights.length,materials:this.scene.materials.length,parallelCompile:!!this.engine.getCaps().parallelShaderCompile},vehicleReflections:this.vehicleReflections?.stats(),pedestrianImpacts:this.pedestrians?.stats,sampleAreas:{bamboo:this.bambooLook?.stats(),baypark:this.bayparkLook?.stats(),lighting:this.localLighting?.stats()},bambooCorridor:this.bambooCorridor?.stats,depthPrecision:{near:this.camera.minZ,far:this.camera.maxZ,sceneryTop:this.sceneryTop},contactShading:{attached:!!this.ao&&this.ao.cameras.includes(this.camera),gbufferMeshes:this.scene.geometryBufferRenderer?.renderList?.length??null,...STREET_AO},reflectionFrames:{...this.reflectionFrames,current:this.renderFrames,roadRate:this.mirror.refreshRate,waterRate:this.waterMirror.refreshRate},updateMs:this.updateMs,renderSubmitMs:this.renderMs,gpuMs:this.gpuInstrumentation.gpuFrameTimeCounter.lastSecAverage/1e6,activeEvaluationMs:i.activeMeshesEvaluationTimeCounter.lastSecAverage,renderTargetsMs:i.renderTargetsRenderTimeCounter.lastSecAverage,drawCalls:i.drawCallsCounter.current,instantFps:this.engine.getFps(),renderFrames:this.renderFrames,hidden:document.hidden,facades:this.facadeStream?.stats,rooftops:this.rooftops?.stats??null,roofSurface:this.roofSurface?.stats(),ambient:this.ambient?.stats(),facadeDiversity:this.facadeDiversity?.stats(),coastalHorizon:this.coastalHorizon.map(h=>h.stats),distantCity:{strategy:"original-building-meshes",proxyMeshes:0,extraTextures:0,extraShadowDraws:0,extraReflectionDraws:0},detailFocus:{...this.sceneFocus()},aerial:this.aerial,observer:this.observer.status,loadedMeshes:this.scene.meshes.length,enabledMeshes:this.scene.meshes.filter(m=>m.isEnabled()).length};}
 performance(){const a=this.samples.slice(120),b=[...a].sort((x,y)=>x-y);const pct=(p:number)=>b[Math.floor((b.length-1)*p)]??0;const mean=a.reduce((s,v)=>s+v,0)/Math.max(1,a.length);return {...this.diagnostics(),cafe:this.bambooCafe?.stats,samples:a.length,meanFps:a.length?1000/mean:0,p50:pct(.5),p95:pct(.95),p99:pct(.99),over50ms:a.filter(v=>v>50).length,resolution:[this.engine.getRenderWidth(),this.engine.getRenderHeight()],meshes:this.scene.getActiveMeshes().length,triangles:this.scene.getActiveIndices()/3};}
}
