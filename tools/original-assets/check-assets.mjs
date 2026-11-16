import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {NodeIO} from '@gltf-transform/core';

const assetRoot = new URL('../../public/cities/hangzhou/', import.meta.url);
const io = new NodeIO();

async function readAsset(directory, entry) {
  const url = new URL(directory + entry.file, assetRoot);
  const bytes = await readFile(url);
  assert.equal(bytes.byteLength, entry.bytes);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), entry.sha256);
  const document = await io.read(fileURLToPath(url));
  return document.getRoot();
}

function dimensions(root) {
  const lower = [Infinity, Infinity, Infinity];
  const upper = [-Infinity, -Infinity, -Infinity];
  for (const node of root.listNodes()) {
    for (const primitive of node.getMesh()?.listPrimitives() ?? []) {
      const matrix = node.getWorldMatrix(), vertices = primitive.getAttribute('POSITION').getArray();
      for (let i = 0; i < vertices.length; i += 3) {
        for (let axis = 0; axis < 3; axis++) {
          const value = matrix[axis] * vertices[i] + matrix[axis + 4] * vertices[i + 1] + matrix[axis + 8] * vertices[i + 2] + matrix[axis + 12];
          lower[axis] = Math.min(lower[axis], value);
          upper[axis] = Math.max(upper[axis], value);
        }
      }
    }
  }
  return {lower, upper};
}

function checkCharacter(root, name, height, clips) {
  const {lower, upper} = dimensions(root);
  assert.ok(Math.abs(lower[1]) < 0.015, `${name} floor ${lower[1]}`);
  assert.ok(Math.abs(upper[1] - height) < 0.06, `${name} height ${upper[1]}`);
  assert.equal(root.listSkins().length, 1);
  const [skin] = root.listSkins();
  const joints = skin.listJoints();
  assert.ok(joints.length >= 10);
  assert.equal(skin.getInverseBindMatrices().getCount(), joints.length);
  const skinnedNodes = root.listNodes().filter(node => node.getSkin() === skin);
  assert.equal(skinnedNodes.length, 1);
  for (const primitive of skinnedNodes[0].getMesh().listPrimitives()) {
    const positions = primitive.getAttribute('POSITION');
    const jointIndices = primitive.getAttribute('JOINTS_0');
    const weights = primitive.getAttribute('WEIGHTS_0');
    assert.equal(jointIndices.getCount(), positions.getCount());
    assert.equal(weights.getCount(), positions.getCount());
    assert.ok(jointIndices.getArray().every(value => value < joints.length));
    assert.ok(weights.getArray().every((value, index) => value === (index % 4 === 0 ? 1 : 0)));
  }
  assert.deepEqual(root.listAnimations().map(animation => animation.getName()).sort(), Object.keys(clips).sort());
  for (const animation of root.listAnimations()) {
    assert.ok(animation.listChannels().length >= 5, animation.getName());
    for (const channel of animation.listChannels()) {
      assert.ok(joints.includes(channel.getTargetNode()), channel.getTargetNode().getName());
      const sampler = channel.getSampler();
      const times = sampler.getInput().getArray();
      assert.equal(times[0], 0);
      assert.ok(Math.abs(times.at(-1) - clips[animation.getName()]) < 1e-5, animation.getName());
      const rotations = sampler.getOutput().getArray();
      assert.equal(rotations.length, times.length * 4);
      assert.ok(rotations.some((value, index) => index % 4 !== 3 && Math.abs(value) > 1e-3), channel.getTargetNode().getName());
    }
  }
  assert.equal(root.listTextures().length, 0);
}

const rider = JSON.parse(await readFile(new URL('rider/manifest.json', assetRoot)));
assert.equal(rider.license, 'CC-BY-4.0');
assert.ok(rider.gait.walk.authoredSpeed > 0 && rider.gait.run.authoredSpeed > rider.gait.walk.authoredSpeed);
checkCharacter(await readAsset('rider/', rider), 'rider', rider.height, {Rider_Idle: 2, Rider_Walk: rider.gait.walk.cycleSeconds, Rider_Run: rider.gait.run.cycleSeconds});

const cafe = JSON.parse(await readFile(new URL('bamboo-cafe/characters/manifest.json', assetRoot)));
assert.equal(cafe.license, 'CC-BY-4.0');
assert.deepEqual(cafe.staffAssignments, {zhixia: 'maid', wangshu: 'maid', xiaolan: 'jk'});
assert.deepEqual(cafe.models.map(model => model.id).sort(), ['jk','maid']);
for (const model of cafe.models) {
  checkCharacter(await readAsset('bamboo-cafe/characters/', model), model.id, model.height, {CafeIdle: 2, CafeWalk: 1.2, CafeWave: 1.25});
}

const tank = JSON.parse(await readFile(new URL('tank/manifest.json', assetRoot)));
assert.equal(tank.license, 'CC-BY-4.0');
const tankRoot = await readAsset('tank/', tank);
const nodes = new Map(tankRoot.listNodes().map(node => [node.getName(), node]));
assert.equal(nodes.get('tank_turret').getParentNode(), nodes.get('tank_root'));
assert.equal(nodes.get('tank_barrel').getParentNode(), nodes.get('tank_turret'));
assert.equal(nodes.get('tank_muzzle').getParentNode(), nodes.get('tank_barrel'));
assert.ok(nodes.get('tank_muzzle').getWorldTranslation()[2] > 4);
const {lower, upper} = dimensions(tankRoot);
assert.ok(Math.abs(lower[1]) < .02, 'tank floor');
assert.ok(upper[0] - lower[0] > 3 && upper[0] - lower[0] < 3.7, 'tank width');
assert.ok(upper[2] - lower[2] > 7.7 && upper[2] - lower[2] < 8.8, 'tank length');
assert.equal(tankRoot.listTextures().length, 0);
console.log('Asset contracts passed for rider, maid, cafe server and tank.');
