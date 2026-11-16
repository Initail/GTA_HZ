import {createHash} from 'node:crypto';
import {mkdir, writeFile} from 'node:fs/promises';
import {Document, NodeIO} from '@gltf-transform/core';

const output = new URL('../../artifacts/original-assets/cities/hangzhou/', import.meta.url);
const io = new NodeIO();
const credit = 'GTA_HZ contributors';
const license = 'CC-BY-4.0';
const licenseUrl = 'https://creativecommons.org/licenses/by/4.0/';
const source = 'Original procedural Hangzhou game art authored for this release. No external geometry, textures or motion.';
const provenance = {credit, license, licenseUrl, source};

const palette = {
  amber: [.80, .37, .05], chartreuse: [.55, .68, .055], silver: [.77, .79, .69],
  dark: [.046, .055, .062], charcoal: [.082, .10, .12], blue: [.065, .17, .25],
  skin: [.66, .36, .24], mauve: [.33, .087, .105], ink: [.051, .077, .11],
  mahogany: [.13, .055, .041], cream: [.83, .74, .56], green: [.10, .25, .22],
  sage: [.29, .37, .20], darkSage: [.13, .18, .10], steel: [.12, .16, .16],
  glass: [.16, .33, .39], lamp: [.81, .64, .31], red: [.48, .068, .049],
};

function newAsset(label) {
  const document = new Document();
  document.getRoot().getAsset().copyright = `2026 ${credit}. ${license} ${licenseUrl}`;
  document.getRoot().setExtras({...provenance, label});
  const buffer = document.createBuffer();
  const scene = document.createScene(label);
  const materials = new Map();
  function material(color) {
    if (!materials.has(color)) {
      materials.set(color, document.createMaterial(color)
        .setBaseColorFactor([...palette[color], 1])
        .setMetallicFactor(color === 'steel' ? .35 : .04)
        .setRoughnessFactor(color === 'glass' ? .22 : .72));
    }
    return materials.get(color);
  }
  function accessor(type, values, Type = Float32Array) {
    return document.createAccessor().setType(type).setArray(new Type(values)).setBuffer(buffer);
  }
  return {document, scene, material, accessor};
}

function builder(asset, name, skinned = false) {
  const meshes = new Map();
  function emit(color, points, center, joint = 0) {
    if (!meshes.has(color)) meshes.set(color, {positions: [], normals: [], joints: [], weights: []});
    const batch = meshes.get(color);
    for (let i = 1; i < points.length - 1; i++) {
      const [a, b, c] = [points[0], points[i], points[i + 1]];
      const u = b.map((value, axis) => value - a[axis]);
      const v = c.map((value, axis) => value - a[axis]);
      const raw = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]];
      const length = Math.hypot(...raw);
      if (length < 1e-8) continue;
      const inward = raw.reduce((sum, value, axis) => sum + value * (a[axis] - center[axis]), 0) < 0;
      const normal = raw.map(value => value / length * (inward ? -1 : 1));
      for (const point of inward ? [a, c, b] : [a, b, c]) {
        batch.positions.push(...point);
        batch.normals.push(...normal);
        if (skinned) {
          batch.joints.push(joint, 0, 0, 0);
          batch.weights.push(1, 0, 0, 0);
        }
      }
    }
  }
  function box(color, center, size, joint) {
    const corners = [[-1,-1,-1], [1,-1,-1], [1,-1,1], [-1,-1,1], [-1,1,-1], [1,1,-1], [1,1,1], [-1,1,1]]
      .map(point => point.map((value, axis) => center[axis] + value * size[axis] / 2));
    for (const face of [[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]) {
      emit(color, face.map(index => corners[index]), center, joint);
    }
  }
  function loft(color, center, profiles, sides, joint) {
    const rings = profiles.map(([y, width, depth, z = 0]) => Array.from({length: sides}, (_, i) => {
      const angle = (i + .5) * Math.PI * 2 / sides;
      return [center[0] + Math.sin(angle)*width, center[1] + y, center[2] + z + Math.cos(angle)*depth];
    }));
    const centroid = points => [0,1,2].map(axis => points.reduce((sum, point) => sum + point[axis], 0) / points.length);
    const first = rings[0], last = rings.at(-1);
    const middle = centroid([...first, ...last]);
    emit(color, first, middle, joint);
    emit(color, last, middle, joint);
    for (let i = 1; i < rings.length; i++) {
      const lower = rings[i - 1], upper = rings[i];
      const inside = centroid([...lower, ...upper]);
      for (let j = 0; j < sides; j++) {
        const next = (j + 1) % sides;
        emit(color, [lower[j], lower[next], upper[next], upper[j]], inside, joint);
      }
    }
  }
  function finish() {
    const mesh = asset.document.createMesh(name);
    let triangles = 0;
    for (const [color, batch] of meshes) {
      const primitive = asset.document.createPrimitive()
        .setAttribute('POSITION', asset.accessor('VEC3', batch.positions))
        .setAttribute('NORMAL', asset.accessor('VEC3', batch.normals))
        .setMaterial(asset.material(color));
      if (skinned) {
        primitive.setAttribute('JOINTS_0', asset.accessor('VEC4', batch.joints, Uint8Array))
          .setAttribute('WEIGHTS_0', asset.accessor('VEC4', batch.weights));
      }
      mesh.addPrimitive(primitive);
      triangles += batch.positions.length / 9;
    }
    return {mesh, triangles};
  }
  return {emit, box, loft, finish};
}

function makeAvatar(label, kind, height) {
  const asset = newAsset(label);
  const {document, scene, accessor} = asset;
  const scale = height / 1.78;
  const sized = values => values.map(value => value * scale);
  const joints = new Map();
  function joint(name, parent, translation) {
    const node = document.createNode(name).setTranslation(sized(translation));
    if (parent) joints.get(parent).node.addChild(node);
    else scene.addChild(node);
    joints.set(name, {node, index: joints.size});
  }
  joint('hips', null, [0,.94,0]);
  joint('spine', 'hips', [0,.17,0]);
  joint('head', 'spine', [0,.34,0]);
  for (const side of [-1, 1]) {
    joint('arm'+side, 'spine', [side*.23,.26,0]);
    joint('elbow'+side, 'arm'+side, [side*.035,-.255,0]);
    joint('leg'+side, 'hips', [side*.102,-.015,0]);
    joint('knee'+side, 'leg'+side, [0,-.425,0]);
    joint('ankle'+side, 'knee'+side, [0,-.405,0]);
  }
  const inverseBindMatrices = [];
  const skin = document.createSkin(label).setSkeleton(joints.get('hips').node);
  for (const {node} of joints.values()) {
    const [x, y, z] = node.getWorldTranslation();
    inverseBindMatrices.push(1,0,0,0, 0,1,0,0, 0,0,1,0, -x,-y,-z,1);
    skin.addJoint(node);
  }
  skin.setInverseBindMatrices(accessor('MAT4', inverseBindMatrices));

  const geometry = builder(asset, label, true);
  function position(name, local) {
    const base = joints.get(name).node.getWorldTranslation();
    return sized(local).map((value, axis) => base[axis] + value);
  }
  const box = (name, color, offset, size) => geometry.box(color, position(name, offset), sized(size), joints.get(name).index);
  const loft = (name, color, offset, rings, sides = 10) => geometry.loft(color, position(name, offset), rings.map(sized), sides, joints.get(name).index);

  const rider = kind === 'rider';
  const server = kind === 'jk';
  const cloth = rider ? 'chartreuse' : server ? 'ink' : 'green';
  const trim = rider ? 'blue' : server ? 'mauve' : 'cream';
  const trousers = rider ? 'blue' : 'charcoal';
  loft('hips', trousers, [0,0,0], [[-.12,.165,.105], [.09,.17,.11]]);
  loft('spine', cloth, [0,0,0], [[-.09,.167,.10], [.02,.167,.105], [.225,.227,.118], [.293,.16,.088]]);
  loft('head', 'skin', [0,0,0], [[-.032,.055,.050], [.019,.087,.083], [.13,.106,.087], [.21,.083,.069]], 12);
  loft('head', rider ? 'amber' : 'mahogany', [0,0,-.007], [[.108,.110,.095], [.205,.118,.102], [.284,.084,.074], [.33,.038,.040]], 12);
  box('head', rider ? 'dark' : 'mahogany', [0,.162,-.076], [.16,.14,.052]);
  for (const side of [-1, 1]) {
    box('head', 'dark', [side*.039,.119,.077], [.024,.015,.014]);
    box('head', 'skin', [side*.097,.083,0], [.022,.049,.035]);
  }
  box('head', 'mauve', [0,.037,.080], [.04,.009,.012]);
  if (rider) {
    box('head', 'dark', [0,.192,.093], [.190,.018,.069]);
    loft('spine', 'silver', [0,0,0], [[.06,.191,.114], [.105,.204,.119]]);
    box('spine', 'dark', [0,.11,.119], [.018,.31,.018]);
    box('spine', 'blue', [0,.119,-.16], [.33,.29,.137]);
    box('spine', 'amber', [0,.129,-.232], [.276,.224,.030]);
    box('spine', 'silver', [0,.118,-.249], [.180,.034,.015]);
  } else {
    loft('hips', server ? 'ink' : 'green', [0,0,0], [[-.285,.205,.123], [-.25,.192,.125], [.05,.164,.108]], 12);
    box('spine', 'cream', [0,.082,.113], [.145,.225,.022]);
    box('hips', 'cream', [0,-.074,.139], [.205,.24,.034]);
    box('spine', trim, [0,.201,.138], [.141,.034,.024]);
    box('spine', trim, [0,.17,.138], [.033,.059,.024]);
    box('head', server ? 'mauve' : 'cream', [0,.292,.015], [.170,.045,.086]);
  }
  for (const side of [-1, 1]) {
    loft('arm'+side, cloth, [0,0,0], [[-.253,.064,.062], [-.042,.085,.078], [.034,.060,.057]], 8);
    loft('elbow'+side, cloth, [0,0,0], [[-.19,.052,.048], [.012,.065,.062]], 8);
    if (rider) loft('elbow'+side, 'silver', [0,0,0], [[-.16,.056,.055], [-.119,.056,.057]], 8);
    else loft('elbow'+side, 'cream', [0,0,0], [[-.19,.054,.052], [-.165,.057,.053]], 8);
    loft('elbow'+side, 'skin', [0,0,.01], [[-.261,.049,.039], [-.183,.042,.038]], 8);
    loft('leg'+side, trousers, [0,0,0], [[-.443,.073,.061], [-.04,.086,.079], [0,.085,.081]], 8);
    loft('knee'+side, trousers, [0,0,0], [[-.392,.060,.054], [-.06,.071,.066], [.025,.072,.062]], 8);
    box('ankle'+side, 'dark', [0,-.048,.048], [.139,.09,.213]);
    box('ankle'+side, trim, [0,-.008,.058], [.122,.029,.155]);
  }
  const {mesh, triangles} = geometry.finish();
  scene.addChild(document.createNode(label + ' mesh').setMesh(mesh).setSkin(skin));

  function clip(name, duration, poses) {
    const animation = document.createAnimation(name);
    const phases = [0,.25,.5,.75,1];
    const input = accessor('SCALAR', phases.map(phase => duration * phase));
    for (const [part, axis, angles] of poses) {
      const rotations = angles.flatMap(angle => {
        const quaternion = [0,0,0,Math.cos(angle / 2)];
        quaternion[axis] = Math.sin(angle / 2);
        return quaternion;
      });
      const sampler = document.createAnimationSampler()
        .setInterpolation('LINEAR').setInput(input).setOutput(accessor('VEC4', rotations));
      const channel = document.createAnimationChannel()
        .setTargetNode(joints.get(part).node).setTargetPath('rotation').setSampler(sampler);
      animation.addSampler(sampler).addChannel(channel);
    }
  }
  const oscillate = (amount, offset = 0) => [offset, offset + amount, offset, offset - amount, offset];
  function gait(amount) {
    return [
      ['spine', 1, oscillate(amount*.13)], ['head', 1, oscillate(-amount*.08)],
      ...[-1, 1].flatMap(side => [
        ['leg'+side, 0, oscillate(amount*side)],
        ['knee'+side, 0, [0, amount*(side > 0 ? .72 : .21), amount*.23, amount*(side < 0 ? .72 : .21), 0]],
        ['ankle'+side, 0, oscillate(-amount*side*.24)],
        ['arm'+side, 0, oscillate(-amount*side*.49)],
        ['elbow'+side, 0, oscillate(amount*side*.15, -amount*.35)],
      ]),
    ];
  }
  const walk = {cycleSeconds:rider ? 1 : 1.2, authoredSpeed:rider ? .93 : .45};
  const run = {cycleSeconds:.73, authoredSpeed:2.18};
  clip(rider?'Rider_Idle':'CafeIdle', 2, [
    ['spine', 2, oscillate(.026)], ['head', 1, oscillate(.075)],
    ['arm-1', 2, oscillate(.021, -.055)], ['arm1', 2, oscillate(-.021, .055)],
    ['elbow1', 0, oscillate(.037, -.041)],
  ]);
  clip(rider?'Rider_Walk':'CafeWalk', walk.cycleSeconds, gait(rider ? .41 : .31));
  if (rider) clip('Rider_Run', run.cycleSeconds, gait(.81));
  else clip('CafeWave', 1.25, [
    ['spine', 2, [0,.04,.048,.04,0]], ['head', 1, [0,.16,.15,.16,0]],
    ['arm1', 2, [0,.84,.87,.84,0]], ['elbow1', 2, [0,.95,1.42,.95,0]],
    ['arm-1', 2, [0,-.12,-.16,-.12,0]],
  ]);
  return {document, triangles, bones:joints.size, gait:{walk, run}};
}

function makeTank() {
  const {document, scene, ...rest} = newAsset('Stylized tracked game vehicle');
  const asset = {document, scene, ...rest};
  const root = document.createNode('tank_root');
  const hull = document.createNode('tank_hull');
  const turret = document.createNode('tank_turret').setTranslation([0,1.91,-.88]);
  const barrel = document.createNode('tank_barrel').setTranslation([0,.295,.885]);
  const muzzle = document.createNode('tank_muzzle').setTranslation([0,0,4.85]);
  scene.addChild(root);
  root.addChild(hull).addChild(turret);
  turret.addChild(barrel);
  barrel.addChild(muzzle);
  const body = builder(asset, 'Hull, running gear and paint');
  body.loft('sage', [0,.35,.03], [[.20,1.47,2.81], [.68,1.52,3.10], [1.14,1.47,3.01], [1.39,1.16,2.54]], 8);
  body.box('darkSage', [0,1.72,-1.75], [2.4,.28,2.06]);
  for (const side of [-1,1]) {
    const track = [[.025,-2.64],[.025,2.49],[.27,2.95],[.63,3.13],[.99,2.85],[1.11,2.42],[1.11,-2.62],[.95,-3.05],[.56,-3.19],[.26,-2.98]];
    const inside = [side*1.43,.54,0], edges = [side*1.15,side*1.76].map(x => track.map(([y,z]) => [x,y,z]));
    for (const edge of edges) body.emit('dark', edge, inside);
    for (let i = 0; i < track.length; i++) {
      const next = (i + 1) % track.length;
      body.emit('charcoal', [edges[0][i], edges[1][i], edges[1][next], edges[0][next]], inside);
    }
    for (let i = 0; i < 7; i++) {
      const z = 2.37 - i * .79;
      const x = side * 1.778, center = [x,.52,z];
      const circle = (radius, offset) => Array.from({length:12}, (_, index) => {
        const angle = index*Math.PI/6;
        return [x + side*offset, .52 + Math.cos(angle)*radius, z + Math.sin(angle)*radius];
      });
      body.emit('darkSage', circle(.42, .014), [x - side*.04,center[1],z]);
      body.emit('sage', circle(.21, .018), [x - side*.04,center[1],z]);
      body.emit('steel', circle(.095, .024), [x - side*.04,center[1],z]);
    }
    for (let i = -10; i <= 10; i++) body.box('steel', [side*1.431,.055,i*.24], [.68,.11,.058]);
    body.box('darkSage', [side*1.45,1.22,-.02], [.55,.24,4.94]);
    body.box('steel', [side*1.40,1.40,-.02], [.18,.09,4.94]);
    body.box('lamp', [side*.97,1.42,2.59], [.27,.14,.072]);
    body.box('red', [side*.99,1.17,-2.79], [.19,.15,.07]);
  }
  body.box('cream', [0,1.48,2.17], [.18,.022,.38]);
  const cabin = builder(asset, 'Rotating upper hull');
  cabin.loft('darkSage', [0,-.078,0], [[-.037,.71,.79], [.06,.84,.92]], 10);
  cabin.loft('sage', [0,0,.09], [[.05,.99,1.72], [.32,1.12,1.54], [.655,.83,1.29]], 8);
  cabin.loft('darkSage', [-.30,.67,-.39], [[0,.31,.27], [.145,.27,.23]], 10);
  cabin.box('glass', [.32,.56,.74], [.33,.17,.16]);
  cabin.box('cream', [-.56,.52,.91], [.36,.08,.17]);
  cabin.box('darkSage', [0,.28,1.23], [.64,.43,.32]);
  const front = builder(asset, 'Animated stylized barrel');
  const circles = [[.12,.25],[.37,.20],[1.40,.165],[4.32,.12],[4.43,.17],[4.85,.17]].map(([z,radius]) =>
    Array.from({length:12}, (_, index) => {
      const angle = index*Math.PI/6;
      return [Math.sin(angle)*radius, Math.cos(angle)*radius, z];
    }));
  for (let i = 1; i < circles.length; i++) {
    for (let j = 0; j < 12; j++) {
      const next = (j + 1) % 12;
      front.emit(i >= 4 ? 'steel' : 'darkSage', [circles[i-1][j],circles[i-1][next],circles[i][next],circles[i][j]], [0,0,circles[i][j][2]]);
    }
  }
  front.emit('dark',circles.at(-1),[0,0,4.5]);
  let triangles = 0;
  for (const [node, part] of [[hull, body], [turret, cabin], [barrel, front]]) {
    const payload = part.finish();
    node.setMesh(payload.mesh);
    triangles += payload.triangles;
  }
  return {document, triangles};
}

async function save(directory, key, art) {
  const target = new URL(directory + '/', output);
  await mkdir(target, {recursive:true});
  const file = key + '.glb';
  const bytes = await io.writeBinary(art.document);
  await writeFile(new URL(file,target), bytes);
  return {file, bytes:bytes.length, triangles:art.triangles, sha256:createHash('sha256').update(bytes).digest('hex')};
}

async function manifest(directory, payload) {
  await writeFile(new URL(directory + '/manifest.json', output), JSON.stringify({schemaVersion:1,...provenance,...payload}, null, 2)+'\n');
}

const rider = makeAvatar('Hangzhou courier', 'rider', 1.78);
await manifest('rider', {
  ...await save('rider', 'rider', rider), name:'杭城骑手', height:1.78, bones:rider.bones,
  coordinateSpace:'glTF Y-up, +Z forward', gait:rider.gait, animations:['Rider_Idle','Rider_Walk','Rider_Run'],
});
const cafeDir = 'bamboo-cafe/characters';
const staff = [];
for (const [id, label, height] of [['maid','Maison Lune barista',1.69],['jk','Maison Lune server',1.67]]) {
  const art = makeAvatar(label, id, height);
  staff.push({id, ...await save(cafeDir, id, art), height, rigged:true,
    bones:art.bones, gait:art.gait.walk, animations:['CafeIdle','CafeWalk','CafeWave']});
}
await manifest(cafeDir, {staffAssignments:{zhixia:'maid', wangshu:'maid', xiaolan:'jk'}, models:staff});
const tank = await save('tank', 'tank', makeTank());
await manifest('tank', {
  ...tank, coordinateSpace:'glTF Y-up, +Z forward', nodes:{root:'tank_root',hull:'tank_hull',turret:'tank_turret',barrel:'tank_barrel',muzzle:'tank_muzzle'},
  assetStats:{bytes:tank.bytes, triangles:tank.triangles, sha256:tank.sha256},
});
