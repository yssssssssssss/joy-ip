// Three.js Editor Integration (adapted for Next.js iframe embedding)
// Adds parent postMessage and backend save hooks

let scene, camera, renderer, controls, clock;
let ambientLight, dirLight, pointLight, spotLight;
let model, skeleton, mixer;
let renderInfoEl, loadingEl;
let renderAreaEl;
let currentAspect = 16 / 9;
// 视窗比例微调：在当前基础上将宽高比（W/H）增加 5%
let baseViewportAspect = null; // 首次测得的视窗比例（W/H）
let targetViewportAspect = null; // 目标视窗比例（W/H）

const canvas = document.getElementById('canvas');

function initScene() {
  clock = new THREE.Clock();
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a0a15);

  renderAreaEl = document.querySelector('.render-area');
  const { width, height } = getRenderSize();

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
  camera.position.set(0, 1.2, 3);

  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, canvas });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.target.set(0, 1, 0);

  // 默认设置 350mm 焦段，并保持屏幕投影大小不变（不改变构图）
  try {
    const baseFovRad = THREE.MathUtils.degToRad(camera.fov);
    const basePos = camera.position.clone();
    const focusCenter = controls.target.clone();
    const baseDistance = basePos.distanceTo(focusCenter);
    camera.setFocalLength(350);
    camera.updateProjectionMatrix();
    const newFovRad = THREE.MathUtils.degToRad(camera.fov);
    const scale = Math.tan(baseFovRad / 2) / Math.tan(newFovRad / 2);
    const dir = basePos.clone().sub(focusCenter).normalize();
    const newPos = focusCenter.clone().add(dir.multiplyScalar(baseDistance * scale));
    camera.position.copy(newPos);
    camera.lookAt(focusCenter);
    controls.target.copy(focusCenter);
    controls.update();
  } catch (e) {
    console.warn('设置默认镜头为 350mm 失败：', e);
  }

  ambientLight = new THREE.AmbientLight(0xffffff, 1);
  scene.add(ambientLight);

  dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
  dirLight.position.set(5, 10, 7.5);
  dirLight.castShadow = true;
  scene.add(dirLight);

  pointLight = new THREE.PointLight(0xffffff, 0.6);
  pointLight.position.set(-3, 2, -2);
  scene.add(pointLight);

  spotLight = new THREE.SpotLight(0xffffff, 0.8);
  spotLight.position.set(3, 6, 2);
  spotLight.angle = Math.PI / 6;
  spotLight.penumbra = 0.2;
  scene.add(spotLight);

  // 隐藏网格线
  // const grid = new THREE.GridHelper(10, 10);
  // scene.add(grid);

  renderInfoEl = document.getElementById('render-info');
  loadingEl = document.getElementById('loading');

  window.addEventListener('resize', onWindowResize);
}

function onWindowResize() {
  const { width, height } = getRenderSize();
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

function getRenderSize() {
  const el = renderAreaEl || document.querySelector('.render-area');
  const rect = el.getBoundingClientRect();
  return { width: Math.max(1, Math.floor(rect.width)), height: Math.max(1, Math.floor(rect.height)) };
}

function syncAspectFromView() {
  const { width, height } = getRenderSize();
  currentAspect = width / Math.max(1, height);
}

// 将视窗的宽高比在当前基础上增加指定百分比（默认 5%）
function applyViewportAspectIncrease(percent = 0.05) {
  if (!renderAreaEl) renderAreaEl = document.querySelector('.render-area');
  if (!renderAreaEl) return;
  const rect = renderAreaEl.getBoundingClientRect();
  const curr = rect.width / Math.max(1, rect.height);
  if (baseViewportAspect == null) {
    baseViewportAspect = curr;
  }
  targetViewportAspect = baseViewportAspect * (1 + percent);
  const targetHeight = Math.max(1, Math.floor(rect.width / targetViewportAspect));
  // 通过设置容器高度来实现更“扁”的显示区域
  renderAreaEl.style.height = `${targetHeight}px`;
  // 同步 three 的尺寸与相机比例
  currentAspect = targetViewportAspect;
  onWindowResize();
}

// 监听容器尺寸变化，保持目标视窗比例
function observeViewportAspect() {
  if (!renderAreaEl) renderAreaEl = document.querySelector('.render-area');
  if (!renderAreaEl) return;
  const ro = new ResizeObserver(() => {
    if (!targetViewportAspect) return;
    const rect = renderAreaEl.getBoundingClientRect();
    const targetHeight = Math.max(1, Math.floor(rect.width / targetViewportAspect));
    renderAreaEl.style.height = `${targetHeight}px`;
    onWindowResize();
  });
  ro.observe(renderAreaEl);
}

function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();
  if (mixer) mixer.update(delta);
  controls.update();
  renderer.render(scene, camera);

  if (renderInfoEl) {
    renderInfoEl.textContent = `FPS: ${Math.round(1 / delta)}`;
  }
}

function loadGLTF(file) {
  const reader = new FileReader();
  reader.onload = () => {
    const loader = new GLTFLoader();
    loader.parse(reader.result, '', (gltf) => {
      if (model) scene.remove(model);
      model = gltf.scene;
      scene.add(model);
      if (gltf.animations && gltf.animations.length) {
        mixer = new THREE.AnimationMixer(model);
        const action = mixer.clipAction(gltf.animations[0]);
        action.play();
      }
      findSkeleton(model);
    });
  };
  reader.readAsArrayBuffer(file);
}

function loadFBX(file) {
  const reader = new FileReader();
  reader.onload = () => {
    const loader = new FBXLoader();
    const obj = loader.parse(reader.result);
    if (model) scene.remove(model);
    model = obj;
    scene.add(model);
    findSkeleton(model);
  };
  reader.readAsArrayBuffer(file);
}

function findSkeleton(obj) {
  obj.traverse((child) => {
    if (child.isSkinnedMesh) {
      skeleton = child.skeleton;
    }
  });
}

function takeScreenshot() {
  const dataURL = renderer.domElement.toDataURL('image/png');
  window.parent?.postMessage({ type: 'three-editor-screenshot', dataURL }, '*');
}

// 远程加载 GLTF/GLB
function loadGLTFUrl(url) {
  const loader = new GLTFLoader();
  if (loadingEl) loadingEl.style.display = 'flex';
  
  loader.load(url, (gltf) => {
    if (model) scene.remove(model);
    model = gltf.scene;
    scene.add(model);
    if (gltf.animations && gltf.animations.length) {
      mixer = new THREE.AnimationMixer(model);
      const action = mixer.clipAction(gltf.animations[0]);
      action.play();
    }
    findSkeleton(model);
    // 将相机聚焦到模型中心
    const box = new THREE.Box3().setFromObject(model);
    const c = new THREE.Vector3();
    box.getCenter(c);
    controls.target.copy(c);
    camera.lookAt(c);
    controls.update();
    // 加载完成，隐藏 loading
    if (loadingEl) loadingEl.style.display = 'none';
  }, (progress) => {
    // 可选：显示加载进度
    if (progress.total > 0) {
      const percent = Math.round((progress.loaded / progress.total) * 100);
      console.log(`模型加载进度: ${percent}%`);
    }
  }, (err) => {
    console.error('加载预审模型失败:', err);
    if (loadingEl) loadingEl.style.display = 'none';
  });
}

async function initApprovedGrid() {
  const grid = document.getElementById('approved-grid');
  if (!grid) return;
  try {
    const resp = await fetch('/three-editor/approved-models.json', { cache: 'no-store' });
    const list = await resp.json();
    grid.innerHTML = '';
    list.forEach((item, index) => {
      const card = document.createElement('div');
      card.className = 'approved-item';
      card.style.display = 'inline-flex';
      card.style.flexDirection = 'column';
      card.style.alignItems = 'center';
      card.style.justifyContent = 'center';
      card.style.gap = '6px';
      card.style.margin = '6px';
      card.style.padding = '8px';
      card.style.border = '1px solid rgba(255, 255, 255, 0.15)';
      card.style.borderRadius = '10px';
      card.style.cursor = 'pointer';
      card.style.background = '#424158';
      card.style.transition = 'all 0.2s ease';

      const img = document.createElement('img');
      img.loading = 'lazy'; // 懒加载优化
      img.src = item.preview;
      img.alt = item.name || '预审模型';
      img.style.width = '80px';
      img.style.height = '60px';
      img.style.objectFit = 'cover';
      img.style.borderRadius = '6px';

      const label = document.createElement('div');
      label.textContent = item.name || '';
      label.style.fontSize = '12px';
      label.style.color = '#b7affe';

      card.appendChild(img);
      card.appendChild(label);
      
      card.addEventListener('mouseenter', () => {
        card.style.background = '#4a4964';
        card.style.transform = 'translateY(-2px)';
      });
      card.addEventListener('mouseleave', () => {
        card.style.background = '#424158';
        card.style.transform = 'translateY(0)';
      });
      card.addEventListener('click', () => {
        // 显示加载状态
        if (loadingEl) loadingEl.style.display = 'flex';
        loadGLTFUrl(item.url);
      });
      grid.appendChild(card);
      
      // 首个模型自动加载
      if (index === 0) {
        setTimeout(() => loadGLTFUrl(item.url), 100);
      }
    });
  } catch (e) {
    console.warn('无法加载预审模型列表:', e);
  }
}

async function renderHighQuality(options = {}) {
  const {
    width = 1920,
    height = 1080,
    format = 'png',
    quality = 0.92,
    supersample = 2,
    lensMM = 0,
  } = options;

  try {
    loadingEl.style.display = 'flex';

    const oldSize = renderer.getSize(new THREE.Vector2());
    const oldRatio = renderer.getPixelRatio();

    // 保存当前镜头与视角信息，用于渲染后恢复
    const baseFovDeg = camera.fov;
    const basePos = camera.position.clone();
    const baseTarget = controls.target.clone();
    // 以模型中心为对焦目标（若无模型则使用当前 OrbitControls 目标）
    let focusCenter = baseTarget.clone();
    if (model) {
      const box = new THREE.Box3().setFromObject(model);
      const c = new THREE.Vector3();
      box.getCenter(c);
      focusCenter = c;
    }
    const baseDistance = basePos.distanceTo(focusCenter);

    // 如果指定了焦段，则在渲染前调整镜头焦距与相机距离，保持角色屏幕大小不变
    let didAdjustLens = false;
    if (lensMM && Number(lensMM) > 0) {
      didAdjustLens = true;
      const baseFovRad = THREE.MathUtils.degToRad(baseFovDeg);
      camera.setFocalLength(Number(lensMM));
      camera.updateProjectionMatrix();
      const newFovRad = THREE.MathUtils.degToRad(camera.fov);
      // 依据 FOV 变化比例缩放与目标的距离，以保持屏幕投影大小不变
      const scale = Math.tan(baseFovRad / 2) / Math.tan(newFovRad / 2);
      const dir = basePos.clone().sub(focusCenter).normalize();
      const newPos = focusCenter.clone().add(dir.multiplyScalar(baseDistance * scale));
      camera.position.copy(newPos);
      controls.target.copy(focusCenter);
      camera.lookAt(focusCenter);
      controls.update();
    }

    renderer.setSize(width * supersample, height * supersample);
    renderer.setPixelRatio(1);
    renderer.render(scene, camera);

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const ctx = tempCanvas.getContext('2d');

    const img = new Image();
    img.onload = async () => {
      ctx.drawImage(img, 0, 0, width, height);
      const mime = format === 'jpeg' ? 'image/jpeg' : 'image/png';
      const dataURL = tempCanvas.toDataURL(mime, quality);

      window.parent?.postMessage({ type: 'three-editor-hq-render', dataURL }, '*');

      try {
        const resp = await fetch('/api/save-render', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataURL }),
        });
        const json = await resp.json();
        window.parent?.postMessage({ type: 'three-editor-hq-saved', filePath: json.filePath, previewUrl: json.url }, '*');
      } catch (e) {
        console.error('Failed to persist render:', e);
      }

      renderer.setSize(oldSize.x, oldSize.y);
      renderer.setPixelRatio(oldRatio);
      // 恢复渲染前的镜头与视角
      if (didAdjustLens) {
        controls.target.copy(baseTarget);
        camera.position.copy(basePos);
        camera.fov = baseFovDeg;
        camera.updateProjectionMatrix();
        controls.update();
      }
      loadingEl.style.display = 'none';
    };
    img.src = renderer.domElement.toDataURL('image/png');
  } catch (err) {
    console.error(err);
    loadingEl.style.display = 'none';
  }
}

function setupUI() {
  document.getElementById('screenshot-btn').addEventListener('click', takeScreenshot);
  document.getElementById('render-btn').addEventListener('click', () => {
    openRenderModal();
  });
  document.getElementById('start-render-btn').addEventListener('click', () => {
    // 保持弹窗打开；仅开始渲染，不关闭设置
    const format = document.getElementById('render-format').value;
    const quality = parseFloat(document.getElementById('jpeg-quality').value);
    const supersample = parseInt(document.getElementById('supersample').value || '1', 10);
    const lensMMVal = parseInt(document.getElementById('lens-mm')?.value || '0', 10);
    const keepRatio = !!document.getElementById('keep-aspect-ratio')?.checked;
    let width = parseInt(document.getElementById('render-width').value || '1920', 10);
    let height = parseInt(document.getElementById('render-height').value || '1080', 10);
    if (keepRatio) {
      syncAspectFromView();
      height = Math.max(1, Math.round(width / currentAspect));
      document.getElementById('render-height').value = String(height);
    }
    renderHighQuality({ width, height, format, quality, supersample, lensMM: lensMMVal });
  });

  document.getElementById('upload-model').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.name.toLowerCase().endsWith('.glb') || file.name.toLowerCase().endsWith('.gltf')) {
      loadGLTF(file);
    } else if (file.name.toLowerCase().endsWith('.fbx')) {
      loadFBX(file);
    } else {
      alert('只支持 GLTF/GLB 或 FBX 文件');
    }
  });

  // 灯光设置事件绑定
  const ambInt = document.getElementById('ambient-intensity');
  const ambCol = document.getElementById('ambient-color');
  const dirInt = document.getElementById('dir-intensity');
  const dirCol = document.getElementById('dir-color');
  const dirX = document.getElementById('dir-x');
  const dirY = document.getElementById('dir-y');
  const dirZ = document.getElementById('dir-z');
  const ptInt = document.getElementById('point-intensity');
  const ptCol = document.getElementById('point-color');
  const ptX = document.getElementById('point-x');
  const ptY = document.getElementById('point-y');
  const ptZ = document.getElementById('point-z');
  const addPt = document.getElementById('add-point-light');
  const spInt = document.getElementById('spot-intensity');
  const spCol = document.getElementById('spot-color');
  const spAng = document.getElementById('spot-angle');
  const spPen = document.getElementById('spot-penumbra');

  // 对比按钮（仅保留三档）
  const strongBtn = document.getElementById('contrast-strong');
  const normalBtn = document.getElementById('contrast-normal');
  const weakBtn = document.getElementById('contrast-weak');
  const applyContrast = (ambient, directional) => {
    if (ambientLight) ambientLight.intensity = ambient;
    if (dirLight) dirLight.intensity = directional;
  };
  if (strongBtn) strongBtn.addEventListener('click', () => applyContrast(0.8, 2));
  if (normalBtn) normalBtn.addEventListener('click', () => applyContrast(1.2, 2));
  if (weakBtn) weakBtn.addEventListener('click', () => applyContrast(1.8, 2));

  if (ambInt) ambInt.addEventListener('input', (e) => { ambientLight.intensity = parseFloat(e.target.value) });
  if (ambCol) ambCol.addEventListener('input', (e) => { ambientLight.color.set(e.target.value) });
  if (dirInt) dirInt.addEventListener('input', (e) => { dirLight.intensity = parseFloat(e.target.value) });
  if (dirCol) dirCol.addEventListener('input', (e) => { dirLight.color.set(e.target.value) });
  const updateDirPos = () => {
    const x = parseFloat(dirX?.value || '5');
    const y = parseFloat(dirY?.value || '10');
    const z = parseFloat(dirZ?.value || '7.5');
    dirLight.position.set(x, y, z);
  };
  if (dirX) dirX.addEventListener('input', updateDirPos);
  if (dirY) dirY.addEventListener('input', updateDirPos);
  if (dirZ) dirZ.addEventListener('input', updateDirPos);

  if (ptInt) ptInt.addEventListener('input', (e) => { pointLight.intensity = parseFloat(e.target.value) });
  if (ptCol) ptCol.addEventListener('input', (e) => { pointLight.color.set(e.target.value) });
  const updatePtPos = () => {
    const x = parseFloat(ptX?.value || '-3');
    const y = parseFloat(ptY?.value || '2');
    const z = parseFloat(ptZ?.value || '-2');
    pointLight.position.set(x, y, z);
  };
  if (ptX) ptX.addEventListener('input', updatePtPos);
  if (ptY) ptY.addEventListener('input', updatePtPos);
  if (ptZ) ptZ.addEventListener('input', updatePtPos);
  if (addPt) addPt.addEventListener('click', () => {
    const intensity = parseFloat(ptInt?.value || '0.6');
    const color = ptCol?.value || '#ffffff';
    const x = parseFloat(ptX?.value || '0');
    const y = parseFloat(ptY?.value || '1');
    const z = parseFloat(ptZ?.value || '0');
    const newPoint = new THREE.PointLight(color, intensity);
    newPoint.position.set(x, y, z);
    scene.add(newPoint);
  });

  if (spInt) spInt.addEventListener('input', (e) => { spotLight.intensity = parseFloat(e.target.value) });
  if (spCol) spCol.addEventListener('input', (e) => { spotLight.color.set(e.target.value) });
  if (spAng) spAng.addEventListener('input', (e) => { spotLight.angle = parseFloat(e.target.value) });
  if (spPen) spPen.addEventListener('input', (e) => { spotLight.penumbra = parseFloat(e.target.value) });
}

function openRenderModal() {
  document.getElementById('render-modal').style.display = 'flex';
  // 初始化分辨率输入，保持当前视图高宽比
  syncAspectFromView();
  const wEl = document.getElementById('render-width');
  const hEl = document.getElementById('render-height');
  const keepEl = document.getElementById('keep-aspect-ratio');
  if (wEl && hEl) {
    const w = parseInt(wEl.value || '1920', 10);
    if (keepEl?.checked) {
      hEl.value = String(Math.max(1, Math.round(w / currentAspect)));
    }
    // 绑定联动事件
    wEl.oninput = () => {
      if (keepEl?.checked) {
        const w2 = parseInt(wEl.value || '1920', 10);
        hEl.value = String(Math.max(1, Math.round(w2 / currentAspect)));
      }
    };
    hEl.oninput = () => {
      if (keepEl?.checked) {
        const h2 = parseInt(hEl.value || '1080', 10);
        wEl.value = String(Math.max(1, Math.round(h2 * currentAspect)));
      }
    };
    keepEl?.addEventListener('change', () => {
      syncAspectFromView();
      const w3 = parseInt(wEl.value || '1920', 10);
      hEl.value = String(Math.max(1, Math.round(w3 / currentAspect)));
    });
  }

  // 实时预览镜头焦段（在弹窗打开期间），关闭弹窗时还原
  const lensSelect = document.getElementById('lens-mm');
  // 保存预览前的相机与控制器状态
  if (!window.__lensPreviewBase) {
    window.__lensPreviewBase = {
      fov: camera.fov,
      position: camera.position.clone(),
      target: controls.target.clone(),
    };
  }
  const applyLensPreview = (mmStr) => {
    const mm = parseInt(mmStr || '0', 10);
    const baseState = window.__lensPreviewBase;
    if (!mm || mm <= 0) {
      // 还原到预览前状态
      camera.fov = baseState.fov;
      camera.position.copy(baseState.position);
      controls.target.copy(baseState.target);
      camera.updateProjectionMatrix();
      controls.update();
      return;
    }
    // 以当前（或模型中心）为对焦目标，保持屏幕投影大小不变
    let focusCenter = controls.target.clone();
    if (model) {
      const box = new THREE.Box3().setFromObject(model);
      const c = new THREE.Vector3();
      box.getCenter(c);
      focusCenter = c;
    }
    const baseFovRad = THREE.MathUtils.degToRad(baseState.fov);
    const baseDistance = baseState.position.distanceTo(focusCenter);
    camera.setFocalLength(mm);
    camera.updateProjectionMatrix();
    const newFovRad = THREE.MathUtils.degToRad(camera.fov);
    const scale = Math.tan(baseFovRad / 2) / Math.tan(newFovRad / 2);
    const dir = baseState.position.clone().sub(focusCenter).normalize();
    const newPos = focusCenter.clone().add(dir.multiplyScalar(baseDistance * scale));
    camera.position.copy(newPos);
    controls.target.copy(focusCenter);
    camera.lookAt(focusCenter);
    controls.update();
  };
  if (lensSelect) {
    lensSelect.onchange = (e) => applyLensPreview(e.target.value);
  }
}

function closeRenderModal() {
  document.getElementById('render-modal').style.display = 'none';
  // 关闭弹窗时，恢复预览前的相机状态
  const baseState = window.__lensPreviewBase;
  if (baseState) {
    camera.fov = baseState.fov;
    camera.position.copy(baseState.position);
    controls.target.copy(baseState.target);
    camera.updateProjectionMatrix();
    controls.update();
    // 清理一次，避免污染后续预览
    window.__lensPreviewBase = null;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  initScene();
  setupUI();
  initApprovedGrid();
  // 在当前基础上将视窗的宽高比（W/H）增加 5%，并保持该比例
  applyViewportAspectIncrease(0.05);
  observeViewportAspect();
  animate();
});
// Use ES Modules imports to avoid deprecated global build and ensure controls/loaders work
import * as THREE from 'three'
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/loaders/GLTFLoader.js'
import { FBXLoader } from 'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/loaders/FBXLoader.js'
