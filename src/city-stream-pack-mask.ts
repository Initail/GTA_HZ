import {TransformNode} from '@babylonjs/core/Meshes/transformNode.js';
import type {AssetContainer} from '@babylonjs/core/assetContainer.js';
/** A parent mask survives existing world's per-mesh culling. Merely disabling
 * far meshes would let the next cull re-enable them underneath near geometry. */
export function createPackMemberMask(container:AssetContainer,bindings:readonly {name:string;member:string}[]){
 const root=container.meshes[0],meshes=container.meshes.filter(m=>m.getTotalVertices()>0);
 if(!root||bindings.length!==meshes.length)throw Error('Physical pack mesh coverage mismatch');
 const byName=new Map(bindings.map(b=>[b.name,b.member]));
 if(byName.size!==bindings.length||new Set(meshes.map(m=>m.name)).size!==meshes.length||bindings.some(b=>!b.name||!b.member)||meshes.some(m=>!byName.has(m.name)||m.parent!==root))throw Error('Physical pack hierarchy or member identity changed');
 const groups=new Map<string,TransformNode>();
 for(const mesh of meshes){
  const id=byName.get(mesh.name)!;let group=groups.get(id);
  if(!group){group=new TransformNode('pack-member-'+id,container.scene);group.parent=root;group.setEnabled(false);container.transformNodes.push(group);groups.set(id,group);}
  // The inserted parent is identity under the unchanged GLB root. Local TRS,
  // frozen world matrices and the existing axis conversion stay unchanged.
  mesh.parent=group;
 }
 return {selectMembers(ids:readonly string[]){
  if(new Set(ids).size!==ids.length||ids.some(id=>!groups.has(id)))throw Error('Unknown or duplicate visible pack member');
  const visible=new Set(ids);for(const [id,group] of groups)group.setEnabled(visible.has(id));
 },memberCount:groups.size};
}
