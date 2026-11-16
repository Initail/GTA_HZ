/** Exact semantic snapshot shared by isolated static asset assemblers. */
import crypto from 'node:crypto';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
export function createGltfSnapshot(io){
async function snapshot(doc){
 const jsonDoc=await io.writeJSON(doc),json=jsonDoc.json;
 // Resolve texture indices to actual image bytes and sampler settings, so
 // document pool reindexing cannot hide material or texture changes.
 const materialValue=value=>{
  if(Array.isArray(value))return value.map(materialValue);
  if(!value||typeof value!=='object')return value;
  return Object.fromEntries(Object.entries(value).map(([key,v])=>{
   if(/texture$/i.test(key)&&v&&typeof v==='object'&&Number.isInteger(v.index)){
    const t=json.textures[v.index],im=json.images[t.source];
    if(!im.uri||!jsonDoc.resources[im.uri])throw Error('Expected self-contained candidate texture');
    return [key,{...v,index:{imageSha256:hash(jsonDoc.resources[im.uri]),sampler:json.samplers?.[t.sampler]??null}}];
   }
   return [key,materialValue(v)];
  }));
 };
 const materials=doc.getRoot().listMaterials();
 const meshes=doc.getRoot().listMeshes().map(m=>({name:m.getName(),primitives:m.listPrimitives().map(p=>({
  mode:p.getMode(),material:materialValue(json.materials?.[materials.indexOf(p.getMaterial())]??null),
  attributes:Object.fromEntries(p.listSemantics().sort().map(s=>{const a=p.getAttribute(s),v=a.getArray();return [s,{type:a.getType(),normalized:a.getNormalized(),componentType:a.getComponentType(),sha256:hash(Buffer.from(v.buffer,v.byteOffset,v.byteLength))}];})),
  indices:p.getIndices()?Array.from(p.getIndices().getArray()):null,
 }))}));
 const nodes=doc.getRoot().listNodes().filter(n=>n.getMesh()).map(n=>({name:n.getName(),mesh:n.getMesh().getName(),worldMatrix:n.getWorldMatrix()}));
 return {meshes,nodes};
}
return snapshot;
}
