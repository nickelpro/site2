function setSrcToAttr(dataname) {
  for (const el of document.querySelectorAll(`[${dataname}]`)) {
    el.src = el.getAttribute(dataname);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const dark = localStorage.getItem('dark-mode');
  if (dark == null) {
    localStorage.setItem('dark-mode', 'false');
    setSrcToAttr('data-lightsrc');
  } else if (dark === 'true') {
    document.body.classList.add('dark-mode');
    setSrcToAttr('data-darksrc');
  }
  document.body.style.visibility = 'visible';
  document.body.style.opacity = 1;
  window.requestAnimationFrame(() => {
    document.body.style.transition = 'color 1s';
    document.body.style.transition = 'background-color 1s'
  });
});
