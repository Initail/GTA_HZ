import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {NullEngine} from '@babylonjs/core/Engines/nullEngine.js';
import {Scene} from '@babylonjs/core/scene.js';
import {ImportMeshAsync} from '@babylonjs/core/Loading/sceneLoader.js';
import '@babylonjs/loaders/glTF/index.js';

const root = new URL('../../public/cities/hangzhou/', import.meta.url);
const engine = new NullEngine();
const scene = new Scene(engine);

async function load(path) {
  const bytes = new Uint8Array(await readFile(new URL(path, root)));
  return ImportMeshAsync(bytes, scene, {pluginExtension:'.glb', name:path.split('/').at(-1)});
}

try {
  const rider = await load('rider/rider.glb');
  assert.equal(rider.skeletons.length, 1);
  assert.ok(rider.meshes[0].getChildMeshes().some(mesh => mesh.skeleton));
  assert.deepEqual(rider.animationGroups.map(group => group.name).sort(), ['Rider_Idle','Rider_Run','Rider_Walk']);
  const walk = rider.animationGroups.find(group => group.name === 'Rider_Walk');
  const limb = walk.targetedAnimations.find(entry => entry.target.name === 'leg1').target;
  const rest = limb.rotationQuaternion.clone();
  walk.start(true);
  walk.goToFrame(walk.to * .25);
  assert.ok(Math.abs(limb.rotationQuaternion.x - rest.x) > .05);
  walk.stop();

  const first = await load('bamboo-cafe/characters/maid.glb');
  const second = await load('bamboo-cafe/characters/maid.glb');
  const third = await load('bamboo-cafe/characters/jk.glb');
  for (const imported of [first,second,third]) {
    assert.equal(imported.skeletons.length, 1);
    assert.ok(imported.meshes[0].getChildMeshes().some(mesh => mesh.getTotalVertices() > 0));
    assert.deepEqual(imported.animationGroups.map(group => group.name).sort(), ['CafeIdle','CafeWalk','CafeWave']);
  }
  assert.notEqual(first.skeletons[0], second.skeletons[0]);

  const tank = await load('tank/tank.glb');
  const nodes = new Map([...tank.meshes,...tank.transformNodes].map(node => [node.name,node]));
  assert.equal(nodes.get('tank_turret').parent, nodes.get('tank_root'));
  assert.equal(nodes.get('tank_barrel').parent, nodes.get('tank_turret'));
  const muzzle = nodes.get('tank_muzzle');
  assert.equal(muzzle.parent, nodes.get('tank_barrel'));
  assert.ok(muzzle.computeWorldMatrix(true).getTranslation().z > 4);
  console.log('Babylon.js imported all original replacement assets and animated the courier.');
} finally {
  scene.dispose();
  engine.dispose();
}
