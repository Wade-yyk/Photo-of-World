'use strict';
const data = JSON.parse(document.querySelector('#alignment-data').textContent);
const featureData = JSON.parse(document.querySelector('#feature-data').textContent);
const records = new Map(data.images.map(r => [r.id, r]));
const features = new Map(featureData.images.map(r => [r.id, r]));
const settings = new Map(data.images.map(r => [r.id, 0]));
const cards = [...document.querySelectorAll('.result-card')];
const select = document.querySelector('#plate-select');
const comparison = document.querySelector('#comparison');
const slider = document.querySelector('#comparison-slider');
const viewerControls = document.querySelector('#viewer-features');
const format = ([x, y]) => `(${x >= 0 ? '+' : ''}${x}, ${y >= 0 ? '+' : ''}${y})`;
const labels = [[1, 'Gradient NCC'], [2, 'Auto crop'], [4, 'White balance'], [8, 'Contrast'], [16, 'Colour mapping']];
let mode = 'pyramid';
let viewerRequest = 0;
const cardRequests = new Map();
const decode = src => { const img = new Image(); img.src = src; return img.decode(); };

function featureName(mask) {
  return mask ? labels.filter(([bit]) => mask & bit).map(([, label]) => label).join(' + ') : 'Original pyramid NCC';
}

function paths(id, mask) {
  const variant = features.get(id).variants[String(mask)];
  return {
    after: `results/${id}/${mask ? variant.file : 'aligned.jpg'}`,
    before: `results/${id}/${mask ? variant.reference : 'before.jpg'}`,
    download: `results/${id}/${mask ? variant.file : 'aligned-full.jpg'}`,
    variant,
  };
}

function syncControls(container, id, disabled = false) {
  const mask = settings.get(id);
  const f = features.get(id);
  const variant = f.variants[String(mask)];
  container.querySelectorAll('[data-feature]').forEach(input => {
    input.checked = Boolean(mask & Number(input.dataset.feature));
    input.disabled = disabled;
  });
  container.querySelector('.reset-features').disabled = disabled;
  container.querySelector('.feature-status').textContent = disabled
    ? 'Options saved · Switch to Pyramid NCC to apply effects'
    : `${featureName(mask)}${mask ? ' · Preview ≤1100 px' : ' · No extra effects'}`;
  const crop = variant.detected_crop;
  let info = mask & 1 ? 'Alignment: gradient-magnitude NCC. ' : 'Alignment: original intensity NCC. ';
  info += mask & 2 ? `Detected crop [left, top, right, bottom]: [${crop.join(', ')}]. ` : 'Automatic crop off. ';
  if (mask & 4) info += `RGB gains: ${variant.gains.map(v => v.toFixed(3)).join(', ')}. `;
  if (mask & 8) info += `Contrast range: ${variant.levels.map(v => v.toFixed(3)).join('–')}. `;
  if (mask & 16) info += 'Experimental matrix: 85% chroma retained; not colour-calibrated. ';
  if (mask) info += `Preview: ${variant.preview_size.join(' × ')} px.`;
  container.querySelector('.feature-metadata').textContent = info;
  container.querySelector('.crop-diagnostic').href = `results/${id}/features/crop-detection-${mask & 1 ? 1 : 0}.jpg`;
  container.querySelector('.baseline-download').href = `results/${id}/aligned-full.jpg`;
}

function updateSplit() {
  const value = Number(slider.value);
  const edited = settings.get(select.value) !== 0;
  comparison.style.setProperty('--split', `${value}%`);
  document.querySelector('#comparison-value').value = `${value} / ${100 - value}`;
  slider.setAttribute('aria-valuetext', `${value}% ${edited ? 'original NCC' : 'unaligned'}, ${100 - value}% ${edited ? 'selected effects' : 'aligned'}`);
}

async function inspect(id) {
  const record = records.get(id);
  if (!record) return;
  const token = ++viewerRequest;
  select.value = id;
  const mask = settings.get(id);
  const assets = paths(id, mask);
  syncControls(viewerControls, id);
  comparison.setAttribute('aria-busy', 'true');
  try {
    await Promise.all([assets.before, assets.after].map(decode));
    if (token !== viewerRequest) return;
    document.querySelector('#before-image').src = assets.before;
    document.querySelector('#after-image').src = assets.after;
    document.querySelector('#before-image').alt = `${mask ? 'Original NCC' : 'Unaligned'} reconstruction of ${record.source}, matched comparison crop`;
    document.querySelector('#after-image').alt = `${featureName(mask)} reconstruction of ${record.source}, same crop`;
    document.querySelector('.before-label').textContent = mask ? 'ORIGINAL NCC' : 'BEFORE';
    document.querySelector('.after-label').textContent = mask ? 'SELECTED EFFECTS' : 'PYRAMID NCC';
    const rangeLabels = document.querySelectorAll('.comparison-controls > div > span');
    rangeLabels[0].textContent = mask ? 'SELECTED EFFECTS' : 'ALIGNED';
    rangeLabels[1].textContent = mask ? 'ORIGINAL NCC' : 'UNALIGNED';
    const link = document.querySelector('#full-result');
    link.href = assets.download;
    link.textContent = mask ? 'Open selected preview (≤1100 px) ↗' : 'Open original full-resolution result ↗';
    const alignment = mask & 1 ? features.get(id).gradient : record.pyramid;
    document.querySelector('#selected-size').textContent = mask ? `Preview: ${assets.variant.preview_size.join(' × ')} px` : `Channel: ${record.channel_size.join(' × ')} px`;
    document.querySelector('#selected-green').textContent = `G shift: ${format(alignment.green)}`;
    document.querySelector('#selected-red').textContent = `R shift: ${format(alignment.red)}`;
    document.querySelector('#selected-time').textContent = `Alignment: ${alignment.seconds.toFixed(3)} s`;
    updateSplit();
  } catch (error) {
    if (token === viewerRequest) viewerControls.querySelector('.feature-status').textContent = 'Could not load selected effects. Toggle again to retry.';
  } finally {
    if (token === viewerRequest) comparison.setAttribute('aria-busy', 'false');
  }
}

async function renderCard(card) {
  const id = card.dataset.id;
  const record = records.get(id);
  const mask = settings.get(id);
  const currentMode = mode;
  const token = (cardRequests.get(id) || 0) + 1;
  cardRequests.set(id, token);
  syncControls(card, id, mode !== 'pyramid');
  const assets = paths(id, mask);
  const src = mode === 'pyramid' ? assets.after : `results/${id}/${mode === 'single' ? 'single' : 'before'}.jpg`;
  card.setAttribute('aria-busy', 'true');
  try {
    await decode(src);
    if (cardRequests.get(id) !== token) return;
    const img = card.querySelector('.inspect-image img');
    img.src = src;
    img.alt = `${currentMode === 'pyramid' ? featureName(mask) : currentMode === 'single' ? 'Single-scale NCC' : 'Unaligned RGB'}: ${record.source}`;
    const alignment = currentMode === 'single' ? record.single : mask & 1 ? features.get(id).gradient : record.pyramid;
    const size = currentMode === 'single' ? record.single_size : record.channel_size;
    card.querySelector('.card-dimensions').textContent = currentMode === 'pyramid' && mask
      ? `Preview ${assets.variant.preview_size.join(' × ')} px` : `${size.join(' × ')} px per channel`;
    card.querySelector('.card-offsets').textContent = currentMode === 'before' ? 'G (0, 0) · R (0, 0)' : `G ${format(alignment.green)} · R ${format(alignment.red)}`;
    card.querySelector('.card-timing').textContent = currentMode === 'before' ? 'No alignment applied'
      : `${alignment.seconds.toFixed(3)} s · ${currentMode === 'single' ? 'Low-resolution search' : mask & 1 ? 'Gradient alignment' : 'Original alignment'}`;
    const link = card.querySelector(':scope > a');
    link.href = currentMode === 'pyramid' ? assets.download : src;
    link.textContent = currentMode === 'pyramid' && !mask ? 'Open original full-resolution result ↗' : 'Open displayed preview ↗';
  } catch (error) {
    if (cardRequests.get(id) === token) card.querySelector('.feature-status').textContent = 'Image could not load. Change an option to retry.';
  } finally {
    if (cardRequests.get(id) === token) card.setAttribute('aria-busy', 'false');
  }
}

function updateFeatures(id, mask) {
  settings.set(id, mask);
  const card = cards.find(c => c.dataset.id === id);
  renderCard(card);
  if (select.value === id) inspect(id);
}

function wireControls(container, getId) {
  container.querySelectorAll('[data-feature]').forEach(input => input.addEventListener('change', () => {
    const id = getId();
    const bit = Number(input.dataset.feature);
    const old = settings.get(id);
    updateFeatures(id, input.checked ? old | bit : old & ~bit);
  }));
  container.querySelector('.reset-features').addEventListener('click', () => updateFeatures(getId(), 0));
}

slider.addEventListener('input', updateSplit);
select.addEventListener('change', () => inspect(select.value));
wireControls(viewerControls, () => select.value);
cards.forEach(card => {
  wireControls(card, () => card.dataset.id);
  card.querySelector('[data-inspect]').addEventListener('click', () => {
    inspect(card.dataset.id);
    document.querySelector('#explore').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    select.focus({preventScroll: true});
  });
  renderCard(card);
});
document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => {
  mode = button.dataset.mode;
  document.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
  document.querySelector('#gallery-description').textContent = mode === 'single'
    ? 'Original single-scale NCC · Saved optional effects are suspended in this view.'
    : mode === 'before' ? 'Original unaligned RGB · Saved optional effects are suspended in this view.'
    : 'Pyramid NCC · Choose effects independently beneath each photo. Reset restores the exact original result.';
  cards.forEach(renderCard);
}));
inspect(select.value);
updateSplit();
