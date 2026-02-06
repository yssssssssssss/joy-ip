// Three.js Editor Integration (adapted for Next.js iframe embedding)
// Adds parent postMessage and backend save hooks

let scene, camera, renderer, controls, clock;
let ambientLight, dirLight, pointLight, spotLight;
let model, skeleton, mixer;
let renderInfoEl, loadingEl;
let renderAreaEl;

const TARGET_CANVAS_WIDTH = 1024;
const TARGET_CANVAS_HEIGHT = 1200;
const TARGET_CANVAS_ASPECT = TARGET_CANVAS_WIDTH / TARGET_CANVAS_HEIGHT;

let currentAspect = TARGET_CANVAS_ASPECT;
let renderAreaResizeObserver = null;

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
  if (!el) return { width: 1, height: 1 };
  const rect = el.getBoundingClientRect();

  const maxWidth = Math.max(1, Math.floor(rect.width));
  const maxHeight = Math.max(1, Math.floor(rect.height));

  const aspect = TARGET_CANVAS_ASPECT;
  let width = maxWidth;
  let height = Math.max(1, Math.round(width / aspect));
  if (height > maxHeight) {
    height = maxHeight;
    width = Math.max(1, Math.round(height * aspect));
  }
  if (width > maxWidth) {
    width = maxWidth;
    height = Math.max(1, Math.round(width / aspect));
  }

  return { width, height };
}

function syncAspectFromView() {
  const { width, height } = getRenderSize();
  currentAspect = width / Math.max(1, height);
}

function observeRenderAreaResize() {
  if (!renderAreaEl) renderAreaEl = document.querySelector('.render-area');
  if (!renderAreaEl || typeof ResizeObserver === 'undefined') return;
  if (renderAreaResizeObserver) renderAreaResizeObserver.disconnect();
  renderAreaResizeObserver = new ResizeObserver(() => {
    onWindowResize();
  });
  renderAreaResizeObserver.observe(renderAreaEl);
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

function setContrastLevel(level) {
  if (!ambientLight || !dirLight) return;
  if (level === 'strong') {
    ambientLight.intensity = 0.8;
    dirLight.intensity = 2;
  } else if (level === 'normal') {
    ambientLight.intensity = 1.2;
    dirLight.intensity = 2;
  } else if (level === 'weak') {
    ambientLight.intensity = 1.8;
    dirLight.intensity = 2;
  }
}

window.addEventListener('message', (event) => {
  const data = event?.data;
  if (!data || typeof data !== 'object') return;

  if (data.type === 'three-editor-load-model') {
    if (typeof data.url !== 'string') return;
    const safeUrl = String(data.url).replace(/\\/g, '/').trim();
    if (!safeUrl || safeUrl.includes('..') || !safeUrl.startsWith('/three-editor/')) return;
    loadGLTFUrl(safeUrl);
    return;
  }

  if (data.type === 'three-editor-set-contrast') {
    const level = data.level;
    if (level !== 'strong' && level !== 'normal' && level !== 'weak') return;
    setContrastLevel(level);
    return;
  }

  if (data.type === 'three-editor-hq-render-default') {
    renderHighQuality({ width: 1024, height: 1200, format: 'png', quality: 0.92, supersample: 2, lensMM: 200 });
  }
});

async function initApprovedGrid() {
  // 已改由父组件 React 加载和展示
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

    renderer.setSize(width * supersample, height * supersample, false);
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

      renderer.setSize(oldSize.x, oldSize.y, false);
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
  // 基础 UI 元素已在 index.html 中被移除，改由父组件 React 控制
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
  observeRenderAreaResize();
  animate();
});
// Use ES Modules imports to avoid deprecated global build and ensure controls/loaders work
import * as THREE from 'three'
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/loaders/GLTFLoader.js'
import { FBXLoader } from 'https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/loaders/FBXLoader.js'
