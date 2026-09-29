'use strict';
const portraits = [...document.querySelectorAll('.portrait-toggle')];
portraits.forEach(button => {
  const img = button.querySelector('img');
  const originalAlt = img.alt;
  const preload = new Image(); preload.src = button.dataset.abstract;
  button.addEventListener('click', () => {
    const abstract = button.getAttribute('aria-pressed') !== 'true';
    button.setAttribute('aria-pressed', String(abstract));
    img.src = abstract ? button.dataset.abstract : button.dataset.original;
    img.alt = abstract ? `Easter egg for: ${originalAlt}` : originalAlt;
    button.querySelector('.flip-hint').textContent = abstract ? '↻ BACK TO PORTRAIT' : '↻ EASTER EGG';
  });
});
const slider = document.querySelector('#frame-slider');
const frameView = document.querySelector('#frame-view');
const frameName = document.querySelector('#frame-name');
const frameBadge = document.querySelector('#frame-badge');
const thumbs = [...document.querySelectorAll('[data-frame]')];
const playButton = document.querySelector('#play-sequence');
const frames = Array.from({length:11}, (_,i) => `assets/img_${8595+i}.jpg`);
let currentFrame = 0, direction = 1, timer = null;
function showFrame(value) {
  currentFrame = Math.max(0, Math.min(10, Number(value)));
  slider.value = currentFrame;
  const name = `IMG_${8595+currentFrame}`;
  frameView.src = frames[currentFrame];
  frameView.alt = `Dolly zoom frame ${currentFrame+1} of 11, ${name}`;
  frameName.value = name;
  frameBadge.textContent = `${String(currentFrame+1).padStart(2,'0')} / 11`;
  slider.setAttribute('aria-valuetext', `Frame ${currentFrame+1} of 11, ${name}`);
  thumbs.forEach((b,i) => b.setAttribute('aria-pressed', String(i === currentFrame)));
}
function stopPlayback() { clearInterval(timer); timer=null; playButton.textContent='Play sequence'; playButton.setAttribute('aria-pressed','false'); }
function selectFrame(value) { stopPlayback(); showFrame(value); }
slider.addEventListener('input', () => selectFrame(slider.value));
thumbs.forEach(b => b.addEventListener('click', () => selectFrame(b.dataset.frame)));
document.querySelector('#previous-frame').addEventListener('click', () => selectFrame(currentFrame-1));
document.querySelector('#next-frame').addEventListener('click', () => selectFrame(currentFrame+1));
playButton.addEventListener('click', () => {
  if(timer !== null) { stopPlayback(); return; }
  frames.forEach(src => { const im=new Image(); im.src=src; });
  playButton.textContent='Pause sequence'; playButton.setAttribute('aria-pressed','true');
  timer=setInterval(() => { if(currentFrame===10)direction=-1; if(currentFrame===0)direction=1; showFrame(currentFrame+direction); },220);
});
const gifView=document.querySelector('#gif-view');
const gifToggle=document.querySelector('#gif-toggle');
const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
let gifPlaying=!reducedMotion.matches;
function updateGif() { gifView.src=gifPlaying?'assets/dolly-zoom.gif':frames[0]; gifToggle.textContent=gifPlaying?'Pause animation':'Play animation'; gifToggle.setAttribute('aria-pressed',String(gifPlaying)); }
updateGif();
gifToggle.addEventListener('click', () => { gifPlaying=!gifPlaying; updateGif(); });
reducedMotion.addEventListener('change', e => { if(e.matches){ stopPlayback();gifPlaying=false;updateGif(); } });
document.addEventListener('visibilitychange', () => { if(document.hidden)stopPlayback(); });
const links=[...document.querySelectorAll('.nav-links a')];
const observer=new IntersectionObserver(entries => { entries.forEach(entry => { if(entry.isIntersecting)links.forEach(link => { const active=link.hash===`#${entry.target.id}`; link.classList.toggle('active',active); if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current'); }); }); },{rootMargin:'-15% 0px -65% 0px'});
document.querySelectorAll('#portraits, #architecture, #dolly').forEach(s => observer.observe(s));
let printState;
window.addEventListener('beforeprint', () => {
  stopPlayback();printState={frame:currentFrame,portraits:portraits.map(b=>b.getAttribute('aria-pressed')==='true')};
  portraits.forEach(b=>{if(b.getAttribute('aria-pressed')==='true')b.click();});
  gifView.src=frames[0];showFrame(10);
});
window.addEventListener('afterprint', () => {
  if(!printState)return;
  portraits.forEach((b,i)=>{if(printState.portraits[i])b.click();});showFrame(printState.frame);updateGif();printState=null;
});
document.querySelector('#print-page').addEventListener('click',()=>window.print());
